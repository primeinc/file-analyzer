#!/usr/bin/env python3
"""
Test that the benchmark script works properly with downloaded images.
This specifically tests the download_test_images and run_benchmark functions.
"""

import os
import tempfile
import json
import sys

# Add project root to system path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the new module structure
from src.cli.benchmark.main import download_test_images, run_benchmark

class MockAnalyzer:
    """Mock analyzer for testing without real FastVLM model."""
    def __init__(self):
        self.model_info = {'name': 'MockModel'}
        self.model_path = '/mock/path'
        
    def analyze_image(self, path, prompt=None):
        """Simulate analyzing an image."""
        # Simply return a mock result for testing
        return {
            "description": f"Mock analysis of {os.path.basename(path)}",
            "tags": ["mock", "test", "downloaded_image"],
            "metadata": {
                "model": "MockModel",
                "time": 0.1
            }
        }

def main():
    """Main test function."""
    print("Testing benchmark with downloaded images...")
    
    # Create a temp directory for downloading images
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")
    
    # Download test images
    print("Downloading test images...")
    downloaded_images = download_test_images(temp_dir)
    print(f"Successfully downloaded {len(downloaded_images)} images")
    
    if not downloaded_images:
        print("ERROR: No images were downloaded, test cannot continue")
        return
    
    # Create mock analyzer
    mock_analyzer = MockAnalyzer()
    
    # Run benchmark with downloaded images
    output_file = os.path.join(temp_dir, "benchmark_downloaded.json")
    print(f"Running benchmark with downloaded images, output to: {output_file}")
    results = run_benchmark(mock_analyzer, downloaded_images, output_file)
    
    # Verify the results
    if os.path.exists(output_file):
        print(f"Benchmark results file created: {output_file}")
        # Read the first few lines to verify content
        with open(output_file, 'r') as f:
            results_data = json.load(f)
            num_images = len(results_data.get('images', {}))
            print(f"Results contain data for {num_images} images")
            
            # Check if the number of results matches the number of downloaded images
            if num_images == len(downloaded_images):
                print("SUCCESS: Results contains entries for all downloaded images")
            else:
                print(f"WARNING: Results contains {num_images} entries, but {len(downloaded_images)} were downloaded")
                
            # Check success rate
            if 'summary' in results_data and 'success_rate' in results_data['summary']:
                success_rate = results_data['summary']['success_rate']
                print(f"Benchmark success rate: {success_rate}%")
                if success_rate == 100.0:
                    print("SUCCESS: All images were processed successfully")
                else:
                    print(f"WARNING: Some images failed processing, success rate: {success_rate}%")
    else:
        print(f"ERROR: Benchmark results file was not created: {output_file}")
    
    print("\nTest completed!")
    
if __name__ == "__main__":
    main()