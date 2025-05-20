#!/usr/bin/env python3
"""
JSON Utilities for Vision Model Output Processing

This module provides centralized JSON handling for vision model outputs:

1. Robust JSON extraction from text with comprehensive pattern matching
2. Validation of expected fields for different output types
3. Retry logic for handling invalid model responses
4. Consistent formatting of metadata and result structure

These utilities are used by various modules including:
- fastvlm_json.py
- vision_analyzer.py
- file_analyzer.py
"""

import json
import re
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JSONValidator:
    """Class for validating and extracting JSON from various text formats."""
    
    @staticmethod
    def extract_json_from_text(text):
        """
        Extract JSON from text using sophisticated pattern matching.
        
        This method uses multiple strategies to find valid JSON:
        1. First attempts to match complete JSON objects with expected fields
        2. Falls back to balanced bracket search for any JSON object
        3. Handles nested objects, arrays, and quoted strings properly
        
        Args:
            text (str): The text that may contain JSON
            
        Returns:
            dict: Extracted JSON object or None if extraction fails
        """
        if not text:
            return None
            
        # Strategy 1: Try direct JSON parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Look for common vision result patterns with key fields
        # This regex specifically looks for our vision output format with description and tags
        vision_pattern = r'\{(?:[^{}]|"(?:\\.|[^"\\])*")*"description"(?:[^{}]|"(?:\\.|[^"\\])*")*"tags"(?:[^{}]|"(?:\\.|[^"\\])*")*\}'
        match = re.search(vision_pattern, text)
        if match:
            try:
                potential_json = match.group(0)
                return json.loads(potential_json)
            except json.JSONDecodeError:
                pass
                
        # Strategy 3: Find any JSON-like structure with balanced brackets
        # This is more general but might capture unrelated JSON
        json_pattern = r'\{(?:[^{}]|"(?:\\.|[^"\\])*")*\}'
        match = re.search(json_pattern, text)
        if match:
            try:
                potential_json = match.group(0)
                return json.loads(potential_json)
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Advanced balanced bracket search
        # This handles nested objects and arrays
        stack = []
        start_index = -1
        
        for i, char in enumerate(text):
            if char == '{' and (i == 0 or text[i-1] != '\\'):
                if not stack:  # Mark the start of potential JSON
                    start_index = i
                stack.append('{')
            elif char == '}' and (i == 0 or text[i-1] != '\\'):
                if stack and stack[-1] == '{':
                    stack.pop()
                    if not stack:  # We've found a complete balanced section
                        try:
                            potential_json = text[start_index:i+1]
                            return json.loads(potential_json)
                        except json.JSONDecodeError:
                            # Continue searching
                            start_index = -1
        
        # No valid JSON found
        return None
    
    @staticmethod
    def validate_json_structure(json_data, expected_fields=None, model_type=None):
        """
        Validate that JSON data contains expected fields for the given model type.
        
        Args:
            json_data (dict): The JSON data to validate
            expected_fields (list): List of expected field names
            model_type (str): Type of model (for specialized validation)
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not json_data or not isinstance(json_data, dict):
            return False
            
        # Default expected fields for vision models
        if expected_fields is None:
            if model_type == "detect":
                expected_fields = ["objects", "description"]
            elif model_type == "document":
                expected_fields = ["text", "document_type"]
            else:  # Default to description mode
                expected_fields = ["description", "tags"]
        
        # Check if all expected fields exist
        return all(field in json_data for field in expected_fields)
    
    @staticmethod
    def add_metadata(json_data, metadata=None):
        """
        Add or update metadata in JSON result.
        
        Args:
            json_data (dict): The JSON data to update
            metadata (dict): Metadata to add
            
        Returns:
            dict: Updated JSON data with metadata
        """
        if not json_data:
            return None
            
        # Create a copy to avoid modifying the original
        result = json_data.copy()
        
        # Initialize metadata if it doesn't exist
        if "metadata" not in result:
            result["metadata"] = {}
            
        # Add standard metadata fields if not provided
        if metadata:
            result["metadata"].update(metadata)
            
        # Ensure timestamp is present
        if "timestamp" not in result["metadata"]:
            result["metadata"]["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
        return result
    
    @staticmethod
    def format_fallback_response(text, metadata=None):
        """
        Format a fallback response when JSON parsing fails.
        
        Args:
            text (str): Original text response
            metadata (dict): Additional metadata
            
        Returns:
            dict: Formatted response with text and metadata
        """
        response = {
            "text": text,
            "metadata": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "json_parsing_failed": True
            }
        }
        
        if metadata:
            response["metadata"].update(metadata)
            
        return response

# Common prompt templates for JSON output
JSON_PROMPT_TEMPLATES = {
    "describe": """Describe this image in a highly detailed, dense manner. 
    Output your answer ONLY as a valid JSON object with two fields:
    - 'description': a verbose, information-dense description.
    - 'tags': a list of all applicable tags as an array of strings.
    
    Your entire response MUST be a valid, parseable JSON object.""",
    
    "detect": """Analyze the objects in this image.
    Output your answer ONLY as a valid JSON object with these fields:
    - 'objects': an array of objects detected, each with 'name' and 'location' properties
    - 'description': a brief scene description
    
    Your entire response MUST be a valid, parseable JSON object.""",
    
    "document": """Extract all text content from this document image.
    Output your answer ONLY as a valid JSON object with these fields:
    - 'text': all the extracted text content, preserving layout where possible
    - 'document_type': the type of document detected
    
    Your entire response MUST be a valid, parseable JSON object.""",
    
    # More robust prompts for retry attempts
    "retry": """Your ENTIRE response must be VALID JSON. Do NOT include any text before or after the JSON.
    Describe this image as a JSON object with exactly these fields:
    {"description": "detailed description here", "tags": ["tag1", "tag2", "etc"]}
    No other text, just the JSON object."""
}

def process_model_output(output, mode="describe", metadata=None, max_retries=0, retry_prompt=None):
    """
    Process model output to extract and validate JSON.
    
    Args:
        output (str): The raw output from the model
        mode (str): The analysis mode (describe, detect, document)
        metadata (dict): Additional metadata to include
        max_retries (int): Number of retries attempted (for metadata)
        retry_prompt (str): Prompt used for retry (for debugging)
        
    Returns:
        dict: Processed JSON data or formatted fallback
    """
    # Try to extract JSON
    json_data = JSONValidator.extract_json_from_text(output)
    
    # Check if extraction was successful and validate structure
    expected_fields = None
    if mode == "detect":
        expected_fields = ["objects", "description"]
    elif mode == "document":
        expected_fields = ["text", "document_type"]
    else:  # Default to description mode
        expected_fields = ["description", "tags"]
    
    if json_data and JSONValidator.validate_json_structure(json_data, expected_fields, mode):
        # Add metadata
        base_metadata = {
            "mode": mode,
        }
        if max_retries > 0:
            base_metadata["attempts"] = max_retries
            
        if metadata:
            base_metadata.update(metadata)
            
        # Mark as extracted if the original wasn't pure JSON
        try:
            json.loads(output)
        except json.JSONDecodeError:
            base_metadata["extracted"] = True
            
        return JSONValidator.add_metadata(json_data, base_metadata)
    
    # If JSON extraction failed, return formatted fallback
    base_metadata = {
        "mode": mode,
        "json_parsing_failed": True
    }
    
    if max_retries > 0:
        base_metadata["attempts"] = max_retries
        
    if metadata:
        base_metadata.update(metadata)
        
    return JSONValidator.format_fallback_response(output, base_metadata)

def get_json_prompt(mode="describe", retry_attempt=0):
    """
    Get the appropriate JSON prompt for the given mode and retry attempt.
    
    Args:
        mode (str): The analysis mode (describe, detect, document)
        retry_attempt (int): The retry attempt number (0 for first attempt)
        
    Returns:
        str: The JSON prompt template
    """
    if retry_attempt > 0:
        return JSON_PROMPT_TEMPLATES["retry"]
    
    return JSON_PROMPT_TEMPLATES.get(mode, JSON_PROMPT_TEMPLATES["describe"])