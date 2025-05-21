#!/usr/bin/env python3
"""
Test benchmark with real images from test_data directory AND downloaded test images.
This ensures both local and remote image sources are tested.
"""

import os
import tempfile
from benchmark_fastvlm import find_test_images, download_test_images, run_benchmark

class MockAnalyzer:
    """Mock analyzer for testing without real FastVLM model."""
    def __init__(self):
        self.model_info = {'name': 'MockModel'}
        self.model_path = '/mock/path'
        
    def analyze_image(self, path, prompt=None):
        """Simulate analyzing an image."""
        # Let's assume all real images are valid
        return {
            "description": f"Mock analysis of {os.path.basename(path)}",
            "tags": ["mock", "test", "real_image"],
            "metadata": {
                "model": "MockModel",
                "time": 0.1
            }
        }

def main():
    """Main test function."""
    print("==== PART 1: Testing with local test images ====")
    # Find real test images
    local_images = find_test_images()
    print(f"Found {len(local_images)} local test images")
    
    # Create mock analyzer
    mock_analyzer = MockAnalyzer()
    
    # Run benchmark with local images
    local_output_file = "/tmp/benchmark_local_images.json"
    local_results = run_benchmark(mock_analyzer, local_images, local_output_file)
    
    print(f"\nLocal images test completed")
    print(f"Results saved to: {local_output_file}")
    
    print("\n==== PART 2: Testing with downloaded test images ====")
    # Download test images
    temp_dir = tempfile.mkdtemp()
    print(f"Downloading test images to: {temp_dir}")
    downloaded_images = download_test_images(temp_dir)
    print(f"Downloaded {len(downloaded_images)} test images")
    
    # Run benchmark with downloaded images
    if downloaded_images:
        downloaded_output_file = "/tmp/benchmark_downloaded_images.json"
        downloaded_results = run_benchmark(mock_analyzer, downloaded_images, downloaded_output_file)
        
        print(f"\nDownloaded images test completed")
        print(f"Results saved to: {downloaded_output_file}")
    else:
        print("\nWARNING: No images were downloaded, skipping this part of the test")
    
    print("\n==== PART 3: Testing with combined image set ====")
    # Combine local and downloaded images
    all_images = local_images + downloaded_images
    print(f"Combined test set contains {len(all_images)} images")
    
    # Run benchmark with all images
    combined_output_file = "/tmp/benchmark_combined_images.json"
    combined_results = run_benchmark(mock_analyzer, all_images, combined_output_file)
    
    print(f"\nCombined images test completed")
    print(f"Results saved to: {combined_output_file}")
    
if __name__ == "__main__":
    main()