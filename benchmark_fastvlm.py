#!/usr/bin/env python3
"""
Benchmark script for FastVLM vision model performance.

This script tests the performance of FastVLM on different image types
and resolutions, reporting metrics like time-to-first-token and
total processing time.
"""

import os
import sys
import time
import json
import argparse
import tempfile
from pathlib import Path
from datetime import datetime

# Make sure fastvlm_test is available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastvlm_test import FastVLMAnalyzer

def download_test_images(output_dir):
    """Download sample test images of different types if not available."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if we already have images
    existing_images = list(Path(output_dir).glob("*.jpg")) + list(Path(output_dir).glob("*.png"))
    if existing_images:
        print(f"Using {len(existing_images)} existing test images in {output_dir}")
        return existing_images
    
    # Download sample images
    try:
        import requests
        from PIL import Image
        from io import BytesIO
        
        # Sample image URLs (replace with actual URLs)
        image_urls = [
            # Natural scenes
            "https://storage.googleapis.com/download.tensorflow.org/example_images/flower_photos.tgz",
            
            # Text documents
            "https://github.com/tesseract-ocr/tessdata/raw/main/pdf.png",
            
            # Technical diagrams
            "https://matplotlib.org/stable/_images/sphx_glr_bar_001.png",
            
            # Portraits
            "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Wildlife_at_Maasai_Mara_%28Lion%29.jpg/330px-Wildlife_at_Maasai_Mara_%28Lion%29.jpg"
        ]
        
        downloaded_images = []
        for i, url in enumerate(image_urls):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    img_path = os.path.join(output_dir, f"sample_{i+1}.jpg")
                    img.save(img_path)
                    downloaded_images.append(img_path)
                    print(f"Downloaded {url} to {img_path}")
            except Exception as e:
                print(f"Error downloading {url}: {e}")
        
        return downloaded_images
    except ImportError:
        print("Missing required packages for downloading images.")
        print("Using sample images from test_data directory instead.")
        return []
        
def find_test_images():
    """Find test images in the project."""
    # Check in test_data directory
    test_data = Path(__file__).parent / "test_data"
    if test_data.exists():
        images = []
        # Find all image files recursively
        for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
            images.extend(list(test_data.glob(f"**/*{ext}")))
        
        if images:
            print(f"Found {len(images)} test images in test_data directory")
            return images
    
    # If no images found, try to download some
    benchmark_dir = Path(__file__).parent / "benchmark_images"
    return download_test_images(str(benchmark_dir))

def run_benchmark(analyzer, images, output_file=None):
    """Run benchmark tests on the provided images."""
    if not images:
        print("No test images available for benchmarking")
        return
        
    results = {
        "timestamp": datetime.now().isoformat(),
        "model": analyzer.model_info["name"] if hasattr(analyzer, "model_info") else "FastVLM",
        "model_path": analyzer.model_path,
        "images": {},
        "summary": {}
    }
    
    total_time = 0
    total_size = 0
    
    for img_path in images:
        img_path = str(img_path)
        print(f"Testing {img_path}...")
        
        # Get image size
        img_size = os.path.getsize(img_path)
        total_size += img_size
        
        # Run analysis
        start_time = time.time()
        analysis = analyzer.analyze_image(img_path, prompt="Describe this image in detail.")
        end_time = time.time()
        
        # Record metrics
        processing_time = end_time - start_time
        total_time += processing_time
        
        # Extract analysis result
        output = None
        if isinstance(analysis, dict):
            output = analysis.get("response", str(analysis))
        elif analysis:
            output = analysis
            
        # Record result
        results["images"][img_path] = {
            "size_bytes": img_size,
            "processing_time": processing_time,
            "output_length": len(output) if output else 0
        }
        
        print(f"  Time: {processing_time:.2f}s, Size: {img_size/1024:.1f}KB")
    
    # Calculate summary metrics
    avg_time = total_time / len(images) if images else 0
    throughput = len(images) / total_time if total_time > 0 else 0
    avg_size = total_size / len(images) / 1024 if images else 0  # KB
    
    results["summary"] = {
        "total_images": len(images),
        "total_time": total_time,
        "avg_time": avg_time,
        "throughput": throughput,
        "avg_size_kb": avg_size
    }
    
    # Print summary
    print("\nBenchmark Summary:")
    print(f"Total images: {len(images)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time per image: {avg_time:.2f}s")
    print(f"Throughput: {throughput:.2f} images/s")
    print(f"Average image size: {avg_size:.1f}KB")
    
    # Save results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to {output_file}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="FastVLM Benchmark")
    parser.add_argument("--model", help="Path to FastVLM model")
    parser.add_argument("--images", help="Directory containing test images")
    parser.add_argument("--output", default="benchmark_results.json", help="Output file for benchmark results")
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = FastVLMAnalyzer(model_path=args.model)
    
    # Find test images
    if args.images and os.path.exists(args.images):
        image_dir = Path(args.images)
        images = []
        for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
            images.extend(list(image_dir.glob(f"*{ext}")))
    else:
        images = find_test_images()
    
    # Run benchmark
    run_benchmark(analyzer, images, args.output)

if __name__ == "__main__":
    main()