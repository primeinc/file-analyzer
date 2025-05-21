#!/usr/bin/env python3
"""
Tests for JSON Utilities

This module tests the json_utils.py module which provides utilities for
extracting, validating, and processing JSON from model outputs.
"""

import os
import sys
import json
import time
import unittest
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the JSON utilities
from src.utils.json_utils import (
    JSONValidator, 
    process_model_output, 
    get_json_prompt, 
    JSON_PROMPT_TEMPLATES
)

class TestJSONValidator(unittest.TestCase):
    """Test the JSONValidator class"""
    
    def test_extract_json_from_text_direct_parsing(self):
        """Test direct JSON parsing (strategy 1)"""
        # Valid JSON - direct parsing
        valid_json = '{"description": "A test image", "tags": ["test", "image"]}'
        result = JSONValidator.extract_json_from_text(valid_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "A test image")
        self.assertEqual(result["tags"], ["test", "image"])
        
        # Invalid JSON
        invalid_json = '{"description": "A test image", "tags": ["test", "image"]'
        result = JSONValidator.extract_json_from_text(invalid_json)
        self.assertIsNone(result)
        
        # Empty input
        result = JSONValidator.extract_json_from_text("")
        self.assertIsNone(result)
        
        # None input
        result = JSONValidator.extract_json_from_text(None)
        self.assertIsNone(result)
    
    def test_extract_json_from_text_balanced_brace_extraction(self):
        """Test JSON extraction with balanced brace tracking (strategy 2)"""
        # JSON object embedded in text
        text_with_json = "Here is the result: {'description': 'A cat', 'tags': ['animal', 'pet']} end of response."
        result = JSONValidator.extract_json_from_text(text_with_json)
        self.assertIsNone(result)  # This should fail as it uses single quotes
        
        # Text with valid JSON using double quotes
        text_with_valid_json = 'Here is the result: {"description": "A cat", "tags": ["animal", "pet"]} end of response.'
        result = JSONValidator.extract_json_from_text(text_with_valid_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "A cat")
        self.assertEqual(result["tags"], ["animal", "pet"])
        
        # Text with escaped quotes in JSON
        text_with_escaped_quotes = 'Here is: {"description": "A \\"quoted\\" text", "tags": ["test"]} end.'
        result = JSONValidator.extract_json_from_text(text_with_escaped_quotes)
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], 'A "quoted" text')
        
        # Text with multiple JSON objects - should find the one with expected fields
        text_with_multiple_json = '''
        First: {"random": "data"} 
        Second: {"description": "The image", "tags": ["valid"]}
        Third: {"other": "data"}
        '''
        result = JSONValidator.extract_json_from_text(text_with_multiple_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["description"], "The image")
        
        # Nested JSON objects
        nested_json = '''
        {"outer": {"description": "Nested object", "tags": ["nested"]}}
        '''
        result = JSONValidator.extract_json_from_text(nested_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["outer"]["description"], "Nested object")
    
    def test_validate_json_structure(self):
        """Test JSON structure validation"""
        # Valid structure for describe mode
        valid_describe = {"description": "A test image", "tags": ["test", "image"]}
        self.assertTrue(JSONValidator.validate_json_structure(valid_describe, model_type="describe"))
        
        # Valid structure for detect mode
        valid_detect = {"objects": [{"name": "cat", "location": "center"}], "description": "A cat"}
        self.assertTrue(JSONValidator.validate_json_structure(valid_detect, model_type="detect"))
        
        # Valid structure for document mode
        valid_document = {"text": "Sample text", "document_type": "letter"}
        self.assertTrue(JSONValidator.validate_json_structure(valid_document, model_type="document"))
        
        # Invalid structure - missing fields
        invalid_describe = {"description": "A test image"}  # Missing tags
        self.assertFalse(JSONValidator.validate_json_structure(invalid_describe, model_type="describe"))
        
        # Invalid input types
        self.assertFalse(JSONValidator.validate_json_structure(None))
        self.assertFalse(JSONValidator.validate_json_structure("not a dict"))
        self.assertFalse(JSONValidator.validate_json_structure([]))
        
        # Custom expected fields
        custom_fields = ["field1", "field2"]
        valid_custom = {"field1": "value1", "field2": "value2", "extra": "value3"}
        self.assertTrue(JSONValidator.validate_json_structure(valid_custom, expected_fields=custom_fields))
        
        invalid_custom = {"field1": "value1", "extra": "value3"}  # Missing field2
        self.assertFalse(JSONValidator.validate_json_structure(invalid_custom, expected_fields=custom_fields))
    
    def test_add_metadata(self):
        """Test adding metadata to JSON results"""
        # Basic JSON data
        json_data = {"description": "A test image", "tags": ["test", "image"]}
        
        # Add basic metadata
        with patch('time.strftime', return_value="2023-01-01 12:00:00"):
            result = JSONValidator.add_metadata(json_data)
            self.assertIsNotNone(result)
            self.assertIn("metadata", result)
            self.assertEqual(result["metadata"]["timestamp"], "2023-01-01 12:00:00")
            
            # Original data should be preserved
            self.assertEqual(result["description"], "A test image")
            self.assertEqual(result["tags"], ["test", "image"])
            
            # Custom metadata
            custom_metadata = {"model": "test_model", "execution_time": 0.5}
            result_with_custom = JSONValidator.add_metadata(json_data, custom_metadata)
            self.assertEqual(result_with_custom["metadata"]["model"], "test_model")
            self.assertEqual(result_with_custom["metadata"]["execution_time"], 0.5)
            self.assertEqual(result_with_custom["metadata"]["timestamp"], "2023-01-01 12:00:00")
            
            # Adding to existing metadata
            json_with_metadata = {
                "description": "A test image", 
                "tags": ["test", "image"],
                "metadata": {"existing": "value"}
            }
            result_with_existing = JSONValidator.add_metadata(json_with_metadata, custom_metadata)
            self.assertEqual(result_with_existing["metadata"]["existing"], "value")
            self.assertEqual(result_with_existing["metadata"]["model"], "test_model")
            
            # None input
            self.assertIsNone(JSONValidator.add_metadata(None))
    
    def test_format_fallback_response(self):
        """Test formatting fallback responses"""
        # Basic text response
        text = "This is a fallback text response"
        
        # Format without custom metadata
        with patch('time.strftime', return_value="2023-01-01 12:00:00"):
            result = JSONValidator.format_fallback_response(text)
            self.assertIsNotNone(result)
            self.assertEqual(result["text"], text)
            self.assertEqual(result["metadata"]["timestamp"], "2023-01-01 12:00:00")
            self.assertTrue(result["metadata"]["json_parsing_failed"])
            
            # With custom metadata
            custom_metadata = {"model": "test_model", "execution_time": 0.5}
            result_with_custom = JSONValidator.format_fallback_response(text, custom_metadata)
            self.assertEqual(result_with_custom["text"], text)
            self.assertEqual(result_with_custom["metadata"]["model"], "test_model")
            self.assertEqual(result_with_custom["metadata"]["execution_time"], 0.5)
            self.assertTrue(result_with_custom["metadata"]["json_parsing_failed"])

class TestProcessModelOutput(unittest.TestCase):
    """Test the process_model_output function"""
    
    def test_successful_json_processing(self):
        """Test processing valid JSON output"""
        # Valid JSON for describe mode
        valid_describe = '{"description": "A test image", "tags": ["test", "image"]}'
        
        with patch('time.strftime', return_value="2023-01-01 12:00:00"):
            result = process_model_output(valid_describe, mode="describe")
            self.assertIsNotNone(result)
            self.assertEqual(result["description"], "A test image")
            self.assertEqual(result["tags"], ["test", "image"])
            self.assertEqual(result["metadata"]["mode"], "describe")
            
            # Valid JSON for detect mode
            valid_detect = '{"objects": [{"name": "cat", "location": "center"}], "description": "A cat"}'
            result = process_model_output(valid_detect, mode="detect")
            self.assertIsNotNone(result)
            self.assertEqual(result["objects"][0]["name"], "cat")
            self.assertEqual(result["metadata"]["mode"], "detect")
            
            # Valid JSON for document mode
            valid_document = '{"text": "Sample text", "document_type": "letter"}'
            result = process_model_output(valid_document, mode="document")
            self.assertIsNotNone(result)
            self.assertEqual(result["text"], "Sample text")
            self.assertEqual(result["metadata"]["mode"], "document")
    
    def test_invalid_json_processing(self):
        """Test processing invalid JSON output"""
        # Invalid JSON format
        invalid_json = '{"description": "A test image", "tags": ["test", "image]'  # Missing closing quote
        
        with patch('time.strftime', return_value="2023-01-01 12:00:00"):
            result = process_model_output(invalid_json, mode="describe")
            self.assertIsNotNone(result)
            self.assertEqual(result["text"], invalid_json)
            self.assertEqual(result["metadata"]["mode"], "describe")
            self.assertTrue(result["metadata"]["json_parsing_failed"])
            
            # Valid JSON but missing required fields
            missing_fields = '{"description": "A test image"}'  # Missing tags
            result = process_model_output(missing_fields, mode="describe")
            self.assertIsNotNone(result)
            self.assertEqual(result["text"], missing_fields)
            self.assertTrue(result["metadata"]["json_parsing_failed"])
    
    def test_process_with_metadata_and_retry(self):
        """Test processing with metadata and retry tracking"""
        # Valid JSON with metadata and retry information
        valid_json = '{"description": "A retry result", "tags": ["retry", "test"]}'
        custom_metadata = {"model": "test_model", "execution_time": 0.5}
        
        with patch('time.strftime', return_value="2023-01-01 12:00:00"):
            # Test with attempt count
            result = process_model_output(
                valid_json, 
                mode="describe", 
                metadata=custom_metadata, 
                attempt_count=2,
                retry_prompt="Retry prompt"
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["description"], "A retry result")
            self.assertEqual(result["metadata"]["model"], "test_model")
            self.assertEqual(result["metadata"]["execution_time"], 0.5)
            self.assertEqual(result["metadata"]["attempts"], 2)
            
            # Test with extracted flag (when original isn't pure JSON)
            text_with_json = 'The JSON result is: {"description": "A test", "tags": ["test"]}'
            result = process_model_output(text_with_json, mode="describe")
            self.assertIsNotNone(result)
            self.assertEqual(result["description"], "A test")
            self.assertTrue(result["metadata"].get("extracted", False))

class TestJSONPrompts(unittest.TestCase):
    """Test the JSON prompt templates and selection"""
    
    def test_get_json_prompt(self):
        """Test getting JSON prompts for different modes"""
        # Default describe mode
        describe_prompt = get_json_prompt(mode="describe")
        self.assertEqual(describe_prompt, JSON_PROMPT_TEMPLATES["describe"])
        
        # Detect mode
        detect_prompt = get_json_prompt(mode="detect")
        self.assertEqual(detect_prompt, JSON_PROMPT_TEMPLATES["detect"])
        
        # Document mode
        document_prompt = get_json_prompt(mode="document")
        self.assertEqual(document_prompt, JSON_PROMPT_TEMPLATES["document"])
        
        # Unknown mode - should return describe prompt
        unknown_prompt = get_json_prompt(mode="unknown")
        self.assertEqual(unknown_prompt, JSON_PROMPT_TEMPLATES["describe"])
        
        # Retry prompt for any mode
        retry_prompt = get_json_prompt(mode="describe", retry_attempt=1)
        self.assertEqual(retry_prompt, JSON_PROMPT_TEMPLATES["retry"])
        
        retry_prompt = get_json_prompt(mode="detect", retry_attempt=2)
        self.assertEqual(retry_prompt, JSON_PROMPT_TEMPLATES["retry"])

if __name__ == "__main__":
    unittest.main()