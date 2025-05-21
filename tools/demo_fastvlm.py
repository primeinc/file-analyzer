#!/usr/bin/env python3
"""
FastVLM Demo Script

This script demonstrates FastVLM working through the File Analyzer integration.
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Make sure our modules are in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our FastVLM analyzer class
from fastvlm_test import FastVLMAnalyzer

def main():
    """Main function that runs FastVLM on test images."""
    parser = argparse.ArgumentParser(description="FastVLM Demo")
    parser.add_argument("--image", default="test_data/images/Layer 3 Merge.png", help="Path to test image")
    parser.add_argument("--model", default="libs/ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3", help="Path to model")
    parser.add_argument("--prompt", default="Describe this image in detail.", help="Prompt for analysis")
    args = parser.parse_args()
    
    # Print banner
    print("="*50)
    print("FastVLM Demo - Apple Silicon Vision Language Model")
    print("="*50)
    
    # Initialize analyzer
    print(f"Initializing FastVLM with model: {args.model}")
    analyzer = FastVLMAnalyzer(model_path=args.model)
    
    # Check if model is available
    if not analyzer.check_model():
        print("Error: Model not found or not correctly set up.")
        sys.exit(1)
    
    # Get test image
    image_path = args.image
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        sys.exit(1)
        
    print(f"Using test image: {image_path}")
    
    # Run direct inference using predict.py
    print("\nRunning FastVLM direct inference via predict.py:")
    start_time = time.time()
    result = analyzer.direct_predict(image_path, args.prompt)
    end_time = time.time()
    
    if result:
        print(f"FastVLM Analysis (took {end_time - start_time:.2f}s):")
        if isinstance(result, dict) and "result" in result:
            print(result["result"])
        else:
            print(result)
    else:
        print("Analysis failed.")
    
    print("\nDemo complete!")

if __name__ == "__main__":
    main()