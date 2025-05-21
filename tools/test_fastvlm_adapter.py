#!/usr/bin/env python3
"""
Test script for FastVLM adapter.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our adapter
from src.fastvlm_adapter import run_fastvlm_analysis

def main():
    # Get the test image path - use the GitHub avatar we downloaded earlier
    test_image = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                             "test_data/images/test.jpg")
    
    # Make sure the test image exists
    if not os.path.exists(test_image):
        print(f"Test image not found: {test_image}")
        return
    
    print(f"Running FastVLM analysis on {test_image}...")
    results = run_fastvlm_analysis(
        image_path=test_image,
        prompt="Describe this image in detail.",
        model_size="0.5b",
        temperature=0.1
    )
    
    # Print the results
    print("\nAnalysis Results:")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()