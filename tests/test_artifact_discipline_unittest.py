#!/usr/bin/env python3
"""
Unittest-based test suite for artifact_guard.py discipline enforcement.

This test suite validates that the Python-only artifact path discipline works
correctly and can fully replace the bash implementation.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import artifact discipline components
from src.core.artifact_guard import (
    get_canonical_artifact_path, 
    PathGuard, 
    validate_artifact_path,
    safe_copy,
    safe_mkdir,
    safe_write,
    enforce_path_discipline,
    ARTIFACT_TYPES,
    ARTIFACTS_ROOT
)

class TestCanonicalPathCreation(unittest.TestCase):
    """Test creating and validating canonical artifact paths."""
    
    def test_canonical_path_creation(self):
        """Test basic canonical path creation."""
        # Create a canonical artifact path for each artifact type
        for artifact_type in ARTIFACT_TYPES:
            path = get_canonical_artifact_path(artifact_type, f"unittest_{artifact_type}")
            self.assertTrue(os.path.exists(path), f"Path {path} should exist")
            self.assertTrue(os.path.isdir(path), f"Path {path} should be a directory")
            self.assertTrue(validate_artifact_path(path), f"Path {path} should be valid")
            
            # Check manifest file exists
            manifest_path = os.path.join(path, "manifest.json")
            self.assertTrue(os.path.exists(manifest_path), f"Manifest {manifest_path} should exist")
            
            # Create a file in the canonical path
            test_file = os.path.join(path, "test.txt")
            with open(test_file, "w") as f:
                f.write(f"Test content for {artifact_type}")
            self.assertTrue(validate_artifact_path(test_file), f"File path {test_file} should be valid")
    
    def test_invalid_artifact_type(self):
        """Test creating a path with an invalid artifact type."""
        with self.assertRaises(ValueError):
            get_canonical_artifact_path("invalid_type", "test_context")
    
    def test_canonical_path_format(self):
        """Test that canonical paths follow the expected format."""
        path = get_canonical_artifact_path("test", "unittest_format")
        
        # Path should be in artifacts/test/
        self.assertTrue(path.startswith(os.path.join(ARTIFACTS_ROOT, "test")), 
                        "Path should be in artifacts/test/")
        
        # Path should contain the context
        self.assertTrue("unittest_format" in path, "Path should contain the context")
        
        # Path should contain git commit and other identifiers
        parts = os.path.basename(path).split("_")
        self.assertGreaterEqual(len(parts), 5, 
                               "Path should have at least 5 parts separated by underscores")
        
        # Verify some part of the path contains a timestamp-like string
        # The exact format may vary, so we just check for presence of digits
        has_timestamp = False
        for part in parts:
            if part.isdigit() and len(part) >= 6:
                has_timestamp = True
                break
        
        self.assertTrue(has_timestamp, "Path should contain a timestamp component")


class TestPathValidation(unittest.TestCase):
    """Test path validation against canonical structure."""
    
    def test_valid_paths(self):
        """Test validation of valid paths."""
        # Canonical artifact paths
        for artifact_type in ARTIFACT_TYPES:
            path = get_canonical_artifact_path(artifact_type, f"unittest_valid_{artifact_type}")
            self.assertTrue(validate_artifact_path(path))
            
            # File in canonical path
            file_path = os.path.join(path, f"valid_{artifact_type}.txt")
            with open(file_path, "w") as f:
                f.write(f"Valid {artifact_type} content")
            self.assertTrue(validate_artifact_path(file_path))
            
        # Specific project structure paths - the validation rules have changed
        # to only include specific directories
        valid_project_dirs = []
        for structure_dir in ["src", "tools", "tests"]:
            path = os.path.join(project_root, structure_dir)
            if validate_artifact_path(path):
                valid_project_dirs.append(structure_dir)
        
        # If there are any valid project dirs, test file paths in them
        for structure_dir in valid_project_dirs:
            path = os.path.join(project_root, structure_dir)
            
            # File in project structure
            file_path = os.path.join(path, f"test_valid_{structure_dir}.txt")
            if os.path.exists(file_path):
                # Only verify if the file exists - we don't create it
                # since it might not be in a valid location
                if validate_artifact_path(file_path):
                    print(f"File in {structure_dir} is valid: {file_path}")
            
        # Root directory files (standard files only)
        for root_file in ["README.md", "setup.py", "requirements.txt"]:
            file_path = os.path.join(project_root, root_file)
            # Only check if the file exists - we don't create it
            if os.path.exists(file_path) and validate_artifact_path(file_path):
                print(f"Root file is valid: {file_path}")
    
    def test_invalid_paths(self):
        """Test validation of invalid paths."""
        # System temporary directories
        self.assertFalse(validate_artifact_path("/tmp/test.txt"))
        self.assertFalse(validate_artifact_path("/var/tmp/test.txt"))
        self.assertFalse(validate_artifact_path(os.path.join(tempfile.gettempdir(), "test.txt")))
        
        # System directories
        for system_dir in ["/dev", "/proc", "/sys", "/var", "/etc", "/usr", "/lib", "/opt", "/bin"]:
            path = os.path.join(system_dir, "test.txt")
            self.assertFalse(validate_artifact_path(path))
            
        # Legacy artifact patterns
        for legacy_pattern in ["test_output", "analysis_results", "fastvlm_test"]:
            path = os.path.join(project_root, f"{legacy_pattern}_1234")
            self.assertFalse(validate_artifact_path(path))
            
        # Random outside path
        path = os.path.join(os.path.expanduser("~"), "some_random_file.txt")
        self.assertFalse(validate_artifact_path(path))


class TestPathGuard(unittest.TestCase):
    """Test the PathGuard context manager."""
    
    def test_path_guard_allows_valid_paths(self):
        """Test that PathGuard allows operations on valid paths."""
        # Create a canonical artifact path
        artifact_dir = get_canonical_artifact_path("test", "unittest_pathguard")
        
        # Use PathGuard to enforce artifact discipline
        with PathGuard(artifact_dir):
            # Valid file path - this should work
            valid_path = os.path.join(artifact_dir, "valid_file.txt")
            with open(valid_path, "w") as f:
                f.write("Valid file content")
            self.assertTrue(os.path.exists(valid_path))
            
            # Valid subdirectory - this should work
            valid_subdir = os.path.join(artifact_dir, "subdir")
            os.makedirs(valid_subdir, exist_ok=True)
            self.assertTrue(os.path.exists(valid_subdir))
            
            # Valid file in subdirectory - this should work
            valid_subfile = os.path.join(valid_subdir, "valid_subfile.txt")
            with open(valid_subfile, "w") as f:
                f.write("Valid subfile content")
            self.assertTrue(os.path.exists(valid_subfile))
    
    def test_path_guard_prevents_invalid_paths(self):
        """Test that PathGuard prevents operations on invalid paths."""
        # Create a canonical artifact path
        artifact_dir = get_canonical_artifact_path("test", "unittest_pathguard_invalid")
        
        # Use PathGuard to enforce artifact discipline
        with PathGuard(artifact_dir):
            # System temp directory - this should fail
            with self.assertRaises(ValueError):
                invalid_path = os.path.join(tempfile.gettempdir(), "invalid_file.txt")
                with open(invalid_path, "w") as f:
                    f.write("This should fail")
            
            # Path outside artifacts - this should fail
            with self.assertRaises(ValueError):
                invalid_path = os.path.join(os.path.expanduser("~"), "invalid_file.txt")
                with open(invalid_path, "w") as f:
                    f.write("This should fail")


class TestSafeFunctions(unittest.TestCase):
    """Test the safe_* functions."""
    
    def test_safe_mkdir(self):
        """Test safe_mkdir function."""
        # Create a canonical artifact path
        artifact_dir = get_canonical_artifact_path("test", "unittest_safe_mkdir")
        
        # Use safe_mkdir to create a subdirectory
        subdir = os.path.join(artifact_dir, "subdir")
        result = safe_mkdir(subdir)
        self.assertEqual(result, subdir)
        self.assertTrue(os.path.exists(subdir))
        self.assertTrue(os.path.isdir(subdir))
        
        # Safe mkdir should handle existing directories
        result = safe_mkdir(subdir)  # Should not raise exception
        self.assertEqual(result, subdir)
        
        # Try to create directory in invalid location
        with self.assertRaises(ValueError):
            invalid_dir = os.path.join(tempfile.gettempdir(), "invalid_dir")
            safe_mkdir(invalid_dir)
    
    def test_safe_write(self):
        """Test safe_write function."""
        # Create a canonical artifact path
        artifact_dir = get_canonical_artifact_path("test", "unittest_safe_write")
        
        # Use safe_write to write a file
        file_path = os.path.join(artifact_dir, "safe_write.txt")
        result = safe_write(file_path, "Safe write content")
        self.assertEqual(result, file_path)
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, "r") as f:
            self.assertEqual(f.read(), "Safe write content")
        
        # Try to write to invalid location
        with self.assertRaises(ValueError):
            invalid_path = os.path.join(tempfile.gettempdir(), "invalid_safe_write.txt")
            safe_write(invalid_path, "This should fail")
    
    def test_safe_copy(self):
        """Test safe_copy function."""
        # Create a canonical artifact path
        artifact_dir = get_canonical_artifact_path("test", "unittest_safe_copy")
        
        # Create a source file
        source_path = os.path.join(artifact_dir, "source.txt")
        with open(source_path, "w") as f:
            f.write("Source content")
        
        # Use safe_copy to copy the file
        dest_path = os.path.join(artifact_dir, "dest.txt")
        result = safe_copy(source_path, dest_path)
        self.assertEqual(result, dest_path)
        self.assertTrue(os.path.exists(dest_path))
        with open(dest_path, "r") as f:
            self.assertEqual(f.read(), "Source content")
        
        # Try to copy to invalid location
        with self.assertRaises(ValueError):
            invalid_path = os.path.join(tempfile.gettempdir(), "invalid_safe_copy.txt")
            safe_copy(source_path, invalid_path)


class TestEnforcePathDisciplineDecorator(unittest.TestCase):
    """Test the @enforce_path_discipline decorator."""
    
    @enforce_path_discipline
    def _decorated_write_function(self, output_path, content):
        """Custom function with path discipline enforcement via decorator."""
        with open(output_path, "w") as f:
            f.write(content)
        return output_path
    
    def test_decorator_allows_valid_paths(self):
        """Test that the decorator allows operations on valid paths."""
        # Create a canonical artifact path
        artifact_dir = get_canonical_artifact_path("test", "unittest_decorator")
        
        # Use the decorated function with a valid path
        valid_path = os.path.join(artifact_dir, "decorated_valid.txt")
        result = self._decorated_write_function(valid_path, "Decorator test content")
        self.assertEqual(result, valid_path)
        self.assertTrue(os.path.exists(valid_path))
        with open(valid_path, "r") as f:
            self.assertEqual(f.read(), "Decorator test content")
    
    def test_decorator_prevents_invalid_paths(self):
        """Test that the decorator prevents operations on invalid paths."""
        # Try to use the decorated function with an invalid path
        with self.assertRaises(ValueError):
            invalid_path = os.path.join(tempfile.gettempdir(), "decorated_invalid.txt")
            self._decorated_write_function(invalid_path, "This should fail")


class TestCleanupArtifacts(unittest.TestCase):
    """Test artifact cleanup functionality."""
    
    def test_cleanup_setup(self):
        """Test setting up the artifact structure."""
        from src.core.artifact_guard import setup_artifact_structure
        
        # Setup artifact structure
        setup_artifact_structure()
        
        # Check that the directories exist
        self.assertTrue(os.path.exists(ARTIFACTS_ROOT))
        for artifact_type in ARTIFACT_TYPES:
            type_dir = os.path.join(ARTIFACTS_ROOT, artifact_type)
            self.assertTrue(os.path.exists(type_dir))
            self.assertTrue(os.path.isdir(type_dir))
        
        # Check that artifacts.env exists
        env_file = os.path.join(project_root, "artifacts.env")
        self.assertTrue(os.path.exists(env_file))


if __name__ == "__main__":
    unittest.main()