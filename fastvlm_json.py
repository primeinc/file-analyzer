#!/usr/bin/env python3
"""
FastVLM JSON Output Demo

This script demonstrates FastVLM with JSON-formatted output for better
structured results, including descriptions and tags. It implements robust
JSON validation and retry logic to ensure valid structured output.
"""

import os
import sys
import time
import json
import re
import argparse
import logging
from pathlib import Path

# Make sure our modules are in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# The JSON-formatted prompt template
JSON_PROMPT_TEMPLATE = """Describe this image in a highly detailed, dense manner. 
Output your answer ONLY as a valid JSON object with two fields:
- 'description': a verbose, information-dense description.
- 'tags': a list of all applicable tags as an array of strings.

Your entire response MUST be a valid, parseable JSON object."""

def extract_json_from_text(text):
    """Attempt to extract JSON from text response if it's embedded in other content."""
    # Try to find JSON-like structure using regex
    json_pattern = r'\{[^\{\}]*\"description\"[^\{\}]*\"tags\"[^\{\}]*\}'  
    # Basic pattern to find the likely JSON object with our expected fields
    
    match = re.search(json_pattern, text)
    if match:
        try:
            potential_json = match.group(0)
            return json.loads(potential_json)
        except json.JSONDecodeError:
            pass
    return None

def run_fastvlm_json_analysis(image_path, model_path, prompt=None, max_retries=3):
    """
    Run FastVLM analysis with JSON output and retry logic.
    
    This function provides robust JSON output from FastVLM vision analysis by:
    1. Using JSON-specific prompting to encourage structured output
    2. Implementing retry logic if the initial response isn't valid JSON
    3. Extracting JSON from text responses when possible
    4. Adding consistent metadata about response time and model
    
    Args:
        image_path (str): Path to the image file to analyze
        model_path (str): Path to the FastVLM model directory
        prompt (str, optional): Custom prompt for analysis. If None, uses JSON_PROMPT_TEMPLATE.
        max_retries (int, optional): Maximum number of retry attempts for invalid JSON. Default is 3.
        
    Returns:
        dict: JSON result with 'description', 'tags', and 'metadata' fields,
              or None if analysis fails after all retries.
              
    Example:
        >>> result = run_fastvlm_json_analysis("image.jpg", "models/fastvlm_1.5b")
        >>> print(result["description"])
        >>> print(result["metadata"]["response_time"])
    """
    if not os.path.exists(image_path):
        logging.error(f"Image not found at {image_path}")
        return None
        
    if not os.path.exists(model_path):
        logging.error(f"Model not found at {model_path}")
        return None
        
    # Use the JSON prompt template if not provided
    if not prompt:
        prompt = JSON_PROMPT_TEMPLATE
        
    # Get the predict.py script path
    ml_fastvlm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml-fastvlm")
    predict_script = os.path.join(ml_fastvlm_dir, "predict.py")
    
    if not os.path.exists(predict_script):
        logging.error(f"predict.py script not found at {predict_script}")
        return None
        
    import subprocess
    
    # Core command excluding prompt (to avoid PII in logs)
    base_cmd = [
        sys.executable,
        predict_script,
        "--model-path", model_path,
        "--image-file", image_path
    ]
    
    # Add prompt separately to avoid logging it directly
    cmd = base_cmd + ["--prompt", prompt]
    
    # Try with retries
    for attempt in range(max_retries):
        try:
            logging.info(f"Attempt {attempt+1}/{max_retries} - Running FastVLM")
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            response_time = time.time() - start_time
            
            # Process the output
            output = result.stdout.strip()
            
            # Try to parse as JSON
            try:
                # Check if the output is already valid JSON
                json_data = json.loads(output)
                
                # Validate the expected structure
                if 'description' not in json_data or 'tags' not in json_data:
                    if attempt < max_retries - 1:
                        logging.warning("JSON missing required fields. Retrying...")
                        # Strengthen the prompt to emphasize JSON format
                        prompt = prompt + "\nYour response MUST be a JSON object with 'description' and 'tags' fields."
                        cmd = base_cmd + ["--prompt", prompt]
                        continue
                    else:
                        # Create proper structure if missing in final attempt
                        if 'description' not in json_data:
                            json_data['description'] = "No description provided"
                        if 'tags' not in json_data:
                            json_data['tags'] = []
                
                # Add metadata
                json_data["metadata"] = {
                    "response_time": response_time,
                    "model": "FastVLM 1.5B",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "attempts": attempt + 1
                }
                
                logging.info(f"Successfully parsed JSON output on attempt {attempt+1}")
                return json_data
                
            except json.JSONDecodeError:
                # Try to extract JSON from the text
                extracted_json = extract_json_from_text(output)
                if extracted_json and attempt < max_retries - 1:
                    logging.info("Successfully extracted JSON from text response")
                    # Add metadata
                    extracted_json["metadata"] = {
                        "response_time": response_time,
                        "model": "FastVLM 1.5B",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "attempts": attempt + 1,
                        "extracted": True
                    }
                    return extracted_json
                    
                if attempt < max_retries - 1:
                    logging.warning("Invalid JSON format. Retrying with stronger prompt...")
                    # Make the JSON requirement even more explicit
                    prompt = """Your ENTIRE response must be VALID JSON. Do NOT include any text before or after the JSON.
                    Describe this image as a JSON object with exactly these fields:
                    {"description": "detailed description here", "tags": ["tag1", "tag2", "etc"]}
                    No other text, just the JSON object."""
                    cmd = base_cmd + ["--prompt", prompt]
                    continue
                else:
                    # Final attempt failed, return structured error
                    logging.warning("All JSON parsing attempts failed. Returning as text.")
                    return {
                        "text": output,
                        "metadata": {
                            "response_time": response_time,
                            "model": "FastVLM 1.5B",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "json_parsing_failed": True,
                            "attempts": max_retries
                        }
                    }
                    
        except subprocess.SubprocessError as e:
            logging.error(f"Error running FastVLM: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                logging.error(f"Error output: {e.stderr}")
            if attempt < max_retries - 1:
                logging.info(f"Retrying... ({attempt+1}/{max_retries})")
                time.sleep(1)  # Short delay before retry
                continue
            else:
                return None
    
    # Should not reach here but just in case
    return None

def main():
    """Main function for the script."""
    parser = argparse.ArgumentParser(description="FastVLM JSON Output Demo")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--model", default="ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3", 
                       help="Path to FastVLM model")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--retries", type=int, default=3, 
                       help="Maximum number of retries for JSON validation")
    parser.add_argument("--prompt", help="Custom prompt (use with caution to ensure JSON output)")
    parser.add_argument("--quiet", action="store_true", help="Reduce verbosity of output")
    
    args = parser.parse_args()
    
    # Set logging level based on quiet flag
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Print banner (only if not quiet)
    if not args.quiet:
        print("="*60)
        print("FastVLM JSON Output Demo")
        print("="*60)
        print(f"Image: {args.image}")
        print(f"Model: {args.model}")
        print(f"Max retries: {args.retries}")
    
    # Run the analysis
    if not args.quiet:
        print("\nRunning analysis...")
    
    result = run_fastvlm_json_analysis(
        args.image, 
        args.model,
        prompt=args.prompt,  # This will be None if not provided
        max_retries=args.retries
    )
    
    if result:
        # Save to file if output path provided
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            if not args.quiet:
                print(f"\nResults saved to {args.output}")
        
        # Print results
        if not args.quiet:
            print("\nAnalysis Results:")
            # Check if the result contains proper JSON structure or just text
            if "text" in result and "json_parsing_failed" in result.get("metadata", {}):
                print("WARNING: JSON parsing failed. Raw output:")
                print(result["text"])
            else:
                print(json.dumps(result, indent=2))
            
            # Print metadata separately
            if "metadata" in result:
                print(f"\nResponse time: {result['metadata']['response_time']:.2f} seconds")
                if "attempts" in result["metadata"] and result["metadata"]["attempts"] > 1:
                    print(f"JSON validation attempts: {result['metadata']['attempts']}")
        else:
            # In quiet mode, just print the JSON
            print(json.dumps(result))
    else:
        print("\nAnalysis failed.")
    
    if not args.quiet:
        print("\nDemo complete!")

if __name__ == "__main__":
    main()