#!/usr/bin/env python3
"""
Test script for FastVLM JSON validation capabilities.
This script runs tests for the JSON validation and retry logic.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Make sure our modules are in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the module we're testing
from fastvlm_json import run_fastvlm_json_analysis, extract_json_from_text


class TestFastVLMJsonOutput(unittest.TestCase):
    """Test case for FastVLM JSON output functionality."""
    
    def test_json_extraction(self):
        """Test the JSON extraction function."""
        # Test with valid JSON
        valid_json = '{"description": "A photo of a cat.", "tags": ["cat", "animal", "pet"]}'
        result = extract_json_from_text(valid_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "A photo of a cat.")
        
        # Test with JSON embedded in text
        embedded_json = 'Here is the result: {"description": "A photo of a dog.", "tags": ["dog"]} Hope this helps!'
        result = extract_json_from_text(embedded_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "A photo of a dog.")
        
        # Test with invalid input
        invalid_input = "This is not JSON at all."
        result = extract_json_from_text(invalid_input)
        self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_fastvlm_json_valid(self, mock_run):
        """Test with valid JSON response."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.stdout = '{"description": "A test image.", "tags": ["test"]}'
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Test the function
        with patch('os.path.exists', return_value=True):
            result = run_fastvlm_json_analysis("test.jpg", "model_path")
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "A test image.")
        self.assertEqual(result["tags"], ["test"])
        self.assertIn("metadata", result)
    
    @patch('subprocess.run')
    def test_fastvlm_json_retry(self, mock_run):
        """Test retry logic with invalid JSON followed by valid JSON."""
        # Setup mocks for first call (invalid JSON)
        first_process = MagicMock()
        first_process.stdout = "This is not valid JSON"
        first_process.returncode = 0
        
        # Setup mocks for second call (valid JSON)
        second_process = MagicMock()
        second_process.stdout = '{"description": "A retry success.", "tags": ["retry"]}'
        second_process.returncode = 0
        
        # Set up the mock to return different values on successive calls
        mock_run.side_effect = [first_process, second_process]
        
        # Test the function
        with patch('os.path.exists', return_value=True):
            result = run_fastvlm_json_analysis("test.jpg", "model_path", max_retries=2)
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "A retry success.")
        self.assertEqual(result["tags"], ["retry"])
        self.assertIn("metadata", result)
        self.assertEqual(result["metadata"]["attempts"], 2)
    
    @patch('subprocess.run')
    def test_extract_json_from_text(self, mock_run):
        """Test extraction of JSON from text response."""
        # Setup mock
        mock_process = MagicMock()
        mock_process.stdout = 'The image shows: {"description": "An embedded JSON example.", "tags": ["embedded", "json"]}'
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Test the function
        with patch('os.path.exists', return_value=True):
            result = run_fastvlm_json_analysis("test.jpg", "model_path")
        
        # Verify results
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "An embedded JSON example.")
        self.assertEqual(result["tags"], ["embedded", "json"])
        self.assertIn("metadata", result)
        self.assertTrue(result["metadata"]["extracted"])
    
    @patch('subprocess.run')
    def test_json_fallback(self, mock_run):
        """Test fallback to text output when all JSON parsing attempts fail."""
        # Setup mocks for multiple failed attempts
        # Each process will return invalid JSON
        first_process = MagicMock()
        first_process.stdout = "This is not valid JSON"
        first_process.returncode = 0
        
        second_process = MagicMock()
        second_process.stdout = "Still not valid JSON"
        second_process.returncode = 0
        
        third_process = MagicMock()
        third_process.stdout = "Final attempt, still not JSON"
        third_process.returncode = 0
        
        # Set up the mock to return different values on successive calls
        mock_run.side_effect = [first_process, second_process, third_process]
        
        # Test the function with 3 retry attempts
        with patch('os.path.exists', return_value=True):
            result = run_fastvlm_json_analysis("test.jpg", "model_path", max_retries=3)
        
        # Verify fallback to text format
        self.assertIsNotNone(result)
        self.assertIn("text", result)
        self.assertEqual(result["text"], "Final attempt, still not JSON")
        self.assertIn("metadata", result)
        self.assertTrue(result["metadata"]["json_parsing_failed"])
        self.assertEqual(result["metadata"]["attempts"], 3)
    
    @patch('subprocess.run')
    def test_progressively_corrupted_json(self, mock_run):
        """Test JSON validation with progressively corrupted inputs."""
        # Setup mocks for multiple partially corrupted JSON attempts
        first_process = MagicMock()
        first_process.stdout = '{"description": "Almost valid", "tags": ["missing closing bracket"'
        first_process.returncode = 0
        
        second_process = MagicMock()
        second_process.stdout = 'Nearly JSON {"description": "Getting closer", "tags": []}'
        second_process.returncode = 0
        
        third_process = MagicMock()
        third_process.stdout = '{"description": "Valid now", "tags": ["success"]}'
        third_process.returncode = 0
        
        # Set up the mock to return different values on successive calls
        mock_run.side_effect = [first_process, second_process, third_process]
        
        # Test the function
        with patch('os.path.exists', return_value=True):
            result = run_fastvlm_json_analysis("test.jpg", "model_path", max_retries=3)
        
        # Either the second or third attempt might succeed depending on the extraction implementation
        # Our new improved extractor is able to get JSON from the second attempt
        self.assertIsNotNone(result)
        self.assertIn("description", result)
        self.assertIn("tags", result)
        self.assertIn("metadata", result)
        # Check that we have metadata indicating extraction
        self.assertTrue(result["metadata"].get("extracted", False))
        # We should have made at least 2 attempts
        self.assertGreaterEqual(result["metadata"]["attempts"], 2)


if __name__ == "__main__":
    unittest.main()