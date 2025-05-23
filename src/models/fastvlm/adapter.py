#!/usr/bin/env python3
"""
FastVLM Adapter

This module provides a simplified interface for using FastVLM models with the
file analyzer system. It handles model discovery, initialization, and prediction.

The adapter supports both:
1. Using FastVLM installed via pip (mlx-fastvlm package)
2. Using the FastVLM model files directly via the predict.py script

It automatically finds models in the centralized model directory structure.
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime


def run_model_command(cmd: list[str], cwd: str = None, timeout: int = 120):
    """
    Execute model command with robust subprocess validation.
    
    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for execution
        timeout: Timeout in seconds
        
    Returns:
        stdout from the subprocess
        
    Raises:
        RuntimeError: If subprocess fails or exits with non-zero code
    """
    logger = logging.getLogger("src.models.fastvlm.adapter")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False  # don't raise yet, we handle manually
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Model execution timed out after {timeout}s: {e}")
    except Exception as e:
        raise RuntimeError(f"Subprocess execution failed: {e}")

    if result.returncode != 0:
        logger.error(f"Model subprocess failed with exit code {result.returncode}")
        logger.error(f"STDERR:\n{result.stderr.strip()}")
        raise RuntimeError(f"Model execution failed: {result.stderr.strip()}")

    logger.debug(f"Model STDOUT:\n{result.stdout.strip()}")
    return result.stdout

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import model configuration
from src.models.config import (
    get_model_path,
    get_model_info,
    download_model,
    get_predict_script_path,
    create_artifact_path_for_model_output,
    DEFAULT_MODEL_TYPE,
    DEFAULT_MODEL_SIZE
)

# Import JSON utility if available
try:
    from src.utils.json_utils import JSONValidator, process_model_output, get_json_prompt
    JSON_UTILS_AVAILABLE = True
except ImportError:
    JSON_UTILS_AVAILABLE = False
    logger.warning("JSON utilities not available.")

# Import artifact discipline tools if available
try:
    from src.core.artifact_guard import get_canonical_artifact_path, PathGuard, validate_artifact_path
    ARTIFACT_DISCIPLINE = True
except ImportError:
    ARTIFACT_DISCIPLINE = False
    logger.warning("Artifact discipline tools not available. Using fallback paths.")

class FastVLMAdapter:
    """
    Adapter for FastVLM models that handles model discovery and prediction.
    """
    
    def __init__(self, model_type: str = DEFAULT_MODEL_TYPE, 
                model_size: str = DEFAULT_MODEL_SIZE,
                auto_download: bool = True):
        """
        Initialize the FastVLM adapter.
        
        Args:
            model_type: Type of model (default: fastvlm)
            model_size: Size of model (default: 0.5b)
            auto_download: Whether to automatically download the model if not found
        """
        self.model_type = model_type
        self.model_size = model_size
        self.model_path = None
        self.predict_script = None
        self.model_info = None
        self.initialized = False
        
        # Get model info
        self._initialize_model(auto_download)
        
    def _initialize_model(self, auto_download: bool = True) -> bool:
        """
        Initialize the model by finding the model path and predict script.
        
        Args:
            auto_download: Whether to automatically download the model if not found
            
        Returns:
            True if initialization was successful, False otherwise
        """
        # Get model info
        self.model_info = get_model_info(self.model_type, self.model_size)
        
        if "error" in self.model_info:
            logger.error(f"Error getting model info: {self.model_info['error']}")
            return False
            
        # Get model path
        self.model_path = get_model_path(self.model_type, self.model_size)
        
        if not self.model_path:
            logger.warning(f"Model {self.model_type} {self.model_size} not found")
            
            if auto_download:
                logger.info(f"Attempting to download {self.model_type} {self.model_size}...")
                success, message = download_model(self.model_type, self.model_size)
                
                if success:
                    logger.info(f"Successfully downloaded model: {message}")
                    self.model_path = get_model_path(self.model_type, self.model_size)
                else:
                    logger.error(f"Failed to download model: {message}")
                    return False
            else:
                logger.error("Model not found and auto_download is disabled")
                return False
        
        # Get predict script path
        self.predict_script = get_predict_script_path(self.model_type)
        
        if not self.predict_script:
            logger.error(f"Predict script for {self.model_type} not found")
            return False
            
        logger.debug(f"Initialized {self.model_type} {self.model_size} at {self.model_path}")
        logger.debug(f"Using predict script: {'mlx-fastvlm package' if self.predict_script == 'package' else self.predict_script}")
        
        self.initialized = True
        return True
        
    def predict(self, image_path: str, prompt: str = None, 
                output_path: str = None, mode: str = "describe",
                timeout_seconds: int = 60, mock: bool = False) -> Dict[str, Any]:
        """
        Run prediction with the FastVLM model.
        
        Args:
            image_path: Path to the image to analyze
            prompt: Custom prompt (if None, uses default JSON prompt)
            output_path: Path to save the output JSON (if None, uses a canonical artifact path)
            mode: Analysis mode (describe, detect, document)
            timeout_seconds: Timeout for the FastVLM process
            mock: Whether to run in mock mode (for testing)
            
        Returns:
            Dictionary containing the prediction result
            
        Raises:
            RuntimeError: For all failure cases with explicit diagnostic messages
        """
        if not self.initialized:
            if not self._initialize_model():
                raise RuntimeError(f"Model initialization failed for {self.model_type} {self.model_size}")
                
        # Use mock mode for testing when requested
        if mock:
            logger.info("Running in mock mode - will not actually invoke the model")
            
            mock_result = {
                "description": f"This is a mock response for image {os.path.basename(image_path)}",
                "tags": ["mock", "test", "image"],
                "metadata": {
                    "model": f"{self.model_type}_{self.model_size}",
                    "execution_time": 0.1,
                    "timestamp": datetime.now().isoformat(),
                    "mock": True
                }
            }
            
            # Save result to output path if provided
            if output_path:
                try:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Use PathGuard if available
                    if ARTIFACT_DISCIPLINE:
                        with PathGuard(os.path.dirname(output_path)):
                            with open(output_path, "w") as f:
                                json.dump(mock_result, f, indent=2)
                    else:
                        with open(output_path, "w") as f:
                            json.dump(mock_result, f, indent=2)
                except Exception as e:
                    raise RuntimeError(f"Failed to write mock output to {output_path}: {e}")
                        
            return mock_result
                
        # Convert to absolute path and validate image path
        image_path = os.path.abspath(os.path.expanduser(image_path))
        if not os.path.exists(image_path):
            raise RuntimeError(f"Image file not found: {image_path}")
            
        # Use JSON prompt if available and no custom prompt provided
        if prompt is None and JSON_UTILS_AVAILABLE:
            prompt = get_json_prompt(mode, retry_attempt=0)
        elif prompt is None:
            # Fallback prompts if JSON utilities not available
            if mode == "describe":
                prompt = "Describe this image in detail. Format your response as JSON with 'description' and 'tags' fields."
            elif mode == "detect":
                prompt = "Identify objects in this image. Format your response as JSON with 'objects' and 'description' fields."
            elif mode == "document":
                prompt = "Extract text from this document. Format your response as JSON with 'text' and 'document_type' fields."
                
        # Create output path if not provided
        if output_path is None:
            # Extract image basename for context
            image_basename = os.path.basename(image_path)
            image_name = os.path.splitext(image_basename)[0]
            
            # Create canonical artifact path
            if ARTIFACT_DISCIPLINE:
                artifact_dir = create_artifact_path_for_model_output(self.model_type, f"{mode}_{self.model_size}")
                output_path = os.path.join(artifact_dir, f"{image_name}_result.json")
            else:
                # Fallback path
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                artifact_dir = os.path.join(project_root, "artifacts", "vision", 
                                          f"{self.model_type}_{mode}_{self.model_size}_{timestamp}")
                os.makedirs(artifact_dir, exist_ok=True)
                output_path = os.path.join(artifact_dir, f"{image_name}_result.json")
                
        # Run prediction with explicit error handling
        start_time = datetime.now()
        
        try:
            # Check if we're using the package or the script
            if self.predict_script == "package":
                result = self._predict_with_package(image_path, prompt, mode, timeout_seconds)
            else:
                result = self._predict_with_script(image_path, prompt, timeout_seconds, output_path)
                
        except Exception as e:
            # Log the full error details
            logger.error(f"Model prediction failed for {image_path}: {e}")
            logger.error(f"Model: {self.model_type}_{self.model_size}, Mode: {mode}")
            # Re-raise with explicit error message
            raise RuntimeError(f"Model prediction failed: {e}")
            
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Process the result
        if isinstance(result, dict):
            # Add metadata
            if "metadata" not in result:
                result["metadata"] = {}
                
            result["metadata"]["model"] = f"{self.model_type}_{self.model_size}"
            result["metadata"]["execution_time"] = execution_time
            result["metadata"]["timestamp"] = datetime.now().isoformat()
            
            # Save result to output path if provided (only if not already saved by _predict_with_script)
            if output_path and self.predict_script == "package":
                try:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Use PathGuard if available
                    if ARTIFACT_DISCIPLINE:
                        with PathGuard(os.path.dirname(output_path)):
                            with open(output_path, "w") as f:
                                json.dump(result, f, indent=2)
                    else:
                        with open(output_path, "w") as f:
                            json.dump(result, f, indent=2)
                    logger.debug(f"Successfully wrote model output to: {output_path}")
                except Exception as e:
                    raise RuntimeError(f"Failed to write model output to {output_path}: {e}")
                        
            return result
            
        elif JSON_UTILS_AVAILABLE:
            # Try to extract JSON from text result
            metadata = {
                "model": f"{self.model_type}_{self.model_size}",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
            }
            
            try:
                json_result = process_model_output(result, metadata, mode)
            except Exception as e:
                raise RuntimeError(f"Failed to process model output: {e}")
            
            # Save result to output path if provided
            if output_path:
                try:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Use PathGuard if available
                    if ARTIFACT_DISCIPLINE:
                        with PathGuard(os.path.dirname(output_path)):
                            with open(output_path, "w") as f:
                                json.dump(json_result, f, indent=2)
                    else:
                        with open(output_path, "w") as f:
                            json.dump(json_result, f, indent=2)
                    logger.debug(f"Successfully wrote processed output to: {output_path}")
                except Exception as e:
                    raise RuntimeError(f"Failed to write processed output to {output_path}: {e}")
                        
            return json_result
            
        else:
            # Return raw text result with metadata
            result_dict = {
                "raw_output": result,
                "metadata": {
                    "model": f"{self.model_type}_{self.model_size}",
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat(),
                }
            }
            
            # Save result to output path if provided
            if output_path:
                try:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Use PathGuard if available
                    if ARTIFACT_DISCIPLINE:
                        with PathGuard(os.path.dirname(output_path)):
                            with open(output_path, "w") as f:
                                json.dump(result_dict, f, indent=2)
                    else:
                        with open(output_path, "w") as f:
                            json.dump(result_dict, f, indent=2)
                    logger.debug(f"Successfully wrote raw output to: {output_path}")
                except Exception as e:
                    raise RuntimeError(f"Failed to write raw output to {output_path}: {e}")
                        
            return result_dict
            
    def _predict_with_package(self, image_path: str, prompt: str, 
                             mode: str, timeout_seconds: int) -> Union[Dict[str, Any], str]:
        """
        Run prediction using the mlx-fastvlm package.
        
        Args:
            image_path: Path to the image to analyze
            prompt: Prompt for the model
            mode: Analysis mode
            timeout_seconds: Timeout in seconds
            
        Returns:
            Prediction result (dict or string)
        """
        try:
            # Import the package
            from mlx_fastvlm import FastVLM
            
            # Check for double-nested structure and handle it
            model_path = self.model_path
            nested_path = os.path.join(self.model_path, os.path.basename(self.model_path))
            
            # Check if we have a double-nested directory structure (common with downloads)
            if os.path.isdir(nested_path):
                # Check for required model files in the nested path, including sharded model files
                required_files = ["tokenizer_config.json", "config.json"]
                model_files = ["model.safetensors", "model.safetensors.index.json", "model-00001-of-00004.safetensors"]
                
                # First check for config files
                has_config = False
                for req_file in required_files:
                    if os.path.exists(os.path.join(nested_path, req_file)):
                        has_config = True
                        break
                        
                # Then check for model files (regular or sharded format)
                has_model = False
                for model_file in model_files:
                    if os.path.exists(os.path.join(nested_path, model_file)):
                        has_model = True
                        break
                        
                if has_config and has_model:
                    # Found required files in the nested structure
                    logger.info(f"Detected double-nested model structure. Using {nested_path} instead of {model_path}")
                    model_path = nested_path
            
            # Initialize the model with the potentially updated path
            model = FastVLM(model_path)
            
            # Run prediction
            result = model.predict(image_path, prompt)
            
            # Try to parse as JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        except ImportError:
            raise ImportError("mlx-fastvlm package not installed")
            
    def _predict_with_script(self, image_path: str, prompt: str, 
                           timeout_seconds: int, output_path: str = None) -> Union[Dict[str, Any], str]:
        """
        Run prediction using the predict.py script.
        
        Args:
            image_path: Path to the image to analyze
            prompt: Prompt for the model
            timeout_seconds: Timeout in seconds
            output_path: Path to save output JSON (optional)
            
        Returns:
            Prediction result (dict or string)
            
        Raises:
            RuntimeError: For all failure cases with explicit diagnostic messages
        """
        import platform
        
        # Check for double-nested structure and handle it
        model_path = self.model_path
        nested_path = os.path.join(self.model_path, os.path.basename(self.model_path))
        
        # Check if we have a double-nested directory structure (common with downloads)
        # where model files are actually inside model_path/model_name/ rather than directly in model_path
        if os.path.isdir(nested_path):
            # Check for required model files in the nested path, including sharded model files
            required_files = ["tokenizer_config.json", "config.json"]
            model_files = ["model.safetensors", "model.safetensors.index.json", "model-00001-of-00004.safetensors"]
            
            # First check for config files
            has_config = False
            for req_file in required_files:
                if os.path.exists(os.path.join(nested_path, req_file)):
                    has_config = True
                    break
                    
            # Then check for model files (regular or sharded format)
            has_model = False
            for model_file in model_files:
                if os.path.exists(os.path.join(nested_path, model_file)):
                    has_model = True
                    break
                    
            if has_config and has_model:
                # Found required files in the nested structure
                logger.info(f"Detected double-nested model structure. Using {nested_path} instead of {model_path}")
                model_path = nested_path
        
        # Build command with the possibly updated model_path
        cmd = [
            sys.executable, self.predict_script,
            "--model-path", model_path,
            "--image-file", image_path,
            "--prompt", prompt,
            "--max_new_tokens", "256"  # Reduced to prevent repetition issues
        ]
        
        working_dir = os.path.dirname(self.predict_script)
        logger.debug(f"Running command: {' '.join(cmd)}")
        logger.debug(f"Working directory: {working_dir}")

        # Run subprocess with validation - this will raise RuntimeError with diagnostics
        try:
            output = run_model_command(cmd, cwd=working_dir, timeout=timeout_seconds)
        except RuntimeError as e:
            # Re-raise with additional context
            raise RuntimeError(f"Model subprocess failed: {e}")
            
        output = output.strip()
        if not output:
            raise RuntimeError(f"Model returned empty output. Command: {' '.join(cmd)}")

        # Validate JSON parsing with repair capability
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as e:
            # Try to repair the JSON using json-repair
            try:
                from json_repair import repair_json
                logger.debug(f"JSON parsing failed, attempting to repair: {str(e)[:100]}")
                repaired_json = repair_json(output)
                parsed = json.loads(repaired_json)
                logger.debug("Successfully repaired malformed JSON")
            except Exception as repair_error:
                raise RuntimeError(f"Failed to parse model output as JSON: {e}. JSON repair also failed: {repair_error}. Raw output: {output[:200]}...")

        # Validate required fields
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Model output is not a valid JSON object. Got: {type(parsed)}")
        
        if "description" not in parsed or "tags" not in parsed:
            available_keys = list(parsed.keys()) if isinstance(parsed, dict) else "N/A"
            raise RuntimeError(f"Model output missing required fields (description, tags). Available keys: {available_keys}")

        # Write structured output to file only after successful validation
        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump(parsed, f, indent=2)
                logger.debug(f"Successfully wrote model output to: {output_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to write model output to disk at {output_path}: {e}")

        return parsed
            
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model.
        
        Returns:
            Dictionary with model information
        """
        if not self.initialized:
            if not self._initialize_model():
                return {"error": "Model initialization failed"}
                
        return self.model_info

# Convenience function to create and initialize adapter
def create_adapter(model_type: str = DEFAULT_MODEL_TYPE, 
                  model_size: str = DEFAULT_MODEL_SIZE,
                  auto_download: bool = True) -> FastVLMAdapter:
    """
    Create and initialize a FastVLM adapter.
    
    Args:
        model_type: Type of model (default: fastvlm)
        model_size: Size of model (default: 0.5b)
        auto_download: Whether to automatically download the model if not found
        
    Returns:
        Initialized FastVLM adapter
    """
    return FastVLMAdapter(model_type, model_size, auto_download)

# Backward compatibility with previous API
def init_fastvlm(model_size=DEFAULT_MODEL_SIZE, download_if_missing=True):
    """
    Initialize a FastVLM model (backward compatibility).
    
    Args:
        model_size: Size of the model to use ("0.5b", "1.5b", or "7b")
        download_if_missing: Whether to download the model if it's missing
        
    Returns:
        FastVLM adapter instance that mimics the old API
    """
    adapter = create_adapter("fastvlm", model_size, download_if_missing)
    
    # Create a wrapper that mimics the old API
    class BackwardCompatWrapper:
        def __init__(self, adapter):
            self.adapter = adapter
            
        def run(self, image_path, prompt, temperature=0.1):
            result = self.adapter.predict(image_path, prompt)
            if "error" in result:
                raise RuntimeError(result["error"])
            if "raw_output" in result:
                return result["raw_output"]
            if isinstance(result, dict) and "response" in result:
                return result["response"]
            return str(result)
    
    return BackwardCompatWrapper(adapter)

# Backward compatibility with previous API
def run_fastvlm_analysis(image_path, prompt="Describe this image in detail.", 
                        model_size=DEFAULT_MODEL_SIZE, temperature=0.1):
    """
    Run FastVLM analysis on an image (backward compatibility).
    
    Args:
        image_path: Path to the image to analyze
        prompt: Prompt to use for the analysis
        model_size: Size of the model to use ("0.5b", "1.5b", "7b")
        temperature: Temperature parameter for generation
        
    Returns:
        Dictionary with analysis results
    """
    adapter = create_adapter("fastvlm", model_size, True)
    result = adapter.predict(image_path, prompt)
    
    # Convert to old response format
    if "error" in result:
        return {"error": result["error"]}
    
    if "raw_output" in result:
        response = result["raw_output"]
    elif isinstance(result, dict) and "response" in result:
        response = result["response"]
    else:
        response = str(result)
    
    return {
        "response": response,
        "model": f"FastVLM-{model_size}",
        "version": adapter.model_info.get("version", "v1.0.2"),
        "response_time": result.get("metadata", {}).get("execution_time", 0),
    }

if __name__ == "__main__":
    # Command-line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="FastVLM Adapter")
    parser.add_argument("--model", default=DEFAULT_MODEL_TYPE, help=f"Model type (default: {DEFAULT_MODEL_TYPE})")
    parser.add_argument("--size", default=DEFAULT_MODEL_SIZE, help=f"Model size (default: {DEFAULT_MODEL_SIZE})")
    parser.add_argument("--image", required=True, help="Path to the image to analyze")
    parser.add_argument("--prompt", help="Custom prompt (if omitted, uses default JSON prompt)")
    parser.add_argument("--output", help="Path to save the output JSON (if omitted, uses canonical artifact path)")
    parser.add_argument("--mode", default="describe", choices=["describe", "detect", "document"], 
                        help="Analysis mode (default: describe)")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default: 60)")
    
    args = parser.parse_args()
    
    # Initialize adapter
    adapter = create_adapter(args.model, args.size)
    
    # Run prediction
    result = adapter.predict(args.image, args.prompt, args.output, args.mode, args.timeout)
    
    # Print result
    print(json.dumps(result, indent=2))