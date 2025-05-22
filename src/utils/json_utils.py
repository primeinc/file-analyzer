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
    """Class for validating and extracting JSON from various text formats.
    
    This class provides a multi-strategy approach to JSON extraction:
    1. Direct JSON parsing for well-formed JSON
    2. Pattern matching for flat JSON with expected fields (limitations with nested objects)
    3. General JSON object pattern matching
    4. Advanced balanced bracket algorithm for complex nested structures
    
    The strategies are tried in order, with each subsequent strategy being more robust
    but potentially less precise for our specific output format.
    """
    
    @staticmethod
    def extract_json_from_text(text):
        """
        Extract JSON from text using robust extraction methods.
        
        This method employs a comprehensive approach to finding valid JSON:
        1. Parse the entire text as JSON if possible
        2. Find all potential JSON objects with proper nesting support
        3. Extract largest valid JSON object from the text
        
        Args:
            text (str): The text that may contain JSON
            
        Returns:
            dict: Extracted JSON object or None if extraction fails
        """
        if not text:
            return None
            
        # Strategy 1: Try to parse the entire text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract all potential JSON objects
        potential_jsons = []
        
        # Find all opening braces
        start_positions = [i for i, char in enumerate(text) if char == '{']
        
        for start_pos in start_positions:
            # Track nesting level of braces
            nest_level = 0
            in_string = False
            escape_next = False
            
            for i in range(start_pos, len(text)):
                char = text[i]
                
                # Handle string boundaries and escaping
                if char == '"' and not escape_next:
                    in_string = not in_string
                elif char == '\\' and in_string:
                    escape_next = True
                else:
                    escape_next = False
                
                # Only count braces outside of strings
                if not in_string:
                    if char == '{':
                        nest_level += 1
                    elif char == '}':
                        nest_level -= 1
                        
                        # Found a complete JSON object
                        if nest_level == 0:
                            json_str = text[start_pos:i+1]
                            try:
                                json_obj = json.loads(json_str)
                                potential_jsons.append(json_obj)
                                break  # Found a valid JSON, move to next starting position
                            except json.JSONDecodeError:
                                pass  # Not valid JSON, continue searching
                
                # If the nesting goes negative, this isn't valid
                if nest_level < 0:
                    break
        
        # If we found potential JSON objects, select the most relevant one
        if potential_jsons:
            # First look for objects with required fields for vision output
            for json_obj in potential_jsons:
                if isinstance(json_obj, dict) and "description" in json_obj and "tags" in json_obj:
                    return json_obj
                    
            # Then check for objects with any of our expected fields
            expected_fields = ["description", "tags", "objects", "text", "document_type"]
            for json_obj in potential_jsons:
                if isinstance(json_obj, dict) and any(field in json_obj for field in expected_fields):
                    return json_obj
            
            # If no objects with expected fields, return the largest one
            return max(potential_jsons, key=lambda x: len(json.dumps(x)) if isinstance(x, dict) else 0)
        
        # Strategy 3: More aggressive extraction for strings with escaped characters
        # Find sequences that look like JSON by using regex (with safety limits)
        import re
        # Limit text size to prevent regex catastrophic backtracking
        if len(text) > 10000:
            text = text[:10000]  # Truncate very long text
        
        # Look for more complex JSON-like patterns that might have nested structure
        json_pattern = r'(\{(?:[^{}]|\"(?:\\.|[^\"])*\")*\})'
        try:
            matches = re.findall(json_pattern, text, re.DOTALL)
        except re.error:
            matches = []  # Skip regex if it fails
        
        # Try each potential match
        for match in matches:
            # Look for our expected fields
            if ('"description"' in match and '"tags"' in match) or any(f'"{field}"' in match for field in ["objects", "text", "document_type"]):
                # Try multiple approaches to parse potentially malformed JSON
                for parse_attempt in range(3):  # Try different parsing strategies
                    try:
                        if parse_attempt == 0:
                            # Standard parsing
                            json_obj = json.loads(match)
                            return json_obj
                        elif parse_attempt == 1:
                            # Fix common JSON errors - escaped quotes
                            # Replace escaped quotes with a temporary placeholder
                            temp = match.replace('\\"', '§ESCAPED_QUOTE§')
                            # Fix the JSON structure
                            temp = temp.replace('§ESCAPED_QUOTE§', '\\"')
                            json_obj = json.loads(temp)
                            return json_obj
                        elif parse_attempt == 2:
                            # More aggressive fixing for problematic escaping
                            # First normalize all backslashes
                            temp = match.replace('\\\\', '§DOUBLE_BACKSLASH§')
                            temp = temp.replace('\\"', '§ESCAPED_QUOTE§')
                            # Replace with proper escaping
                            temp = temp.replace('§ESCAPED_QUOTE§', '\\"')
                            temp = temp.replace('§DOUBLE_BACKSLASH§', '\\\\')
                            json_obj = json.loads(temp)
                            return json_obj
                    except json.JSONDecodeError:
                        continue  # Try next parsing strategy
                        
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

def process_model_output(output, mode="describe", metadata=None, attempt_count=0, retry_prompt=None):
    """
    Process model output to extract and validate JSON.
    
    Args:
        output (str): The raw output from the model
        mode (str): The analysis mode (describe, detect, document)
        metadata (dict): Additional metadata to include
        attempt_count (int): Actual number of attempts made, including this one
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
        
        # Record the actual attempt count
        if attempt_count > 0:
            base_metadata["attempts"] = attempt_count
            
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
    
    # Record the actual attempt count
    if attempt_count > 0:
        base_metadata["attempts"] = attempt_count
        
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