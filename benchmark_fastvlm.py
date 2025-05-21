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

# Check if PIL is available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def download_test_images(output_dir=None):
    """Download sample test images of different types if not available.
    
    Args:
        output_dir: Directory to save images. If None, uses test_data/sample_images
        
    Returns:
        List of paths to downloaded or existing images
    """
    # Use test_data/sample_images as the default location
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data", "sample_images")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if we already have images
    existing_images = list(Path(output_dir).glob("*.jpg")) + list(Path(output_dir).glob("*.png"))
    if existing_images:
        print(f"Using {len(existing_images)} existing test images in {output_dir}")
        return existing_images
    
    # Download sample images
    try:
        import requests
        from io import BytesIO
        
        # Check if PIL is available (should be imported at module level)
        if not PIL_AVAILABLE:
            print("PIL/Pillow is required for image processing but not installed.")
            print("Please install with: pip install Pillow")
            return []
        
        # Sample image URLs with diverse content for benchmarking
        # Including standard test images commonly used in computer vision
        image_urls = [
            # Standard computer vision test images from various reliable sources
            "https://github.com/tensorflow/models/raw/master/research/deeplab/g3doc/img/image1.jpg",    # Person with bicycle
            "https://github.com/tensorflow/models/raw/master/research/deeplab/g3doc/img/image2.jpg",    # Dog on a beach
            
            # Natural scenes from reliable sources
            "https://raw.githubusercontent.com/tensorflow/models/master/research/object_detection/test_images/image1.jpg",
            "https://raw.githubusercontent.com/tensorflow/models/master/research/object_detection/test_images/image2.jpg",
            "https://raw.githubusercontent.com/tensorflow/tfjs-examples/master/mobilenet/cat.jpg",
            
            # Technical diagrams and charts that are stable URLs
            "https://matplotlib.org/stable/_images/sphx_glr_bar_001.png",
            "https://matplotlib.org/stable/_images/sphx_glr_pie_001.png",
            "https://matplotlib.org/stable/_images/sphx_glr_scatter_001.png",     # Scatter plot
            
            # Document images
            "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/printed_text.jpg", # Text document from Microsoft
            
            # Aerial images
            "https://raw.githubusercontent.com/microsoft/AirSim/master/docs/images/demo_video.png",     # Aerial view
            
            # Wildlife
            "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Wildlife_at_Maasai_Mara_%28Lion%29.jpg/330px-Wildlife_at_Maasai_Mara_%28Lion%29.jpg"
        ]
        
        downloaded_images = []
        for i, url in enumerate(image_urls):
            try:
                print(f"Downloading image from {url}...")
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    try:
                        # Determine file extension from content type or URL
                        file_ext = ".jpg"  # Default extension
                        content_type = response.headers.get('content-type', '')
                        if 'png' in content_type:
                            file_ext = ".png"
                        elif 'gif' in content_type:
                            file_ext = ".gif"
                        elif 'jpeg' in url.lower() or 'jpg' in url.lower():
                            file_ext = ".jpg"
                        elif 'png' in url.lower():
                            file_ext = ".png"
                        
                        # Attempt to open the image to validate it
                        img = Image.open(BytesIO(response.content))
                        img_path = os.path.join(output_dir, f"sample_{i+1}{file_ext}")
                        img.save(img_path)
                        downloaded_images.append(img_path)
                        print(f"✓ Successfully downloaded and saved {url} to {img_path}")
                    except Exception as img_error:
                        print(f"✗ Error processing image from {url}: {img_error}")
                        print("  This may not be a valid image file or could be in an unsupported format.")
                else:
                    print(f"✗ Failed to download {url}: HTTP status {response.status_code}")
            except requests.RequestException as req_error:
                print(f"✗ Network error downloading {url}: {req_error}")
            except Exception as e:
                print(f"✗ Unexpected error processing {url}: {e}")
        
        return downloaded_images
    except ImportError:
        print("Missing required packages for downloading images.")
        print("Using sample images from test_data directory instead.")
        return []
        
def find_test_images():
    """Find test images in the project.
    
    This function looks for images in the following locations, in order:
    1. test_data/sample_images (downloaded standard test images)
    2. test_data/images (user-provided test images)
    3. Throughout test_data recursively
    4. Downloads sample images to test_data/sample_images if none found
    
    Returns:
        List of paths to test images
    """
    images = []
    
    # Check in test_data/sample_images directory first (our standard test images)
    sample_images_dir = Path(__file__).parent / "test_data" / "sample_images"
    if sample_images_dir.exists():
        # Find all image files in the sample images directory
        for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"]:
            images.extend(list(sample_images_dir.glob(f"*{ext}")))
        
        if images:
            print(f"Found {len(images)} test images in test_data/sample_images directory")
            return images
    
    # Check in test_data/images directory next (user test images)
    test_images_dir = Path(__file__).parent / "test_data" / "images"
    if test_images_dir.exists():
        test_images = []
        # Find all image files in the images directory
        for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"]:
            test_images.extend(list(test_images_dir.glob(f"*{ext}")))
        
        if test_images:
            print(f"Found {len(test_images)} test images in test_data/images directory")
            return test_images
            
    # If images dir doesn't have images, check all of test_data
    test_data = Path(__file__).parent / "test_data"
    if test_data.exists():
        recursive_images = []
        # Find all image files recursively
        for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"]:
            recursive_images.extend(list(test_data.glob(f"**/*{ext}")))
        
        if recursive_images:
            print(f"Found {len(recursive_images)} test images in test_data directory")
            return recursive_images
    
    # If no local images found, download standard test images to sample_images dir
    print("No test images found in test_data. Downloading standard test images...")
    downloaded_images = download_test_images()  # Uses default location test_data/sample_images
    
    # If download also failed, return an empty list with clear error
    if not downloaded_images:
        print("WARNING: Could not find or download any test images!")
        print("Please ensure either:")
        print("  1. test_data/images/ directory contains image files, or")
        print("  2. Internet connectivity is available for downloading sample images")
        return []
        
    return downloaded_images

def run_benchmark(analyzer, images, output_file=None):
    """Run benchmark tests on the provided images."""
    if not images:
        print("No test images available for benchmarking")
        return None
    
    # Setup results structure    
    results = {
        "timestamp": datetime.now().isoformat(),
        "model": analyzer.model_info["name"] if hasattr(analyzer, "model_info") else "FastVLM",
        "model_path": analyzer.model_path,
        "images": {},
        "summary": {},
        "errors": []
    }
    
    # Initialize counters
    total_time = 0
    total_size = 0 
    total_preprocessed_size = 0  # Keep track of preprocessed size to show savings
    successful_images = 0
    failed_images = 0
    
    # Import PIL if available for preprocessing
    if PIL_AVAILABLE:
        from PIL import Image
    
    for img_path in images:
        img_path = str(img_path)
        print(f"\nTesting {img_path}...")
        
        try:
            # Verify the image exists and is readable
            if not os.path.exists(img_path):
                print(f"  ✗ Error: Image file not found")
                results["errors"].append({
                    "image": img_path,
                    "error": "File not found"
                })
                failed_images += 1
                continue
            
            # Get original image size
            try:
                img_size = os.path.getsize(img_path)
                total_size += img_size
                
                # Try to open the image to verify it's valid
                if PIL_AVAILABLE:
                    Image.open(img_path).verify()
            except Exception as img_error:
                print(f"  ✗ Error: Invalid image file: {img_error}")
                results["errors"].append({
                    "image": img_path,
                    "error": f"Invalid image file: {str(img_error)}"
                })
                failed_images += 1
                continue
                
            # Check if the image is already preprocessed (to avoid double processing)
            already_preprocessed = ("fastvlm_temp_" in os.path.basename(img_path) or 
                                  "benchmark_temp_" in os.path.basename(img_path))
            
            if already_preprocessed:
                print(f"  Image already preprocessed, skipping preprocessing step")
                preprocessed_image = img_path
                preprocessed_size = img_size
            else:
                # NORMALIZE AND REDUCE IMAGE SIZE BEFORE PROCESSING
                # Initialize with defaults
                preprocessed_image = img_path
                preprocessed_size = img_size
                
                # First try to use VisionAnalyzer's preprocess method if available
                has_vision_preprocessing = (hasattr(analyzer, 'vision_analyzer') and 
                                          hasattr(analyzer.vision_analyzer, 'preprocess_image'))
                
                # Fallback to manual preprocessing if needed
                if has_vision_preprocessing:
                    # Use the vision analyzer's built-in preprocessing
                    try:
                        preprocessed_image = analyzer.vision_analyzer.preprocess_image(img_path, mode="describe")
                        if preprocessed_image and os.path.exists(preprocessed_image):
                            preprocessed_size = os.path.getsize(preprocessed_image)
                            print(f"  Preprocessed image: {img_size/1024:.1f}KB → {preprocessed_size/1024:.1f}KB " +
                                f"({(1 - preprocessed_size/img_size)*100:.1f}% reduction)")
                    except Exception as preproc_error:
                        print(f"  ⚠ Warning: Could not preprocess with vision_analyzer: {preproc_error}")
                        
                # If no preprocessing happened or it failed, do manual preprocessing for large images
                elif PIL_AVAILABLE and img_size > 1024*1024:  # Only preprocess if > 1MB
                    try:
                        # Open image
                        img = Image.open(img_path)
                        
                        # Calculate resize dimensions (max 1024x1024, preserve aspect ratio)
                        max_dim = 1024
                        orig_width, orig_height = img.size
                        
                        if orig_width > max_dim or orig_height > max_dim:
                            if orig_width > orig_height:
                                new_width = max_dim
                                new_height = int(orig_height * (max_dim / orig_width))
                            else:
                                new_height = max_dim
                                new_width = int(orig_width * (max_dim / orig_height))
                                
                            # Resize image
                            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                            
                            # Save to temporary file
                            import tempfile
                            temp_dir = tempfile.gettempdir()
                            preprocessed_image = os.path.join(temp_dir, f"benchmark_temp_{os.path.basename(img_path)}")
                            
                            # Save with reduced quality/compression for JPEGs to further reduce size
                            if img_path.lower().endswith(('.jpg', '.jpeg')):
                                resized_img.save(preprocessed_image, quality=85, optimize=True)
                            else:
                                resized_img.save(preprocessed_image, optimize=True)
                                
                            # Get new size
                            preprocessed_size = os.path.getsize(preprocessed_image)
                            print(f"  Manually preprocessed: {img_size/1024:.1f}KB → {preprocessed_size/1024:.1f}KB " +
                                f"({(1 - preprocessed_size/img_size)*100:.1f}% reduction)")
                    except Exception as preproc_error:
                        print(f"  ⚠ Warning: Manual preprocessing failed: {preproc_error}")
            
            total_preprocessed_size += preprocessed_size
                
            # Run analysis with preprocessed image
            print(f"  Processing image ({preprocessed_size/1024:.1f}KB)...")
            start_time = time.time()
            try:
                analysis = analyzer.analyze_image(preprocessed_image, prompt="Describe this image in detail.")
                end_time = time.time()
                
                if analysis is None:
                    print(f"  ✗ Error: Analysis failed (no result returned)")
                    results["errors"].append({
                        "image": img_path,
                        "error": "Analysis returned None"
                    })
                    failed_images += 1
                    continue
                
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
                    "preprocessed_size_bytes": preprocessed_size,
                    "size_reduction_pct": (1 - preprocessed_size/img_size)*100 if img_size != preprocessed_size else 0,
                    "processing_time": processing_time,
                    "output_length": len(output) if output else 0,
                    "status": "success"
                }
                
                print(f"  ✓ Success: Time: {processing_time:.2f}s, Size: {preprocessed_size/1024:.1f}KB")
                successful_images += 1
                
            except Exception as analysis_error:
                end_time = time.time()
                processing_time = end_time - start_time
                
                print(f"  ✗ Error during analysis: {analysis_error}")
                results["errors"].append({
                    "image": img_path,
                    "error": f"Analysis error: {str(analysis_error)}",
                    "time_before_error": processing_time
                })
                
                # Record the failure in results
                results["images"][img_path] = {
                    "size_bytes": img_size,
                    "preprocessed_size_bytes": preprocessed_size,
                    "processing_time": processing_time,
                    "status": "error",
                    "error": str(analysis_error)
                }
                
                failed_images += 1
                
        except Exception as e:
            print(f"  ✗ Unexpected error processing image: {e}")
            results["errors"].append({
                "image": img_path,
                "error": f"Unexpected error: {str(e)}"
            })
            failed_images += 1
    
    # Only calculate metrics if we have successful images
    if successful_images > 0:
        # Calculate summary metrics (only for successful analyses)
        avg_time = total_time / successful_images
        throughput = successful_images / total_time if total_time > 0 else 0
        avg_orig_size = total_size / len(images) / 1024 if images else 0  # KB
        avg_processed_size = total_preprocessed_size / len(images) / 1024 if images else 0  # KB
        
        # Calculate size reduction percentage
        if total_size > 0:
            size_reduction_pct = (1 - (total_preprocessed_size / total_size)) * 100
        else:
            size_reduction_pct = 0
        
        results["summary"] = {
            "total_images": len(images),
            "successful_images": successful_images,
            "failed_images": failed_images,
            "success_rate": (successful_images / len(images)) * 100 if images else 0,
            "total_time": total_time,
            "avg_time": avg_time,
            "throughput": throughput,
            "avg_original_size_kb": avg_orig_size,
            "avg_processed_size_kb": avg_processed_size,
            "total_size_reduction_pct": size_reduction_pct
        }
        
        # Print summary
        print("\nBenchmark Summary:")
        print(f"Total images: {len(images)}")
        print(f"Successful analyses: {successful_images}")
        print(f"Failed analyses: {failed_images}")
        print(f"Success rate: {(successful_images / len(images)) * 100:.1f}%")
        print(f"Total processing time: {total_time:.2f}s")
        print(f"Average time per image: {avg_time:.2f}s")
        print(f"Throughput: {throughput:.2f} images/s")
        print(f"Average original size: {avg_orig_size:.1f}KB")
        print(f"Average processed size: {avg_processed_size:.1f}KB")
        print(f"Overall size reduction: {size_reduction_pct:.1f}%")
    else:
        # No successful analyses
        avg_orig_size = total_size / len(images) / 1024 if images else 0  # KB
        avg_processed_size = total_preprocessed_size / len(images) / 1024 if images else 0  # KB
        
        # Calculate size reduction percentage
        if total_size > 0:
            size_reduction_pct = (1 - (total_preprocessed_size / total_size)) * 100
        else:
            size_reduction_pct = 0
            
        results["summary"] = {
            "total_images": len(images),
            "successful_images": 0,
            "failed_images": failed_images,
            "success_rate": 0,
            "avg_original_size_kb": avg_orig_size,
            "avg_processed_size_kb": avg_processed_size,
            "total_size_reduction_pct": size_reduction_pct,
            "error": "All image analyses failed"
        }
        
        print("\nBenchmark Summary:")
        print("ERROR: All image analyses failed.")
        print(f"Total images attempted: {len(images)}")
        print(f"Average original size: {avg_orig_size:.1f}KB")
        print(f"Average processed size: {avg_processed_size:.1f}KB")
        print(f"Overall size reduction: {size_reduction_pct:.1f}%")
    
    # Save results
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nDetailed results saved to {output_file}")
        except Exception as save_error:
            print(f"\nError saving results to {output_file}: {save_error}")
    
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