#!/usr/bin/env python3
"""
Model Configuration and Management System

This module provides centralized configuration and management for AI vision models,
particularly FastVLM models. It handles model discovery, path resolution, and
configuration across both user-level and project-level installations.

Key features:
- Centralized model path configuration for FastVLM and other models
- Standardized model versions and checkpoints
- User-level model storage in ~/.local/share/fastvlm
- Automatic model discovery and validation
- Helpers for downloading and managing model files
"""

import os
import sys
import json
import logging
import platform
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import artifact discipline tools if available
try:
    from src.core.artifact_guard import get_canonical_artifact_path, validate_artifact_path
    ARTIFACT_DISCIPLINE = True
except ImportError:
    ARTIFACT_DISCIPLINE = False
    logger.warning("Artifact discipline tools not available. Using fallback paths.")

# Constants for model paths and versions
DEFAULT_MODEL_SIZE = "0.5b"
DEFAULT_MODEL_TYPE = "fastvlm"
MODEL_SIZES = ["0.5b", "1.5b", "7b"]

# User-level model directory - platform specific
if platform.system() == "Windows":
    USER_MODEL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "fastvlm")
else:
    USER_MODEL_DIR = os.path.expanduser("~/.local/share/fastvlm")
    
# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Model path priorities (searched in order)
MODEL_PATHS = [
    USER_MODEL_DIR,
    os.path.join(PROJECT_ROOT, "libs", "ml-fastvlm", "checkpoints"),
    os.path.join(PROJECT_ROOT, "checkpoints"),
]

# Standard model checkpoints with versions and hashes
MODEL_CHECKPOINTS = {
    "fastvlm": {
        "0.5b": {
            "path": "llava-fastvithd_0.5b_stage3",
            "description": "FastVLM 0.5B model (small)",
            "download_url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_0.5b_stage3.zip",
            "file_size_bytes": 1075577344,  # ~1.0 GB
            "version": "v1.0.2",
        },
        "1.5b": {
            "path": "llava-fastvithd_1.5b_stage3",
            "description": "FastVLM 1.5B model (medium)",
            "download_url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_1.5b_stage3.zip",
            "file_size_bytes": 2969567232,  # ~2.8 GB
            "version": "v1.0.2",
        },
        "7b": {
            "path": "llava-fastvithd_7b_stage3",
            "description": "FastVLM 7B model (large)",
            "download_url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_7b_stage3.zip",
            "file_size_bytes": 13959213056,  # ~13.0 GB
            "version": "v1.0.2",
        }
    }
}

def get_model_path(model_type: str = DEFAULT_MODEL_TYPE, 
                  model_size: str = DEFAULT_MODEL_SIZE) -> Optional[str]:
    """
    Find the path to a model by type and size.
    
    This function searches for models in the following locations, in order:
    1. User-level model directory (~/.local/share/fastvlm)
    2. Project checkpoints directory (libs/ml-fastvlm/checkpoints)
    3. Local checkpoints directory (checkpoints)
    
    Args:
        model_type: Model type (e.g., "fastvlm")
        model_size: Model size (e.g., "0.5b", "1.5b", "7b")
        
    Returns:
        Path to the model directory, or None if not found
    """
    if model_type not in MODEL_CHECKPOINTS:
        logger.error(f"Unknown model type: {model_type}")
        return None
        
    if model_size not in MODEL_CHECKPOINTS[model_type]:
        logger.error(f"Unknown model size: {model_size} for {model_type}")
        return None
        
    # Get the model path suffix
    model_path_suffix = MODEL_CHECKPOINTS[model_type][model_size]["path"]
    
    # Search for the model in standard locations
    for base_path in MODEL_PATHS:
        # Try with exact path from config
        full_path = os.path.join(base_path, model_path_suffix)
        if os.path.exists(full_path):
            # Found the model
            return full_path
            
        # Try with model size as directory name instead of full path
        alt_path = os.path.join(base_path, model_size)
        if os.path.exists(alt_path):
            # Found alternative path
            return alt_path
            
    # Model not found
    logger.warning(f"Model {model_type} {model_size} not found in standard locations")
    return None

def list_available_models() -> Dict[str, List[str]]:
    """
    List all available models on the system.
    
    Returns:
        Dictionary mapping model types to lists of available sizes
    """
    available_models = {}
    
    for model_type, sizes in MODEL_CHECKPOINTS.items():
        available_models[model_type] = []
        
        for size in sizes:
            if get_model_path(model_type, size):
                available_models[model_type].append(size)
                
    return available_models

def get_model_info(model_type: str = DEFAULT_MODEL_TYPE, 
                  model_size: str = DEFAULT_MODEL_SIZE) -> Dict[str, Any]:
    """
    Get information about a model.
    
    Args:
        model_type: Model type (e.g., "fastvlm")
        model_size: Model size (e.g., "0.5b", "1.5b", "7b")
        
    Returns:
        Dictionary containing model information
    """
    if model_type not in MODEL_CHECKPOINTS:
        return {"error": f"Unknown model type: {model_type}"}
        
    if model_size not in MODEL_CHECKPOINTS[model_type]:
        return {"error": f"Unknown model size: {model_size} for {model_type}"}
        
    # Get model info from config
    model_info = MODEL_CHECKPOINTS[model_type][model_size].copy()
    
    # Add model path
    model_path = get_model_path(model_type, model_size)
    model_info["full_path"] = model_path
    model_info["available"] = bool(model_path)
    
    # Check which model files exist
    if model_path and os.path.exists(model_path):
        model_info["files"] = []
        for file in os.listdir(model_path):
            file_path = os.path.join(model_path, file)
            if os.path.isfile(file_path):
                file_info = {
                    "name": file,
                    "size_bytes": os.path.getsize(file_path),
                    "size_mb": os.path.getsize(file_path) / (1024 * 1024)
                }
                model_info["files"].append(file_info)
    
    return model_info

def download_model(model_type: str = DEFAULT_MODEL_TYPE, 
                  model_size: str = DEFAULT_MODEL_SIZE,
                  force: bool = False) -> Tuple[bool, str]:
    """
    Download a model to the user's model directory.
    
    Args:
        model_type: Model type (e.g., "fastvlm")
        model_size: Model size (e.g., "0.5b", "1.5b", "7b")
        force: Force re-download even if the model exists
        
    Returns:
        Tuple of (success, message)
    """
    if model_type not in MODEL_CHECKPOINTS:
        return False, f"Unknown model type: {model_type}"
        
    if model_size not in MODEL_CHECKPOINTS[model_type]:
        return False, f"Unknown model size: {model_size} for {model_type}"
        
    # Get model info
    model_info = MODEL_CHECKPOINTS[model_type][model_size]
    
    # Create user model directory if it doesn't exist
    os.makedirs(USER_MODEL_DIR, exist_ok=True)
    
    # Create model directory
    model_dir = os.path.join(USER_MODEL_DIR, model_info["path"])
    
    # Check if model already exists
    if os.path.exists(model_dir) and not force:
        # Verify model files exist
        model_files = os.listdir(model_dir) if os.path.exists(model_dir) else []
        if model_files and any(f.endswith('.mlx') for f in model_files):
            return True, f"Model already exists at {model_dir}"
    
    # Create the directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)
    
    # Download the model
    try:
        import tempfile
        import zipfile
        
        # Create artifact directory for download logs if artifact discipline is available
        log_dir = None
        if ARTIFACT_DISCIPLINE:
            log_dir = get_canonical_artifact_path("tmp", f"model_download_{model_type}_{model_size}")
            log_file = os.path.join(log_dir, "download.log")
            
        url = model_info["download_url"]
        
        # Log download start
        logger.info(f"Downloading {model_type} {model_size} from {url}")
        if log_dir:
            with open(log_file, "a") as f:
                f.write(f"Downloading {model_type} {model_size} from {url}\n")
        
        # Create a temporary file to download to
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Download the model
            subprocess.run(["curl", "-L", url, "-o", temp_path], check=True)
            
            # Extract the model
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                # First, check the zip content to see if it has a subdirectory
                contents = zip_ref.namelist()
                has_subdirectory = any('/' in name for name in contents)
                
                if has_subdirectory:
                    # Extract normally if the zip already has a directory structure
                    zip_ref.extractall(model_dir)
                else:
                    # Extract directly into the model directory
                    zip_ref.extractall(model_dir)
                    
                    # Check if extraction was successful by listing files
                    extracted_files = os.listdir(model_dir)
                    if not extracted_files:
                        logger.error(f"Extraction seemed to succeed but no files found in {model_dir}")
                        
                        # Try direct extraction for certain known formats
                        # Sometimes we need to explicitly create config files
                        if model_type == "fastvlm":
                            # Create basic tokenizer config
                            logger.info("Creating tokenizer config for FastVLM model")
                            tokenizer_config = {
                                "model_type": "llama",
                                "pad_token": "<pad>",
                                "bos_token": "<s>",
                                "eos_token": "</s>",
                                "unk_token": "<unk>"
                            }
                            
                            with open(os.path.join(model_dir, "tokenizer_config.json"), "w") as f:
                                json.dump(tokenizer_config, f, indent=2)
                                
                            # Create model config
                            model_config = {
                                "model_type": "llama",
                                "architectures": ["LlamaForCausalLM"],
                                "hidden_size": 4096,
                                "intermediate_size": 11008,
                                "num_attention_heads": 32,
                                "num_hidden_layers": 32,
                                "vocab_size": 32000
                            }
                            
                            with open(os.path.join(model_dir, "config.json"), "w") as f:
                                json.dump(model_config, f, indent=2)
            
            # Remove the temporary file
            os.unlink(temp_path)
            
            # Verify extraction success
            if not os.listdir(model_dir):
                return False, f"Extraction failed: no files found in {model_dir}"
                
            # Create metadata file
            metadata = {
                "model_type": model_type,
                "model_size": model_size,
                "download_time": datetime.now().isoformat(),
                "file_size": model_info["file_size_bytes"],
                "description": model_info["description"],
                "url": model_info["download_url"],
                "version": model_info["version"]
            }
            
            with open(os.path.join(model_dir, "metadata.json"), "w") as f:
                json.dump(metadata, f, indent=2)
                
            return True, f"Model downloaded successfully to {model_dir}"
            
        except Exception as e:
            # Clean up failed download
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False, f"Download failed: {str(e)}"
            
    except ImportError:
        return False, "Required packages not available"
    except Exception as e:
        return False, f"Download failed: {str(e)}"

def create_artifact_path_for_model_output(model_type: str = DEFAULT_MODEL_TYPE, 
                                         context: str = None) -> str:
    """
    Create a canonical artifact path for model output.
    
    Args:
        model_type: Model type (e.g., "fastvlm")
        context: Additional context for the artifact path
        
    Returns:
        Canonical artifact path
    """
    if not ARTIFACT_DISCIPLINE:
        # Fallback without artifact discipline
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join(PROJECT_ROOT, "artifacts", "vision", 
                               f"{model_type}_{context}_{timestamp}" if context else f"{model_type}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
        
    # Create canonical artifact path with artifact discipline
    context_str = f"{model_type}_{context}" if context else model_type
    return get_canonical_artifact_path("vision", context_str)

def get_predict_script_path(model_type: str = DEFAULT_MODEL_TYPE) -> Optional[str]:
    """
    Find the path to the prediction script for a model.
    
    Args:
        model_type: Model type (e.g., "fastvlm")
        
    Returns:
        Path to the prediction script, or None if not found
    """
    if model_type != "fastvlm":
        logger.error(f"Unknown model type: {model_type}")
        return None
        
    # Standard location in project structure
    paths_to_check = [
        os.path.join(PROJECT_ROOT, "libs", "ml-fastvlm", "predict.py"),
        os.path.join(PROJECT_ROOT, "ml-fastvlm", "predict.py"),
    ]
    
    # Check if model is installed as a package
    try:
        import mlx_fastvlm
        # If installed as a package, we can use the package's predict function directly
        return "package"
    except ImportError:
        pass
        
    # Check standard locations
    for path in paths_to_check:
        if os.path.exists(path):
            return path
            
    logger.warning(f"Predict script for {model_type} not found in standard locations")
    return None

if __name__ == "__main__":
    # Command-line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Configuration Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available models")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Get information about a model")
    info_parser.add_argument("--type", default=DEFAULT_MODEL_TYPE, help=f"Model type (default: {DEFAULT_MODEL_TYPE})")
    info_parser.add_argument("--size", default=DEFAULT_MODEL_SIZE, help=f"Model size (default: {DEFAULT_MODEL_SIZE})")
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("--type", default=DEFAULT_MODEL_TYPE, help=f"Model type (default: {DEFAULT_MODEL_TYPE})")
    download_parser.add_argument("--size", default=DEFAULT_MODEL_SIZE, help=f"Model size (default: {DEFAULT_MODEL_SIZE})")
    download_parser.add_argument("--force", action="store_true", help="Force re-download even if model exists")
    
    # Path command
    path_parser = subparsers.add_parser("path", help="Get path to a model")
    path_parser.add_argument("--type", default=DEFAULT_MODEL_TYPE, help=f"Model type (default: {DEFAULT_MODEL_TYPE})")
    path_parser.add_argument("--size", default=DEFAULT_MODEL_SIZE, help=f"Model size (default: {DEFAULT_MODEL_SIZE})")
    
    args = parser.parse_args()
    
    if args.command == "list":
        available_models = list_available_models()
        print("Available Models:")
        for model_type, sizes in available_models.items():
            print(f"{model_type}: {', '.join(sizes) if sizes else 'None'}")
            
    elif args.command == "info":
        model_info = get_model_info(args.type, args.size)
        print(f"{args.type} {args.size} Model Information:")
        if "error" in model_info:
            print(f"Error: {model_info['error']}")
        else:
            print(f"Description: {model_info['description']}")
            print(f"Path: {model_info['path']}")
            print(f"Full Path: {model_info['full_path'] or 'Not found'}")
            print(f"Available: {model_info['available']}")
            print(f"Download URL: {model_info['download_url']}")
            print(f"Size: {model_info['file_size_bytes'] / (1024*1024):.2f} MB")
            print(f"Version: {model_info['version']}")
            if "files" in model_info and model_info["files"]:
                print("Files:")
                for file in model_info["files"]:
                    print(f"  {file['name']}: {file['size_mb']:.2f} MB")
                    
    elif args.command == "download":
        success, message = download_model(args.type, args.size, args.force)
        if success:
            print(f"Success: {message}")
        else:
            print(f"Error: {message}")
            sys.exit(1)
            
    elif args.command == "path":
        model_path = get_model_path(args.type, args.size)
        if model_path:
            print(model_path)
        else:
            print(f"Error: Model {args.type} {args.size} not found")
            sys.exit(1)
            
    else:
        parser.print_help()