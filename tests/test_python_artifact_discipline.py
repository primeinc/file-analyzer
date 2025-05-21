#!/usr/bin/env python3
"""
Test script to demonstrate Python-only artifact discipline.

This script demonstrates several ways to enforce artifact discipline:
1. Using get_canonical_artifact_path to create canonical directories
2. Using PathGuard to enforce discipline for all file operations
3. Using safe_* functions for individual operations
4. Using the @enforce_path_discipline decorator on custom functions
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import artifact discipline components
from src.artifact_guard import (
    get_canonical_artifact_path, 
    PathGuard, 
    validate_artifact_path,
    safe_copy,
    safe_mkdir,
    safe_write,
    enforce_path_discipline
)

def test_canonical_path_creation():
    """Test creating a canonical artifact path."""
    print("Testing canonical path creation...")
    
    # Create a canonical artifact path
    artifact_dir = get_canonical_artifact_path("test", "python_test")
    print(f"Created canonical path: {artifact_dir}")
    
    # Validate the path
    assert validate_artifact_path(artifact_dir)
    print("✅ Path validation successful")
    
    # Create a file in the canonical path
    test_file = os.path.join(artifact_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("Test content")
    print(f"Created test file: {test_file}")
    
    # Validate the file path
    assert validate_artifact_path(test_file)
    print("✅ File path validation successful")
    
    return artifact_dir, test_file

def test_path_guard():
    """Test the PathGuard context manager."""
    print("\nTesting PathGuard context manager...")
    
    # Create a canonical artifact path
    artifact_dir = get_canonical_artifact_path("test", "pathguard_test")
    print(f"Created canonical path: {artifact_dir}")
    
    # Use PathGuard to enforce artifact discipline
    with PathGuard(artifact_dir):
        # Valid file path - this should work
        valid_path = os.path.join(artifact_dir, "valid_file.txt")
        with open(valid_path, "w") as f:
            f.write("Valid file content")
        print(f"✅ Created file in canonical path: {valid_path}")
        
        # Try to create a file in /tmp - this should fail
        try:
            invalid_path = os.path.join(tempfile.gettempdir(), "invalid_file.txt")
            with open(invalid_path, "w") as f:
                f.write("This should fail")
            print(f"❌ FAIL: Created file in system temp dir: {invalid_path}")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            print(f"✅ PASS: Prevented write to system temp dir: {str(e).splitlines()[0]}")

def test_safe_functions():
    """Test the safe_* functions."""
    print("\nTesting safe_* functions...")
    
    # Create a canonical artifact path
    artifact_dir = get_canonical_artifact_path("test", "safe_functions_test")
    print(f"Created canonical path: {artifact_dir}")
    
    # Use safe_mkdir to create a subdirectory
    subdir = os.path.join(artifact_dir, "subdir")
    safe_mkdir(subdir)
    print(f"✅ Created subdirectory: {subdir}")
    
    # Use safe_write to write a file
    file_path = os.path.join(artifact_dir, "safe_write.txt")
    safe_write(file_path, "Safe write content")
    print(f"✅ Wrote file: {file_path}")
    
    # Create a temporary file for safe_copy
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b"Temp file content")
    temp_file.close()
    
    # Use safe_copy to copy the file
    copy_path = os.path.join(artifact_dir, "copied_file.txt")
    safe_copy(temp_file.name, copy_path)
    print(f"✅ Copied file: {copy_path}")
    
    # Try to use safe_write with an invalid path
    try:
        invalid_path = os.path.join(tempfile.gettempdir(), "invalid_safe_write.txt")
        safe_write(invalid_path, "This should fail")
        print(f"❌ FAIL: safe_write allowed write to system temp dir")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✅ PASS: safe_write prevented write to system temp dir")
    
    # Clean up temporary file
    os.unlink(temp_file.name)

@enforce_path_discipline
def custom_write_function(output_path, content):
    """Custom function with path discipline enforcement via decorator."""
    with open(output_path, "w") as f:
        f.write(content)
    return output_path

def test_enforce_path_discipline_decorator():
    """Test the @enforce_path_discipline decorator."""
    print("\nTesting @enforce_path_discipline decorator...")
    
    # Create a canonical artifact path
    artifact_dir = get_canonical_artifact_path("test", "decorator_test")
    print(f"Created canonical path: {artifact_dir}")
    
    # Use the decorated function with a valid path
    valid_path = os.path.join(artifact_dir, "decorated_valid.txt")
    custom_write_function(valid_path, "Decorator test content")
    print(f"✅ Decorated function wrote to canonical path: {valid_path}")
    
    # Try to use the decorated function with an invalid path
    try:
        invalid_path = os.path.join(tempfile.gettempdir(), "decorated_invalid.txt")
        custom_write_function(invalid_path, "This should fail")
        print(f"❌ FAIL: Decorated function allowed write to system temp dir")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✅ PASS: Decorated function prevented write to system temp dir")

def main():
    """Run all tests."""
    print("=== Python Artifact Discipline Tests ===\n")
    
    try:
        # Run tests
        test_canonical_path_creation()
        test_path_guard()
        test_safe_functions()
        test_enforce_path_discipline_decorator()
        
        print("\n=== All tests passed! ===")
        return 0
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())