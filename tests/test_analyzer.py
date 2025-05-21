#!/usr/bin/env python3
"""
Tests for the FileAnalyzer class

This script tests the FileAnalyzer class in src/analyzer.py to ensure:
1. Proper initialization and configuration
2. Analysis methods execute correctly
3. Results are properly stored in the expected canonical artifact paths
4. Error handling works as expected

Usage:
    python3 tests/test_analyzer.py
"""

import os
import sys
import tempfile
import unittest
import json
import shutil
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the artifact guard components
from src.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard,
    ARTIFACTS_ROOT
)

# Import the FileAnalyzer class
from src.analyzer import FileAnalyzer

class TestFileAnalyzer(unittest.TestCase):
    """Tests for the FileAnalyzer class"""
    
    def setUp(self):
        """Set up for the tests"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp(prefix="file_analyzer_test_")
        
        # Create some test files
        self.text_file = os.path.join(self.test_dir, "test_file.txt")
        with open(self.text_file, "w") as f:
            f.write("This is a test file for file analyzer testing.")
        
        # Create a test image file
        self.image_file = os.path.join(self.test_dir, "test_image.jpg")
        with open(self.image_file, "wb") as f:
            # Simple empty JPEG file header
            f.write(b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xFF\xDB\x00C')
        
        # Create a test binary file
        self.binary_file = os.path.join(self.test_dir, "test_binary.bin")
        with open(self.binary_file, "wb") as f:
            f.write(b'\x7FELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        
        # Initialize the FileAnalyzer
        self.analyzer = FileAnalyzer()
    
    def tearDown(self):
        """Clean up after the tests"""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test that the FileAnalyzer initializes correctly"""
        # Check that the analyzer has a results dict
        self.assertIsInstance(self.analyzer.results, dict)
        
        # Try with a config
        config = {"test_config": True}
        analyzer_with_config = FileAnalyzer(config)
        self.assertEqual(analyzer_with_config.config, config)
    
    def test_metadata_extraction(self):
        """Test the metadata extraction functionality"""
        # Create a canonical artifact path for testing
        artifact_dir = get_canonical_artifact_path("test", "metadata_test")
        
        # Run the metadata extraction
        result = self.analyzer._extract_metadata(self.test_dir, artifact_dir)
        
        # Check that the method returns a valid path
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        
        # Check that the results dictionary was updated correctly
        self.assertIn("metadata", self.analyzer.results)
        self.assertEqual(self.analyzer.results["metadata"]["status"], "success")
        
        # Verify the output is a JSON file with expected structure
        with open(result, 'r') as f:
            data = json.load(f)
            self.assertIn("files", data)
            self.assertIn("analysis_info", data)
    
    def test_search_content(self):
        """Test the search content functionality"""
        # Create a canonical artifact path for testing
        artifact_dir = get_canonical_artifact_path("test", "search_test")
        
        # Add more content to the text file to ensure search will find something
        with open(self.text_file, "a") as f:
            f.write("\nThis is a line with a SEARCHTERM that should be found.")
        
        # Run the search
        search_term = "SEARCHTERM"
        result = self.analyzer._search_content(self.test_dir, search_term, artifact_dir)
        
        # Check that the method returns a valid path
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        
        # Check that the results dictionary was updated correctly
        self.assertIn("search", self.analyzer.results)
        self.assertEqual(self.analyzer.results["search"]["status"], "success")
        self.assertEqual(self.analyzer.results["search"]["search_text"], search_term)
        
        # Verify that we found at least one match
        self.assertGreater(self.analyzer.results["search"]["match_count"], 0)
        
        # Test with an empty search term (should be skipped)
        result = self.analyzer._search_content(self.test_dir, "", artifact_dir)
        self.assertIsNone(result)
        self.assertEqual(self.analyzer.results["search"]["status"], "skipped")
    
    def test_main_analyze_method(self):
        """Test the main analyze method that coordinates all analyses"""
        # Set up options for the analysis
        options = {
            'metadata': True,
            'duplicates': False,
            'ocr': False,
            'virus': False,
            'search': True,
            'search_text': 'test',
            'binary': False,
            'vision': False
        }
        
        # Run the analyze method
        results = self.analyzer.analyze(self.test_dir, options)
        
        # Check that results were returned and match the instance results
        self.assertEqual(results, self.analyzer.results)
        
        # Verify the expected results are present
        self.assertIn("metadata", results)
        self.assertEqual(results["metadata"]["status"], "success")
        
        self.assertIn("search", results)
        self.assertEqual(results["search"]["status"], "success")
        
        # Check that other analyses (not enabled) are not in results
        self.assertNotIn("duplicates", results)
        self.assertNotIn("ocr", results)
        self.assertNotIn("virus", results)
        self.assertNotIn("binary", results)
        self.assertNotIn("vision", results)
        
        # Check that output files were created in canonical paths
        metadata_file = results["metadata"]["output_file"]
        self.assertTrue(validate_artifact_path(metadata_file))
        
        search_file = results["search"]["output_file"]
        self.assertTrue(validate_artifact_path(search_file))
    
    def test_handle_nonexistent_path(self):
        """Test that the analyzer handles nonexistent paths gracefully"""
        # Create an options dictionary
        options = {
            'metadata': True,
        }
        
        # Run the analyzer with a nonexistent path
        nonexistent_path = os.path.join(self.test_dir, "does_not_exist")
        
        # This shouldn't crash, but should fail gracefully
        results = self.analyzer.analyze(nonexistent_path, options)
        
        # Check that metadata extraction failed with an error
        self.assertIn("metadata", results)
        self.assertEqual(results["metadata"]["status"], "error")
        self.assertIn("error", results["metadata"])

if __name__ == "__main__":
    unittest.main()