#!/usr/bin/env python3
"""
Test script for the benchmark functionality
"""

import time
import tempfile
import os
import sys
import unittest

# Add project root to system path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the new module structure
from src.cli.benchmark.main import run_benchmark

class MockAnalyzer:
    """Mock analyzer for testing without real FastVLM model."""
    def __init__(self):
        self.model_info = {'name': 'MockModel'}
        self.model_path = '/mock/path'
        
    def analyze_image(self, path, prompt=None):
        """Simulate analyzing an image with a delay."""
        if not os.path.exists(path):
            print(f"Mock error: Image not found: {path}")
            return None
            
        # Simulate analysis time proportional to file size
        try:
            size = os.path.getsize(path)
            delay = 0.01 + (size / 1024 / 1024 * 0.1)  # Larger files take longer
            time.sleep(delay)
            
            # Return mock analysis result
            return {
                "description": f"This is a mock analysis of image {path}",
                "tags": ["mock", "test"],
                "metadata": {
                    "time": delay,
                    "model": "MockModel"
                }
            }
        except Exception as e:
            print(f"Mock error: {e}")
            return None

# Create some test files of different sizes
def create_test_files():
    """Create temporary test image files of different sizes."""
    temp_dir = tempfile.mkdtemp()
    test_files = []
    
    # Create files of various sizes
    for i, size_kb in enumerate([10, 50, 100, 500, 1000]):
        file_path = os.path.join(temp_dir, f"test_image_{i+1}.jpg")
        with open(file_path, 'wb') as f:
            f.write(b'X' * (size_kb * 1024))  # Fill with dummy content
        test_files.append(file_path)
        
    return temp_dir, test_files

def main():
    """Main test function."""
    print("Testing benchmark_fastvlm.py run_benchmark function...")
    
    # Create test files
    temp_dir, test_files = create_test_files()
    print(f"Created {len(test_files)} test files in {temp_dir}")
    
    # Initialize mock analyzer
    mock_analyzer = MockAnalyzer()
    
    # Run benchmark with mock analyzer
    output_file = os.path.join(temp_dir, "mock_benchmark_results.json")
    results = run_benchmark(mock_analyzer, test_files, output_file)
    
    if results:
        print("Benchmark completed successfully!")
        print(f"Output saved to: {output_file}")
        
    # Also test failure scenarios
    print("\nTesting failure scenarios:")
    
    # Test with non-existent files
    bad_files = ["/non/existent/file1.jpg", "/non/existent/file2.jpg"]
    print("Running benchmark with non-existent files...")
    failure_results = run_benchmark(mock_analyzer, bad_files)
    
    # Test with empty file list
    print("Running benchmark with empty file list...")
    empty_results = run_benchmark(mock_analyzer, [])
    
    # Clean up
    for file in test_files:
        os.remove(file)
    os.rmdir(temp_dir)
    
    print("All tests completed!")

if __name__ == "__main__":
    main()