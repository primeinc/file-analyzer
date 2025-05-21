#!/usr/bin/env python3
"""
Test script for JSON error handling in fastvlm_json.py

This script tests the error handling capabilities when JSON parsing fails.
"""

import os
import sys
import json
import tempfile
from fastvlm_json import run_fastvlm_json_analysis, JSONParsingError

def create_test_environment():
    """Create a test environment with mock files."""
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    
    # Create a mock image file
    image_path = os.path.join(temp_dir, "test_image.jpg")
    with open(image_path, "wb") as f:
        f.write(b"dummy image data")
    
    # Create a mock model directory
    model_path = os.path.join(temp_dir, "model")
    os.makedirs(model_path, exist_ok=True)
    
    return {
        "temp_dir": temp_dir,
        "image_path": image_path,
        "model_path": model_path
    }

def run_test(test_name, mock_func, expected_error_type=None):
    """Run a test case with the specified parameters."""
    print(f"\n=== Testing: {test_name} ===")
    
    # Set up test environment
    env = create_test_environment()
    
    try:
        # Run the test with mocked dependencies
        with mock_func():
            print("Test function running...")
            # Call the function being tested with our test environment
            result = run_fastvlm_json_analysis(
                env["image_path"],
                env["model_path"],
                prompt="Describe this image in JSON format",
                max_retries=1  # Only one retry to speed up testing
            )
            print(f"Result: {result}")
    except Exception as e:
        print(f"Caught exception: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        
        if expected_error_type and isinstance(e, expected_error_type):
            print(f"Test PASSED ✅ (Expected {expected_error_type.__name__} was raised)")
            
            # For JSONParsingError, check the content
            if isinstance(e, JSONParsingError):
                print(f"Text content available: {bool(e.text)}")
                print(f"Metadata available: {bool(e.metadata)}")
                print(f"Metadata keys: {list(e.metadata.keys())}")
                
            return True
        else:
            print(f"Test FAILED ❌ (Expected {expected_error_type.__name__ if expected_error_type else 'no exception'}, got {type(e).__name__})")
            return False
    else:
        if expected_error_type:
            print(f"Test FAILED ❌ (Expected {expected_error_type.__name__}, but no exception was raised)")
            return False
        else:
            print(f"Test PASSED ✅ (No exception raised as expected)")
            return True

# Test fixtures using context manager to mock behavior
class MockJSONFailure:
    """Mock context for testing JSON parsing failure."""
    def __enter__(self):
        # Store original imports and functions
        import subprocess
        import fastvlm_json
        self.original_subprocess_run = subprocess.run
        
        # Mock subprocess.run to return invalid JSON
        def mock_run(*args, **kwargs):
            class MockCompletedProcess:
                def __init__(self):
                    self.stdout = "This is not valid JSON at all"
                    self.stderr = ""
                    self.returncode = 0
            return MockCompletedProcess()
        
        subprocess.run = mock_run
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original functions
        import subprocess
        subprocess.run = self.original_subprocess_run
        return False  # Don't suppress exceptions
    
# Main test runner
def main():
    """Run all the tests."""
    print("=== JSON Error Handling Tests ===")
    
    # Set up test environment
    env = create_test_environment()
    
    # Define test cases
    tests = [
        ("JSON Parsing Failure", MockJSONFailure, JSONParsingError),
    ]
    
    # Run tests
    results = []
    for name, mock_class, expected_error in tests:
        results.append(run_test(name, mock_class, expected_error))
    
    # Calculate and print summary
    total = len(results)
    passed = sum(results)
    
    print("\n=== Test Summary ===")
    print(f"Tests run: {total}")
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {total - passed}")
    
    if passed == total:
        print("\nAll tests PASSED! ✅")
        return 0
    else:
        print("\nSome tests FAILED ❌")
        return 1

if __name__ == "__main__":
    sys.exit(main())