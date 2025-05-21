#!/usr/bin/env python3
"""
Test script for JSON extraction improvements in json_utils.py

This script tests the improved JSON extraction capabilities with various
test cases including nested JSON, malformed JSON, and different formats.
"""

import os
import sys
import json
from json_utils import JSONValidator

def run_test(test_name, test_input, expected_result=None):
    """Run a single test case and print results."""
    print(f"\n=== Testing: {test_name} ===")
    print(f"Input: {test_input[:50]}..." if len(test_input) > 50 else f"Input: {test_input}")
    
    result = JSONValidator.extract_json_from_text(test_input)
    
    if result:
        print(f"Extracted: {json.dumps(result, indent=2)}")
        if expected_result:
            success = result == expected_result
            print(f"Test {'PASSED ✅' if success else 'FAILED ❌'}")
            if not success:
                print(f"Expected: {json.dumps(expected_result, indent=2)}")
            return success
        else:
            print("No expected result provided, manually verify output")
            return True
    else:
        print("No JSON could be extracted")
        if expected_result is None:
            print("Test PASSED ✅ (Expected no valid JSON)")
            return True
        else:
            print(f"Test FAILED ❌ (Expected: {json.dumps(expected_result, indent=2)})")
            return False

def test_nested_json():
    """Test extracting nested JSON objects."""
    test_input = """
    Here's what I think about the image:
    
    {
      "description": "A beautiful sunset over the ocean",
      "tags": ["sunset", "ocean", "nature"],
      "details": {
        "colors": ["orange", "purple", "blue"],
        "location": {
          "name": "Pacific Ocean",
          "coordinates": {
            "lat": 34.05,
            "lng": -118.25
          }
        }
      }
    }
    
    I hope this helps!
    """
    
    expected = {
      "description": "A beautiful sunset over the ocean",
      "tags": ["sunset", "ocean", "nature"],
      "details": {
        "colors": ["orange", "purple", "blue"],
        "location": {
          "name": "Pacific Ocean",
          "coordinates": {
            "lat": 34.05,
            "lng": -118.25
          }
        }
      }
    }
    
    return run_test("Nested JSON", test_input, expected)

def test_multiple_json_objects():
    """Test extracting the most relevant JSON object when multiple are present."""
    test_input = """
    First JSON: {"id": 123, "name": "Test"}
    
    Second JSON: {"description": "A cat sitting on a windowsill", "tags": ["cat", "pet", "window"]}
    
    Third JSON: {"status": "complete"}
    """
    
    # We expect it to extract the one with description and tags as most relevant
    expected = {"description": "A cat sitting on a windowsill", "tags": ["cat", "pet", "window"]}
    
    return run_test("Multiple JSON Objects", test_input, expected)

def test_malformed_json():
    """Test extracting JSON from text with syntax errors."""
    test_input = """
    Here's the JSON with some errors:
    
    {
      "description": "A mountain landscape with snow,
      "tags": ["mountain", "snow", landscape"]
    }
    
    Sorry about the errors!
    """
    
    # We expect no valid JSON to be extracted
    return run_test("Malformed JSON", test_input, None)

def test_json_with_escaped_quotes():
    """Test extracting JSON with escaped quotes in strings."""
    # Use a raw string to represent what would be in the actual text
    test_input = r"""
    The model said:
    
    {
      "description": "A sign that reads \"Welcome to our store!\"",
      "tags": ["sign", "store", "welcome"]
    }
    """
    
    # The expected parsed result after json.loads would have the quotes processed
    expected = {
      "description": 'A sign that reads "Welcome to our store!"',
      "tags": ["sign", "store", "welcome"]
    }
    
    return run_test("JSON with Escaped Quotes", test_input, expected)

def test_json_with_special_chars():
    """Test extracting JSON with special characters."""
    # Use a raw string to make the test clearer
    test_input = r"""
    Result:
    
    {
      "description": "Page with text: Line 1\nLine 2\nLine 3",
      "tags": ["text", "document", "multi-line"]
    }
    """
    
    expected = {
      "description": "Page with text: Line 1\nLine 2\nLine 3",
      "tags": ["text", "document", "multi-line"]
    }
    
    return run_test("JSON with Special Characters", test_input, expected)

def test_large_json():
    """Test extracting large JSON objects."""
    tags = ["tag" + str(i) for i in range(1, 51)]
    
    object_json = {
      "description": "A very detailed description that goes on for multiple lines and contains lots of information about what's in the image. " * 5,
      "tags": tags,
      "metadata": {
        "timestamp": "2025-05-20T20:45:00Z",
        "model": "FastVLM 1.5B",
        "confidence": 0.95,
        "processing_time": 2.35
      }
    }
    
    test_input = "Here's the analysis:\n\n" + json.dumps(object_json, indent=2) + "\n\nEnd of analysis."
    
    return run_test("Large JSON", test_input, object_json)

def test_real_world_model_output():
    """Test extracting JSON from realistic model output with text before and after."""
    test_input = """
    I've analyzed the image carefully. Here's what I can see:

    {
      "description": "The image shows a busy city street in Tokyo at night, with bright neon signs and advertisements lighting up the buildings. There are people walking on the sidewalks and cars driving on the road. The scene is vibrant and colorful, typical of a Japanese urban nightlife district like Shinjuku or Shibuya.",
      "tags": ["Tokyo", "night", "city", "neon", "urban", "Japan", "street", "nightlife", "Shinjuku", "crowded"]
    }

    The most prominent elements are definitely the neon signs and the bustling atmosphere of the city at night.
    """
    
    expected = {
      "description": "The image shows a busy city street in Tokyo at night, with bright neon signs and advertisements lighting up the buildings. There are people walking on the sidewalks and cars driving on the road. The scene is vibrant and colorful, typical of a Japanese urban nightlife district like Shinjuku or Shibuya.",
      "tags": ["Tokyo", "night", "city", "neon", "urban", "Japan", "street", "nightlife", "Shinjuku", "crowded"]
    }
    
    return run_test("Real-world Model Output", test_input, expected)

def main():
    """Run all tests and report results."""
    print("=== JSON Extraction Tests ===")
    
    tests = [
        test_nested_json,
        test_multiple_json_objects,
        test_malformed_json,
        test_json_with_escaped_quotes,
        test_json_with_special_chars,
        test_large_json,
        test_real_world_model_output
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
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