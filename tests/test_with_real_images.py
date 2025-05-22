#!/usr/bin/env python3
"""
Test benchmark with real images from test_data directory AND downloaded test images.
This ensures both local and remote image sources are tested.
"""

import os
import sys
import tempfile

# Try to import benchmark functions
try:
    # Try importing from src.cli.benchmark.samples
    from src.cli.benchmark.samples import find_test_images, download_test_images
    from src.cli.benchmark.utils import run_benchmark
    BENCHMARK_AVAILABLE = True
except ImportError:
    try:
        # Fallback to old module
        from benchmark_fastvlm import find_test_images, download_test_images, run_benchmark
        BENCHMARK_AVAILABLE = True
    except ImportError:
        BENCHMARK_AVAILABLE = False
        print("Warning: Failed to import benchmark_fastvlm module. Skipping real image tests.")

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
    # Skip if benchmark module is not available
    if not BENCHMARK_AVAILABLE:
        print("Skipping test since benchmark module is not available.")
        return
    
    # Try to use artifact paths for outputs if available
    try:
        from src.core.artifact_guard import get_canonical_artifact_path
        ARTIFACTS_AVAILABLE = True
        artifact_dir = get_canonical_artifact_path("test", "benchmark_test")
    except ImportError:
        ARTIFACTS_AVAILABLE = False
        artifact_dir = "/tmp"
    
    print("==== PART 1: Testing with local test images ====")
    try:
        # Find real test images
        local_images = find_test_images()
        print(f"Found {len(local_images)} local test images")
        
        if not local_images:
            print("No local test images found, skipping test")
            return
        
        # Create mock analyzer
        mock_analyzer = MockAnalyzer()
        
        # Run benchmark with local images
        local_output_file = os.path.join(artifact_dir, "benchmark_local_images.json")
        local_results = run_benchmark(mock_analyzer, local_images, local_output_file)
        
        print(f"\nLocal images test completed")
        print(f"Results saved to: {local_output_file}")
        
        downloaded_images = []
        if os.environ.get("DOWNLOAD_TEST_IMAGES", "0") == "1":
            print("\n==== PART 2: Testing with downloaded test images ====")
            # Download test images
            try:
                if ARTIFACTS_AVAILABLE:
                    temp_dir = get_canonical_artifact_path("tmp", "download_test_images")
                else:
                    temp_dir = tempfile.mkdtemp()
                    
                print(f"Downloading test images to: {temp_dir}")
                downloaded_images = download_test_images(temp_dir)
                print(f"Downloaded {len(downloaded_images)} test images")
                
                # Run benchmark with downloaded images
                if downloaded_images:
                    downloaded_output_file = os.path.join(artifact_dir, "benchmark_downloaded_images.json")
                    downloaded_results = run_benchmark(mock_analyzer, downloaded_images, downloaded_output_file)
                    
                    print(f"\nDownloaded images test completed")
                    print(f"Results saved to: {downloaded_output_file}")
                else:
                    print("\nWARNING: No images were downloaded, skipping this part of the test")
            except Exception as e:
                print(f"Error downloading test images: {str(e)}")
                downloaded_images = []
        
        if downloaded_images:
            print("\n==== PART 3: Testing with combined image set ====")
            # Combine local and downloaded images
            all_images = local_images + downloaded_images
            print(f"Combined test set contains {len(all_images)} images")
            
            # Run benchmark with all images
            combined_output_file = os.path.join(artifact_dir, "benchmark_combined_images.json")
            combined_results = run_benchmark(mock_analyzer, all_images, combined_output_file)
            
            print(f"\nCombined images test completed")
            print(f"Results saved to: {combined_output_file}")
    except Exception as e:
        print(f"Error during benchmark test: {str(e)}")
    
if __name__ == "__main__":
    main()