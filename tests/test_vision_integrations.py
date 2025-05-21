#!/usr/bin/env python3
"""
Test script for verifying the integration between file_analyzer.py and vision_analyzer.py
"""

import os
import sys
import json
from pathlib import Path

# Import vision analyzer
try:
    from vision_analyzer import VisionAnalyzer, DEFAULT_VISION_CONFIG, VISION_MODELS
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    print("Error: Failed to import vision_analyzer module")
    sys.exit(1)

def test_vision_analyzer():
    """Test the VisionAnalyzer integration"""
    print("=== Testing VisionAnalyzer Integration ===")
    
    # Test image
    test_image = "test_data/images/Layer 3 Merge.png"
    if not os.path.exists(test_image):
        print(f"Error: Test image not found: {test_image}")
        sys.exit(1)
    
    print(f"Using test image: {test_image}")
    
    # Create output directory
    output_dir = Path("analysis_results/integration_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load default config
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        vision_config = config.get("vision", DEFAULT_VISION_CONFIG)
    except (FileNotFoundError, json.JSONDecodeError):
        vision_config = DEFAULT_VISION_CONFIG
        print("Warning: Using default vision config (config.json not found or invalid)")
    
    print("\nVision Config:")
    print(json.dumps(vision_config, indent=2))
    
    # Initialize analyzer
    print("\nInitializing VisionAnalyzer...")
    analyzer = VisionAnalyzer(vision_config)
    
    # Print analyzer info
    print(f"Model name: {analyzer.model_name}")
    print(f"Model info: {analyzer.model_info['name']}")
    
    # Access model_path
    print("\nAccessing model_path...")
    model_path = analyzer.config.get("model_path") or analyzer.model_info["model_options"]["default"]
    print(f"Model path: {model_path}")
    
    # Check dependencies
    print("\nChecking dependencies...")
    if not analyzer.check_dependencies():
        print(f"Required dependencies for {analyzer.model_info['name']} not installed.")
        print(f"Run '{analyzer.model_info['install_cmd']}' to install.")
        sys.exit(1)
    
    # Test analysis
    print("\nRunning analyze_image...")
    result = analyzer.analyze_image(test_image, mode="describe")
    
    # Check result
    if result:
        print("\nAnalysis succeeded!")
        
        # Check if result is JSON
        if isinstance(result, dict):
            print("Result is a dictionary (JSON)")
            
            # Print metadata
            if "metadata" in result:
                print("\nMetadata:")
                print(json.dumps(result["metadata"], indent=2))
                
            # Save result
            output_file = output_dir / "test_result.json"
            analyzer.save_results({test_image: result}, output_file)
            print(f"\nResult saved to {output_file}")
        else:
            print("Result is a string (text)")
            print(result[:100] + "..." if len(result) > 100 else result)
    else:
        print("\nAnalysis failed!")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_vision_analyzer()