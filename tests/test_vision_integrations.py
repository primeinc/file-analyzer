#!/usr/bin/env python3
"""
Test script for verifying the integration between file_analyzer and vision analyzer
"""

import os
import sys
import json
from pathlib import Path

# Add project root to system path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the new module structure
from src.core.vision import VisionAnalyzer, DEFAULT_VISION_CONFIG, VISION_MODELS
VISION_AVAILABLE = True

def test_vision_analyzer():
    """Test the VisionAnalyzer integration"""
    print("=== Testing VisionAnalyzer Integration ===")
    
    # Skip test if vision is not available
    if not VISION_AVAILABLE:
        print("Skipping test since vision analyzer is not available.")
        return
    
    # Test image
    test_image = "test_data/images/test.jpg"  # Updated to use the available test image
    if not os.path.exists(test_image):
        print(f"Warning: Test image not found: {test_image}")
        # Try alternate locations
        alt_locations = [
            "test_data/images/Layer 3 Merge.png",
            Path(__file__).parent.parent / "test_data/images/test.jpg"
        ]
        found = False
        for loc in alt_locations:
            if os.path.exists(str(loc)):
                test_image = str(loc)
                found = True
                print(f"Using alternate test image: {test_image}")
                break
        
        if not found:
            print("No test images found. Skipping vision test.")
            return
    
    print(f"Using test image: {test_image}")
    
    # Create output directory using canonical artifact path
    try:
        from src.core.artifact_guard import get_canonical_artifact_path
        output_dir = Path(get_canonical_artifact_path("test", "vision_integration"))
    except ImportError:
        # Fallback to a simple directory if artifact_guard is not available
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
    
    try:
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
            return
        
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
    except Exception as e:
        print(f"Error during vision test: {str(e)}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_vision_analyzer()