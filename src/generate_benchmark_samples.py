#!/usr/bin/env python3
"""
Generate sample benchmark data for FastVLM model testing.

This script creates sample output data for all test images in canonical artifact paths
without actually running the full LLM inference. It can be used to:

1. Initially generate mock response data for all sample images
2. Save this data as a cache file in a canonical artifact path
3. Reuse the cached data to speed up benchmark testing

After running this once to generate sample data, it will load from the cache
on subsequent runs, making benchmark testing much faster.
"""

import os
import sys
import json
import time
import random
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

# Ensure project root is in sys.path for module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import artifact discipline tools
from src.artifact_guard import get_canonical_artifact_path, PathGuard, validate_artifact_path

# Import local modules
from src.benchmark_fastvlm import find_test_images

# Get canonical artifact path for cache
CACHE_DIR = get_canonical_artifact_path("benchmark", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "benchmark_sample_data.json")

# Sample image descriptions for different categories
DESCRIPTIONS = {
    # Natural scenes
    "nature": [
        "A beautiful landscape with mountains and a lake reflecting the sky.",
        "A forest scene with sunlight streaming through the trees and a path leading into the distance.",
        "A beach with white sand and turquoise water, palm trees lining the shore.",
        "A meadow filled with wildflowers under a blue sky with scattered clouds."
    ],
    # Animals
    "animal": [
        "A lion resting on a rock in the savanna, with golden fur catching the sunlight.",
        "A domestic cat with striking orange fur sitting on a windowsill.",
        "A dog playing in a field, running with joyful energy.",
        "A colorful bird perched on a branch with vibrant plumage."
    ],
    # People
    "people": [
        "A person on a bicycle riding along a path with a dog running alongside.",
        "A group of people walking on a street, carrying shopping bags and engaged in conversation.",
        "Two people sitting at a cafe table, enjoying coffee and conversation.",
        "A person standing on a mountain summit, arms raised in triumph."
    ],
    # Urban
    "urban": [
        "A city skyline at sunset with skyscrapers silhouetted against an orange sky.",
        "A narrow cobblestone street lined with historic buildings and small shops.",
        "A modern architectural building with glass and steel, reflecting the surrounding environment.",
        "A busy intersection with pedestrians crossing and vehicles waiting at traffic lights."
    ],
    # Charts and diagrams
    "chart": [
        "A bar chart showing comparative data with four categories and their respective values.",
        "A pie chart displaying the distribution of resources across different departments.",
        "A scatter plot showing the correlation between two variables with a trend line.",
        "A line graph tracking changes over time with multiple series represented."
    ],
    # Text and documents
    "document": [
        "A document containing text about technical specifications, with paragraphs and bullet points.",
        "A page from a book with paragraphs of text and a small illustration.",
        "A form with various fields and checkboxes for data entry.",
        "A printed article with a headline, columns of text, and a small photograph."
    ]
}

# Sample tags for different categories
TAGS = {
    "nature": ["landscape", "outdoor", "scenic", "wilderness", "natural beauty", "serene", "mountains", "water", "forest"],
    "animal": ["wildlife", "mammal", "predator", "safari", "fur", "cat", "dog", "bird", "pet"],
    "people": ["person", "activity", "lifestyle", "urban", "outdoor recreation", "bicycle", "walking", "casual", "everyday life"],
    "urban": ["city", "architecture", "buildings", "urban landscape", "infrastructure", "skyline", "street", "modern", "historic"],
    "chart": ["data visualization", "statistics", "data analysis", "bar chart", "pie chart", "graph", "trend", "metrics", "comparison"],
    "document": ["text", "printed material", "publication", "typography", "formatted text", "layout", "information", "reading material", "form"]
}

def get_image_hash(image_path):
    """Generate a consistent hash for an image file."""
    try:
        with open(image_path, 'rb') as f:
            # Just hash the first 4KB of the file to keep it fast
            return hashlib.md5(f.read(4096)).hexdigest()
    except Exception:
        # If anything goes wrong, fall back to the filename
        return hashlib.md5(os.path.basename(image_path).encode()).hexdigest()

def categorize_image(image_path):
    """Categorize an image based on its filename and path."""
    filename = os.path.basename(image_path).lower()
    
    # Categorize based on filename patterns
    if any(term in filename for term in ["cat", "lion", "dog", "bird", "animal"]):
        return "animal"
    elif any(term in filename for term in ["bar", "pie", "scatter", "chart", "plot", "graph"]):
        return "chart"
    elif any(term in filename for term in ["text", "doc", "print", "page", "book", "form"]):
        return "document"
    elif any(term in filename for term in ["city", "building", "street", "urban", "architecture"]):
        return "urban"
    elif any(term in filename for term in ["person", "people", "bike", "bicycle", "human"]):
        return "people"
    else:
        # Default to nature for anything else
        return "nature"

def generate_sample_response(image_path, category=None):
    """Generate a sample analysis response for an image."""
    # Determine image category if not provided
    if not category:
        category = categorize_image(image_path)
    
    # Select tags and description for this category
    selected_tags = random.sample(TAGS.get(category, TAGS["nature"]), min(5, len(TAGS.get(category, TAGS["nature"]))))
    description = random.choice(DESCRIPTIONS.get(category, DESCRIPTIONS["nature"]))
    
    # Generate a response time between 0.5 and 2 seconds based on image size
    try:
        img_size = os.path.getsize(image_path)
        # Larger images take longer to process
        response_time = 0.5 + (img_size / (1024 * 1024)) * 0.5
        # Cap at 2 seconds
        response_time = min(response_time, 2.0)
    except:
        response_time = 1.0
    
    # Create response object
    response = {
        "description": description,
        "tags": selected_tags,
        "metadata": {
            "model": "FastVLM-Mock",
            "response_time": response_time,
            "image_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "category": category
        }
    }
    
    return response

def create_or_load_cache():
    """Create or load the cache file for sample responses."""
    # Create cache directory if it doesn't exist
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Check if cache file exists
    if os.path.exists(CACHE_FILE):
        try:
            # Use PathGuard to enforce artifact discipline
            with PathGuard(CACHE_DIR):
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading cache file: {e}")
            return {}
    
    return {}

def save_cache(cache_data):
    """Save the cache data to file."""
    # Create cache directory if it doesn't exist
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    try:
        # Use PathGuard to enforce artifact discipline
        with PathGuard(CACHE_DIR):
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Cache saved to {CACHE_FILE}")
    except Exception as e:
        print(f"Error saving cache file: {e}")

def get_or_generate_response(image_path, cache, force_generate=False):
    """Get a cached response or generate a new one."""
    image_hash = get_image_hash(image_path)
    
    # Check cache unless we're forced to generate a new response
    if not force_generate and image_hash in cache:
        return cache[image_hash]
    
    # Generate a new response
    response = generate_sample_response(image_path)
    cache[image_hash] = response
    return response

def generate_benchmark_data(output_file=None, use_cache=True, force_generate=False):
    """Generate benchmark data for all sample images."""
    # Find all test images
    images = find_test_images()
    if not images:
        print("No test images found. Please run benchmark_fastvlm.py first to download sample images.")
        return
    
    print(f"Generating benchmark data for {len(images)} images...")
    
    # Load cache if we're using it
    cache = create_or_load_cache() if use_cache else {}
    
    # Use canonical artifact path for output file if none provided
    if output_file is None:
        benchmark_dir = get_canonical_artifact_path("benchmark", f"mock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        output_file = os.path.join(benchmark_dir, "benchmark_results.json")
        print(f"Using canonical artifact path for benchmark results: {output_file}")
    else:
        # Validate the provided output path
        if not validate_artifact_path(output_file):
            print(f"Warning: Output file {output_file} is not in a canonical artifact path")
            print(f"Creating canonical artifact path for benchmark results")
            benchmark_dir = get_canonical_artifact_path("benchmark", f"mock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            output_file = os.path.join(benchmark_dir, "benchmark_results.json")
            print(f"Using canonical artifact path: {output_file}")
    
    # Create results structure
    results = {
        "timestamp": datetime.now().isoformat(),
        "model": "FastVLM-Mock",
        "model_path": "/mock/path/fastvlm",
        "output_path": output_file,
        "images": {},
        "summary": {},
        "errors": []
    }
    
    # Process each image
    total_time = 0
    total_size = 0
    successful_images = 0
    
    for img_path in images:
        img_path = str(img_path)
        print(f"Processing {os.path.basename(img_path)}...")
        
        try:
            # Get image size
            img_size = os.path.getsize(img_path)
            total_size += img_size
            
            # Get or generate response
            start_time = time.time()
            response = get_or_generate_response(img_path, cache, force_generate)
            
            # Get image hash for verification
            image_hash = get_image_hash(img_path)
            
            # If using cache, add a small delay to simulate processing
            if use_cache and not force_generate and image_hash in cache:
                time.sleep(0.05)
                
            end_time = time.time()
            
            # Record metrics
            processing_time = end_time - start_time
            total_time += processing_time
            
            # Record result
            results["images"][img_path] = {
                "size_bytes": img_size,
                "processing_time": processing_time,
                "output_length": len(json.dumps(response)),
                "status": "success",
                "response": response
            }
            
            print(f"  ✓ Success: Time: {processing_time:.2f}s, Size: {img_size/1024:.1f}KB")
            successful_images += 1
            
        except Exception as e:
            print(f"  ✗ Error processing image: {e}")
            results["errors"].append({
                "image": img_path,
                "error": str(e)
            })
    
    # Calculate summary metrics
    if successful_images > 0:
        avg_time = total_time / successful_images
        throughput = successful_images / total_time if total_time > 0 else 0
        avg_size = total_size / len(images) / 1024 if images else 0  # KB
        
        results["summary"] = {
            "total_images": len(images),
            "successful_images": successful_images,
            "failed_images": len(images) - successful_images,
            "success_rate": (successful_images / len(images)) * 100 if images else 0,
            "total_time": total_time,
            "avg_time": avg_time,
            "throughput": throughput,
            "avg_size_kb": avg_size
        }
        
        print("\nBenchmark Summary:")
        print(f"Total images: {len(images)}")
        print(f"Successful analyses: {successful_images}")
        print(f"Failed analyses: {len(images) - successful_images}")
        print(f"Success rate: {(successful_images / len(images)) * 100 if images else 0:.1f}%")
        print(f"Total processing time: {total_time:.2f}s")
        print(f"Average time per image: {avg_time:.2f}s")
        print(f"Throughput: {throughput:.2f} images/s")
        print(f"Average image size: {avg_size:.1f}KB")
    
    # Save results
    if output_file:
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Use PathGuard to enforce artifact discipline
            with PathGuard(os.path.dirname(output_file)):
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\nDetailed results saved to {output_file}")
                
                # Also save a summary file
                summary_file = os.path.join(os.path.dirname(output_file), "summary.txt")
                with open(summary_file, 'w') as f:
                    f.write("Mock Benchmark Summary:\n")
                    f.write(f"Total images: {len(images)}\n")
                    f.write(f"Successful analyses: {successful_images}\n")
                    f.write(f"Failed analyses: {len(images) - successful_images}\n")
                    f.write(f"Success rate: {(successful_images / len(images)) * 100 if images else 0:.1f}%\n")
                    f.write(f"Total processing time: {total_time:.2f}s\n")
                    f.write(f"Average time per image: {avg_time:.2f}s\n")
                    f.write(f"Throughput: {throughput:.2f} images/s\n")
                    f.write(f"Average image size: {avg_size:.1f}KB\n")
                print(f"Summary saved to {summary_file}")
        except Exception as e:
            print(f"\nError saving results to {output_file}: {e}")
    
    # Save updated cache
    if use_cache:
        save_cache(cache)
    
    return results

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate sample benchmark data")
    parser.add_argument("--output", help="Output file for benchmark data (uses canonical artifact path if not specified)")
    parser.add_argument("--no-cache", action="store_true", help="Don't use or update the cache")
    parser.add_argument("--force", action="store_true", help="Force regenerate all responses")
    parser.add_argument("--canonical", action="store_true", help="Force use of canonical artifact paths")
    
    args = parser.parse_args()
    
    # If output is specified but not canonical, validate and possibly override
    if args.output and not args.canonical:
        if not validate_artifact_path(args.output):
            print(f"Warning: Output file {args.output} is not in a canonical artifact path")
            print(f"Creating canonical artifact path for benchmark results")
            benchmark_dir = get_canonical_artifact_path("benchmark", f"mock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            output_file = os.path.join(benchmark_dir, "benchmark_results.json")
            print(f"Using canonical artifact path: {output_file}")
        else:
            output_file = args.output
    else:
        output_file = args.output
    
    generate_benchmark_data(
        output_file=output_file,
        use_cache=not args.no_cache,
        force_generate=args.force
    )

if __name__ == "__main__":
    main()