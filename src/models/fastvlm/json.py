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
import argparse
import logging
from pathlib import Path

# Define exception classes for JSON handling
class JSONParsingError(Exception):
    """Exception raised when all JSON parsing attempts fail."""
    def __init__(self, text, metadata):
        self.text = text
        self.metadata = metadata
        super().__init__("Failed to parse valid JSON from model output")

# Make sure our modules are in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Import centralized JSON utilities
from src.utils.json_utils import JSONValidator, process_model_output, get_json_prompt

# Import artifact path management
from src.core.artifact_guard import get_canonical_artifact_path, PathGuard, validate_artifact_path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# For backward compatibility - this function now uses the centralized implementation
def extract_json_from_text(text):
    """Attempt to extract JSON from text response if it's embedded in other content."""
    return JSONValidator.extract_json_from_text(text)

def run_fastvlm_json_analysis(image_path, model_path, output_path=None, prompt=None, max_retries=3, mode="describe", timeout_seconds=60):
    """
    Run FastVLM analysis with JSON output and retry logic.
    
    This function provides robust JSON output from FastVLM vision analysis by:
    1. Using JSON-specific prompting to encourage structured output
    2. Implementing retry logic if the initial response isn't valid JSON
    3. Extracting JSON from text responses when possible
    4. Adding consistent metadata about response time and model
    5. Enforcing subprocess timeout to prevent hanging
    
    Args:
        image_path (str): Path to the image file to analyze
        model_path (str): Path to the FastVLM model directory
        output_path (str, optional): Path where JSON results will be written on error
        prompt (str, optional): Custom prompt for analysis. If None, uses JSON_PROMPT_TEMPLATE.
        max_retries (int, optional): Maximum number of retry attempts for invalid JSON. Default is 3.
        mode (str, optional): Analysis mode - describe, detect, or document. Default is "describe".
        timeout_seconds (int, optional): Maximum time to wait for the FastVLM process. Default is 60s.
        
    Returns:
        dict: JSON result with 'description', 'tags', and 'metadata' fields,
              or None if analysis fails after all retries.
              
    Example:
        >>> result = run_fastvlm_json_analysis("image.jpg", "models/fastvlm_1.5b")
        >>> print(result["description"])
        >>> print(result["metadata"]["response_time"])
    """
    # Validate input paths
    if not os.path.exists(image_path):
        logging.error(f"Image not found at {image_path}")
        return None
        
    if not os.path.exists(model_path):
        logging.error(f"Model not found at {model_path}")
        return None
        
    # Use the JSON prompt template if not provided
    if not prompt:
        prompt = get_json_prompt(mode, retry_attempt=0)
    
    # Centralized predict.py resolution logic
    # First determine project root (the parent of src/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Standard location in project structure
    ml_fastvlm_dir = os.path.join(project_root, "libs", "ml-fastvlm")
    predict_script = os.path.join(ml_fastvlm_dir, "predict.py")
    logging.info(f"Looking for predict.py at {predict_script}")
    
    # Validate the predict script exists
    if not os.path.exists(predict_script):
        # Try one alternate location before failing
        alternate_path = os.path.join(os.path.dirname(model_path), "..", "predict.py")
        if os.path.exists(alternate_path):
            predict_script = alternate_path
            logging.info(f"Found predict.py at alternate location: {predict_script}")
        else:
            # Hard fail - we can't proceed without the predict script
            logging.error(f"predict.py script not found at {predict_script} or {alternate_path}")
            raise FileNotFoundError(f"predict.py script not found in expected locations: {predict_script} or {alternate_path}")
        
    import subprocess
    
    import platform
    cmd = [
        sys.executable, predict_script,
        "--model-path", model_path,
        "--image-file", image_path,
        "--prompt", prompt
    ]
    
    # Try with retries
    for attempt in range(max_retries):
        try:
            logging.info(f"Attempt {attempt+1}/{max_retries} - Running FastVLM")
            
            start_time = time.time()
            
            try:
                if platform.system() != "Windows":
                    full_cmd = ["timeout", str(timeout_seconds)] + cmd
                    result = subprocess.run(full_cmd, capture_output=True, text=True)
                    if result.returncode == 124:
                        raise subprocess.TimeoutExpired(cmd, timeout_seconds)
                else:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
            except Exception as e:
                error_result = {
                    "error": "FastVLM failed",
                    "exception": str(e),
                    "metadata": {"timeout_seconds": timeout_seconds}
                }
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with PathGuard(os.path.dirname(output_path)):
                    with open(output_path, "w") as f:
                        json.dump(error_result, f, indent=2)
                raise Exception(f"FastVLM failed: {e}")
                
            response_time = time.time() - start_time
            
            # Process the output
            output = result.stdout.strip()
            
            # Try to parse and validate using the centralized utilities
            # Prepare base metadata with key metrics
            metadata = {
                "response_time": response_time,
                "model": "FastVLM 1.5B",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "attempts": attempt + 1
            }
            
            # First, try direct JSON parsing
            try:
                json_data = json.loads(output)
                
                # Validate the expected structure using centralized validator
                expected_fields = []
                if mode == "detect":
                    expected_fields = ["objects", "description"]
                elif mode == "document":
                    expected_fields = ["text", "document_type"]
                else:  # Default to description mode
                    expected_fields = ["description", "tags"]
                    
                if JSONValidator.validate_json_structure(json_data, expected_fields, mode):
                    # Structure is valid, add metadata and return
                    return JSONValidator.add_metadata(json_data, metadata)
                    
                # Missing required fields - try again with stronger prompt if not final attempt
                if attempt < max_retries - 1:
                    logging.warning("JSON missing required fields. Retrying...")
                    prompt = get_json_prompt(mode, retry_attempt=attempt+1)
                    cmd = [
                        sys.executable, predict_script,
                        "--model-path", model_path,
                        "--image-file", image_path,
                        "--prompt", prompt
                    ]
                    continue
                else:
                    # Create proper structure if missing in final attempt
                    if mode == "describe":
                        if 'description' not in json_data:
                            json_data['description'] = "No description provided"
                        if 'tags' not in json_data:
                            json_data['tags'] = []
                    elif mode == "detect":
                        if 'objects' not in json_data:
                            json_data['objects'] = []
                        if 'description' not in json_data:
                            json_data['description'] = "No description provided"
                    elif mode == "document":
                        if 'text' not in json_data:
                            json_data['text'] = "No text extracted"
                        if 'document_type' not in json_data:
                            json_data['document_type'] = "unknown"
                            
                    # Add metadata to result
                    return JSONValidator.add_metadata(json_data, metadata)
                    
            except json.JSONDecodeError:
                # Try to extract JSON from text using advanced extraction
                json_data = JSONValidator.extract_json_from_text(output)
                
                if json_data:
                    logging.info("Successfully extracted JSON from text response")
                    # Add extraction flag to metadata
                    metadata["extracted"] = True
                    
                    # Add metadata and return
                    return JSONValidator.add_metadata(json_data, metadata)
                
                # JSON extraction failed - retry with stronger prompt if not final attempt
                if attempt < max_retries - 1:
                    logging.warning("Invalid JSON format. Retrying with stronger prompt...")
                    prompt = get_json_prompt(mode, retry_attempt=attempt+1)
                    cmd = [
                        sys.executable, predict_script,
                        "--model-path", model_path,
                        "--image-file", image_path,
                        "--prompt", prompt
                    ]
                    continue
                else:
                    # Final attempt failed - write error output and exit
                    logging.warning("All JSON parsing attempts failed.")
                    
                    # Create error result with structured data
                    error_result = {
                        "error": "Failed to parse JSON output",
                        "description": "FastVLM output could not be parsed as valid JSON",
                        "tags": ["error", "json_parsing_failed"],
                        "metadata": {
                            "response_time": response_time,
                            "model": "FastVLM 1.5B",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "json_parsing_failed": True,
                            "attempts": max_retries
                        }
                    }
                    
                    # Write to output path
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with PathGuard(os.path.dirname(output_path)):
                        with open(output_path, "w") as f:
                            json.dump(error_result, f, indent=2)
                    raise JSONParsingError(text=output, metadata=error_result["metadata"])
                
        except Exception as e:
            # This should not happen with our direct error handling above,
            # but just in case, handle any other exceptions
            logging.error(f"Error running FastVLM: {e}")
            
            # Create error result
            error_result = {
                "error": "FastVLM process error",
                "description": str(e),
                "tags": ["error"],
                "metadata": {
                    "timeout_seconds": timeout_seconds,
                    "attempts": attempt + 1,
                    "model": "FastVLM",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            
            # Write to output path
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with PathGuard(os.path.dirname(output_path)):
                with open(output_path, "w") as f:
                    json.dump(error_result, f, indent=2)
            raise Exception(f"FastVLM process error: {e}")
    
    # Should not reach here but just in case
    return None

def main():
    """Main function for the script."""
    parser = argparse.ArgumentParser(description="FastVLM JSON Output Demo")
    parser.add_argument("--image", required=True, help="Path to test image")
    parser.add_argument("--model", default="libs/ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3", 
                       help="Path to FastVLM model")
    parser.add_argument("--output", help="Output JSON file path (MUST be canonical or will be REJECTED)")
    parser.add_argument("--retries", type=int, default=3, 
                       help="Maximum number of retries for JSON validation")
    parser.add_argument("--prompt", help="Custom prompt (use with caution to ensure JSON output)")
    parser.add_argument("--mode", choices=["describe", "detect", "document"], default="describe",
                       help="Analysis mode (describe, detect, document)")
    parser.add_argument("--quiet", action="store_true", help="Reduce verbosity of output")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds for the FastVLM subprocess")
    
    args = parser.parse_args()
    
    # Set logging level based on quiet flag
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # ---- PATH VALIDATION (HARD ENFORCEMENT) ----
    if args.output and not validate_artifact_path(args.output):
        print(f"ERROR: Non-canonical artifact path: {args.output}", file=sys.stderr)
        # In the main script we can exit directly
        sys.exit(1)
    image_basename = os.path.basename(args.image)
    image_name = os.path.splitext(image_basename)[0]
    artifact_dir = get_canonical_artifact_path("vision", f"fastvlm_{args.mode}")
    output_path = args.output if args.output else os.path.join(artifact_dir, f"{image_name}_result.json")
    
    # Print banner (only if not quiet)
    if not args.quiet:
        print("="*60)
        print("FastVLM JSON Output Demo")
        print("="*60)
        print(f"Image: {args.image}")
        print(f"Model: {args.model}")
        print(f"Mode: {args.mode}")
        print(f"Max retries: {args.retries}")
        print(f"Subprocess timeout: {args.timeout} seconds")
        print(f"Output: {output_path}")
        print("\nRunning analysis...")
    
    # Run analysis with proper error handling
    result = run_fastvlm_json_analysis(
        args.image, 
        args.model,
        output_path=output_path,  # Pass output path for error handling
        prompt=args.prompt,
        max_retries=args.retries,
        mode=args.mode,
        timeout_seconds=args.timeout
    )
    
    if result:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to file with PathGuard to ensure artifact discipline
        with PathGuard(os.path.dirname(output_path)):
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            if not args.quiet:
                print(f"\nResults saved to {output_path}")
        
        # Print results
        if not args.quiet:
            print("\nAnalysis Results:")
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
        # This should never happen now with our direct error handling
        print("\nAnalysis failed, but no error was caught.")
        # In the main script we can exit directly
        sys.exit(1)
    
    if not args.quiet:
        print("\nDemo complete!")

if __name__ == "__main__":
    main()