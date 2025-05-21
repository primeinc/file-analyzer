#!/usr/bin/env python3
"""
fastvlm_adapter.py - Adapter for FastVLM model integration

This module provides a simple adapter for using FastVLM models with the File Analyzer
system. It handles finding models from the proper location and initializing them.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Import the model config 
from src.model_config import get_model_path, download_model

def init_fastvlm(model_size="0.5b", download_if_missing=True):
    """
    Initialize a FastVLM model.
    
    Args:
        model_size: Size of the model to use ("0.5b", "1.5b", or "7b")
        download_if_missing: Whether to download the model if it's missing
        
    Returns:
        FastVLM model instance
    """
    try:
        # Check if model exists, download if needed
        model_path = get_model_path("fastvlm", model_size)
        if not os.path.exists(model_path) and download_if_missing:
            print(f"FastVLM {model_size} model not found, downloading...")
            model_path = download_model("fastvlm", model_size)
        
        # Import FastVLM here to avoid dependencies during module import
        repo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "libs/ml-fastvlm")
        sys.path.insert(0, repo_path)
        
        try:
            # Try to load the predict module from the FastVLM repository
            import predict
            
            # Create a wrapper around the predict module's functionality
            class FastVLMWrapper:
                def __init__(self, model_dir):
                    self.model_dir = model_dir
                
                def run(self, image_path, prompt, temperature=0.1):
                    # We'll directly use the command-line arguments to run predict.py
                    import sys
                    import subprocess
                    
                    # Save the current sys.argv
                    old_argv = sys.argv
                    
                    try:
                        # Set up the arguments for predict.py
                        cmd = [
                            "python", os.path.join(repo_path, "predict.py"),
                            "--model-path", self.model_dir,
                            "--image-file", image_path,
                            "--prompt", prompt
                        ]
                        
                        # Run the command and capture the output
                        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                        return result.stdout.strip()
                    
                    finally:
                        # Restore the original sys.argv
                        sys.argv = old_argv
            
            # Use our wrapper instead of the direct FastVLM class
            FastVLM = FastVLMWrapper
            
        except ImportError:
            raise ImportError(
                "FastVLM is not installed correctly. Please run: "
                "./tools/setup_fastvlm.sh"
            )
        
        # Initialize the model
        print(f"Initializing FastVLM {model_size} from {model_path}...")
        model = FastVLM(model_path)
        return model
    
    except Exception as e:
        print(f"Error initializing FastVLM: {e}")
        return None

def run_fastvlm_analysis(image_path, prompt="Describe this image in detail.", 
                        model_size="0.5b", temperature=0.1):
    """
    Run FastVLM analysis on an image.
    
    Args:
        image_path: Path to the image to analyze
        prompt: Prompt to use for the analysis
        model_size: Size of the model to use ("0.5b", "1.5b", "7b")
        temperature: Temperature parameter for generation
        
    Returns:
        Dictionary with analysis results
    """
    try:
        # Initialize the model
        model = init_fastvlm(model_size=model_size)
        if model is None:
            return {"error": "Failed to initialize model"}
        
        # Process the image
        import time
        start_time = time.time()
        response = model.run(image_path, prompt, temperature=temperature)
        end_time = time.time()
        
        # Return the analysis results
        return {
            "response": response,
            "model": f"FastVLM-{model_size}",
            "version": "v1.0.2",
            "response_time": end_time - start_time,
        }
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Example usage when run directly
    import argparse
    
    parser = argparse.ArgumentParser(description="Run FastVLM analysis on an image")
    parser.add_argument("image_path", help="Path to the image to analyze")
    parser.add_argument("--prompt", default="Describe this image in detail.",
                        help="Prompt to use for the analysis")
    parser.add_argument("--model-size", choices=["0.5b", "1.5b", "7b"], default="0.5b",
                        help="Size of the model to use")
    parser.add_argument("--temperature", type=float, default=0.1,
                        help="Temperature parameter for generation")
    
    args = parser.parse_args()
    
    results = run_fastvlm_analysis(
        args.image_path, 
        prompt=args.prompt,
        model_size=args.model_size,
        temperature=args.temperature
    )
    
    print(json.dumps(results, indent=2))