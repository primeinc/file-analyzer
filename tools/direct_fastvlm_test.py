#!/usr/bin/env python3
"""
Direct test script for FastVLM using Python
Replaces the direct_fastvlm_test.sh shell script
"""

import os
import sys
import subprocess
from pathlib import Path
import argparse

# Define paths
project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(project_root))

# Import artifact guard
try:
    from src.artifact_guard import PathGuard, get_canonical_artifact_path
except ImportError:
    print("Error: Could not import artifact_guard. Make sure you're running from the project root.")
    sys.exit(1)

def run_test(image_path, model_dir, prompt, test_name):
    """Run a FastVLM test with the given prompt"""
    print(f"\nTesting with {test_name} prompt:")
    
    # Build the command to run fastvlm_analyzer.py
    analyzer_path = os.path.join(project_root, "src", "fastvlm_analyzer.py")
    cmd = [
        sys.executable,
        analyzer_path,
        "--image", image_path,
        "--model", model_dir,
        "--prompt", prompt,
        "--direct"
    ]
    
    # Run the command
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running FastVLM test: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def main():
    """Main function"""
    # Define test parameters
    test_image = "test_data/images/test.jpg"
    model_dir = "libs/ml-fastvlm/checkpoints/llava-fastvithd_0.5b_stage2/llava-fastvithd_0.5b_stage2"
    
    # Convert to absolute paths
    test_image = os.path.join(project_root, test_image)
    model_dir = os.path.join(project_root, model_dir)
    
    # Print test information
    print(f"=== FastVLM Direct Test ===")
    print(f"Model: {model_dir}")
    print(f"Image: {test_image}")
    
    # Run tests with different prompts
    tests = [
        ("description", "Describe this image in detail."),
        ("architectural analysis", "What architectural style is shown in this logo? Be specific."),
        ("object detection", "List all visual elements in this image and their positions.")
    ]
    
    success_count = 0
    for test_name, prompt in tests:
        if run_test(test_image, model_dir, prompt, test_name):
            success_count += 1
    
    # Print test results
    print(f"\nTests complete! {success_count}/{len(tests)} successful")

if __name__ == "__main__":
    main()