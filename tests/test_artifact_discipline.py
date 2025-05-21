#!/usr/bin/env python3
"""
Test script to verify artifact discipline enforcement in Python modules.
This script doesn't require any ML models to run.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import artifact discipline tools
from src.artifact_guard import get_canonical_artifact_path, PathGuard, validate_artifact_path

def test_canonical_paths():
    """Test creating and using canonical artifact paths."""
    print("Testing canonical artifact path creation...")
    
    # Create canonical paths for different artifact types
    test_dir = get_canonical_artifact_path("test", "artifact_discipline_test")
    vision_dir = get_canonical_artifact_path("vision", "mock_analysis")
    benchmark_dir = get_canonical_artifact_path("benchmark", "mock_benchmark")
    
    print(f"Created test directory: {test_dir}")
    print(f"Created vision directory: {vision_dir}")
    print(f"Created benchmark directory: {benchmark_dir}")
    
    # Verify manifest files were created
    print("\nVerifying manifest files...")
    for dir_path in [test_dir, vision_dir, benchmark_dir]:
        manifest_path = os.path.join(dir_path, "manifest.json")
        if os.path.exists(manifest_path):
            print(f"✅ Manifest exists at {manifest_path}")
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                print(f"  - Created: {manifest.get('created', 'unknown')}")
                print(f"  - Script: {manifest.get('context', {}).get('script', 'unknown')}")
            except Exception as e:
                print(f"❌ Error reading manifest: {e}")
        else:
            print(f"❌ Manifest missing at {manifest_path}")
    
    return test_dir, vision_dir, benchmark_dir

def test_path_validation():
    """Test the path validation logic."""
    print("\nTesting path validation...")
    
    # Test valid paths
    valid_paths = [
        os.path.join(project_root, "artifacts", "test", "sample"),
        os.path.join(project_root, "src", "module.py"),
        os.path.join(project_root, "tools", "script.sh"),
        os.path.join(project_root, "tests", "test_file.py"),
        os.path.join(project_root, "README.md")
    ]
    
    # Test invalid paths
    invalid_paths = [
        os.path.join(project_root, "test_output"),
        os.path.join(project_root, "fastvlm_test_results"),
        os.path.join(project_root, "analysis_temp"),
        "/tmp/artifact_test.txt",
        "/var/tmp/test_results.json"
    ]
    
    # Check valid paths
    for path in valid_paths:
        result = validate_artifact_path(path)
        print(f"Path: {path}")
        print(f"  {'✅ Valid' if result else '❌ Invalid'} - Expected: Valid")
    
    # Check invalid paths
    for path in invalid_paths:
        result = validate_artifact_path(path)
        print(f"Path: {path}")
        print(f"  {'❌ Valid' if result else '✅ Invalid'} - Expected: Invalid")

def test_pathguard(test_dir):
    """Test PathGuard context manager enforcement."""
    print("\nTesting PathGuard enforcement...")
    
    # Create a file within canonical path (should work)
    canonical_file = os.path.join(test_dir, "allowed_file.txt")
    try:
        with PathGuard(test_dir):
            with open(canonical_file, 'w') as f:
                f.write("This file is allowed because it's in a canonical artifact path.")
        print(f"✅ Successfully wrote to canonical path: {canonical_file}")
    except Exception as e:
        print(f"❌ Error writing to canonical path: {e}")
    
    # Try to create a file outside canonical paths (should fail)
    non_canonical_file = os.path.join(project_root, "bad_output.txt")
    try:
        with PathGuard(test_dir):
            with open(non_canonical_file, 'w') as f:
                f.write("This file should not be allowed.")
        print(f"❌ Warning: Wrote to non-canonical path: {non_canonical_file}")
    except ValueError as e:
        print(f"✅ Correctly prevented write to non-canonical path: {non_canonical_file}")
        print(f"  Error message: {str(e).split('\n')[0]}")

def test_mock_analysis(vision_dir, test_image_path=None):
    """Test creating a mock analysis output."""
    print("\nTesting mock analysis output creation...")
    
    # Use a default image path if none provided
    if not test_image_path:
        # Try to find a test image from artifacts
        try:
            benchmark_dir = os.path.join(project_root, "artifacts", "benchmark")
            for root, dirs, files in os.walk(benchmark_dir):
                for file in files:
                    if file.endswith(('.jpg', '.png')):
                        test_image_path = os.path.join(root, file)
                        break
                if test_image_path:
                    break
        except Exception:
            test_image_path = "example_image.jpg"  # Placeholder if no image found
    
    # Create mock analysis output
    analysis_file = os.path.join(vision_dir, "mock_analysis.json")
    
    # Mock analysis data
    analysis = {
        "description": "A cartoon rubber duck wearing a wizard hat and sunglasses in a bathtub surrounded by alphabet blocks. Three penguin businessmen are presenting a blueprint labeled 'INTERGALACTIC BANANA LAUNCHER'.",
        "tags": ["cartoon", "rubber duck", "wizard hat", "sunglasses", "penguins", 
                "business meeting", "bathtub", "alphabet blocks", "banana launcher", 
                "blueprint", "humorous", "colorful"],
        "metadata": {
            "model": "Mock-Analysis",
            "response_time": 0.5,
            "timestamp": datetime.now().isoformat(),
            "image_path": test_image_path
        }
    }
    
    # Write analysis to file using PathGuard
    try:
        with PathGuard(vision_dir):
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
        print(f"✅ Successfully created mock analysis at: {analysis_file}")
    except Exception as e:
        print(f"❌ Error creating mock analysis: {e}")
    
    return analysis_file

def main():
    """Main test function."""
    print("=" * 60)
    print("Artifact Discipline Enforcement Test")
    print("=" * 60)
    
    # Parse command-line arguments
    test_image = None
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
        print(f"Using test image: {test_image}")
    
    # Run tests
    test_dir, vision_dir, benchmark_dir = test_canonical_paths()
    test_path_validation()
    test_pathguard(test_dir)
    analysis_file = test_mock_analysis(vision_dir, test_image)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Canonical test directory: {test_dir}")
    print(f"Canonical vision directory: {vision_dir}")
    print(f"Canonical benchmark directory: {benchmark_dir}")
    print(f"Mock analysis file: {analysis_file}")
    print("\nArtifact discipline test completed successfully!")

if __name__ == "__main__":
    main()