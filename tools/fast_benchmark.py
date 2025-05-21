#!/usr/bin/env python3
"""
Fast benchmark script for FastVLM model testing without actual inference.

This script uses cached sample data to perform benchmarks without running
the actual FastVLM model, making it much faster for testing and development.

It follows the same interface as benchmark_fastvlm.py but uses 
pre-generated sample responses from the cache.
"""

import os
import sys
import json
import time
import argparse
import random
from pathlib import Path
from datetime import datetime

# Make sure benchmark modules are available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmark_fastvlm import find_test_images, run_benchmark
from generate_benchmark_samples import (
    CACHE_FILE,
    get_image_hash,
    create_or_load_cache,
    get_or_generate_response
)

class FastMockAnalyzer:
    """Mock analyzer that uses cached sample data with simulated preprocessing."""
    
    def __init__(self, model_path=None, cache_file=CACHE_FILE):
        """Initialize the mock analyzer with optional model path."""
        self.model_info = {'name': 'FastVLM-Mock'}
        self.model_path = model_path or "/mock/path/fastvlm"
        
        # Load the response cache
        self.cache = create_or_load_cache()
        
        # Add slight randomization to response times
        self.min_response_time = 0.05
        self.max_response_time = 0.15
        
        # Track whether image was preprocessed
        self.preprocessed = {}
        
    def preprocess_image_info(self, image_path):
        """Simulates image preprocessing without actually doing it.
        Returns info about the preprocessing that would be done.
        """
        try:
            # Get original size
            orig_size = os.path.getsize(image_path)
            
            # Check if preprocessing would be needed (>1MB files)
            if orig_size > 1024*1024:
                # For large files, simulate size reduction based on file type
                if image_path.lower().endswith(('.png')):
                    # PNG files compress better for screenshots
                    reduction_factor = random.uniform(0.55, 0.97)  # 55-97% reduction
                elif image_path.lower().endswith(('.jpg', '.jpeg')):
                    # JPEGs already compressed, less reduction 
                    reduction_factor = random.uniform(0.30, 0.60)  # 30-60% reduction
                else:
                    # Other formats, moderate reduction
                    reduction_factor = random.uniform(0.40, 0.80)  # 40-80% reduction
                
                # Calculate new size
                new_size = int(orig_size * (1 - reduction_factor))
                
                # Mark as preprocessed in our tracker
                self.preprocessed[image_path] = {
                    "original_size": orig_size,
                    "new_size": new_size,
                    "reduction_pct": reduction_factor * 100
                }
                
                return {
                    "would_preprocess": True,
                    "original_size": orig_size,
                    "new_size": new_size,
                    "reduction_pct": reduction_factor * 100
                }
            else:
                # Small files wouldn't be preprocessed
                return {
                    "would_preprocess": False,
                    "original_size": orig_size,
                    "new_size": orig_size,
                    "reduction_pct": 0
                }
        except Exception as e:
            # On error, assume no preprocessing
            return {
                "would_preprocess": False,
                "error": str(e)
            }
        
    def analyze_image(self, image_path, prompt=None):
        """Return cached analysis for an image with preprocessing simulation."""
        # Get image hash
        image_hash = get_image_hash(image_path)
        
        # Simulate preprocessing check
        preproc_info = self.preprocess_image_info(image_path)
        if preproc_info.get("would_preprocess", False):
            # Log the simulated preprocessing
            orig_kb = preproc_info["original_size"] / 1024
            new_kb = preproc_info["new_size"] / 1024
            reduction = preproc_info["reduction_pct"]
            print(f"  Simulated preprocessing: {orig_kb:.1f}KB → {new_kb:.1f}KB ({reduction:.1f}% reduction)")
            
            # Simulate slightly faster processing due to smaller image
            delay_factor = 0.7  # preprocessed images process ~30% faster
        else:
            # No preprocessing, use normal timing
            delay_factor = 1.0
            
        # Add a small random delay to simulate processing (adjusted for preprocessing)
        base_delay = random.uniform(self.min_response_time, self.max_response_time)
        delay = base_delay * delay_factor
        time.sleep(delay)
        
        # Check if we have a cached response
        if image_hash in self.cache:
            response = self.cache[image_hash].copy()  # Use a copy to avoid modifying original
            # Update metadata for this run
            if "metadata" not in response:
                response["metadata"] = {}
                
            response["metadata"]["response_time"] = delay
            response["metadata"]["timestamp"] = datetime.now().isoformat()
            response["metadata"]["prompt"] = prompt or "Describe this image."
            
            # Add preprocessing info if applicable
            if preproc_info.get("would_preprocess", False):
                response["metadata"]["preprocessing"] = {
                    "original_size_kb": preproc_info["original_size"] / 1024,
                    "processed_size_kb": preproc_info["new_size"] / 1024,
                    "reduction_pct": preproc_info["reduction_pct"]
                }
            
            return response
        
        # If no cache entry, create a simple response
        return {
            "description": f"Mock analysis of image: {os.path.basename(image_path)}",
            "tags": ["mock", "test", "no-cache"],
            "metadata": {
                "model": "FastVLM-Mock",
                "response_time": delay,
                "timestamp": datetime.now().isoformat(),
                "note": "No cached response found for this image",
                "preprocessing": preproc_info if preproc_info.get("would_preprocess", False) else None
            }
        }

def run_fast_benchmark(image_dir=None, output_file=None, model_path=None):
    """Run a fast benchmark using the mock analyzer with simulated preprocessing."""
    # Find test images
    if image_dir and os.path.exists(image_dir):
        # Use specified directory
        image_dir = Path(image_dir)
        images = []
        for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"]:
            images.extend(list(image_dir.glob(f"**/*{ext}")))
    else:
        # Find images using the standard function
        images = find_test_images()
    
    if not images:
        print("No test images found.")
        return
    
    # Create mock analyzer
    analyzer = FastMockAnalyzer(model_path)
    
    # Calculate original total size
    total_orig_size = 0
    for img_path in images:
        try:
            size = os.path.getsize(img_path)
            total_orig_size += size
        except:
            pass
    
    # Run benchmark
    start_time = time.time()
    results = run_benchmark(analyzer, images, output_file)
    end_time = time.time()
    
    # Calculate preprocessing statistics
    total_preprocessed_size = 0
    files_preprocessed = 0
    
    for img_path, data in analyzer.preprocessed.items():
        total_preprocessed_size += data["new_size"]
        files_preprocessed += 1
    
    # If we did any preprocessing, show stats
    if files_preprocessed > 0:
        overall_reduction = ((total_orig_size - total_preprocessed_size) / total_orig_size) * 100
        print(f"\nPreprocessing Statistics:")
        print(f"Images preprocessed: {files_preprocessed} of {len(images)}")
        print(f"Total original size: {total_orig_size/1024/1024:.2f}MB")
        print(f"Total preprocessed size: {total_preprocessed_size/1024/1024:.2f}MB")
        print(f"Overall size reduction: {overall_reduction:.1f}%")
    
    # Print total benchmark time
    print(f"\nTotal benchmark time: {end_time - start_time:.2f}s")
    
    return results

def main():
    """Main function to parse arguments and run benchmark."""
    parser = argparse.ArgumentParser(description="Fast FastVLM Benchmark")
    parser.add_argument("--model", help="Path to FastVLM model (ignored but kept for compatibility)")
    parser.add_argument("--images", help="Directory containing test images")
    parser.add_argument("--output", default="fast_benchmark_results.json", help="Output file for benchmark results")
    
    args = parser.parse_args()
    
    run_fast_benchmark(args.images, args.output, args.model)

if __name__ == "__main__":
    main()