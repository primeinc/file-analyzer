#!/usr/bin/env python3
"""
model_config.py - Configuration for model paths and versions

This module centralizes the configuration for model paths, ensuring consistent
access to model files across different environments.
"""

import os
import json
from pathlib import Path

# Define central locations for model storage
USER_MODEL_DIR = os.path.expanduser("~/.local/share/fastvlm/checkpoints")
PROJECT_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "libs/ml-fastvlm/checkpoints")

# Ensure directories exist
os.makedirs(USER_MODEL_DIR, exist_ok=True)
os.makedirs(PROJECT_MODEL_DIR, exist_ok=True)

# Model configuration
MODELS = {
    "fastvlm": {
        "0.5b": {
            "name": "llava-fastvithd_0.5b_stage3",
            "url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_0.5b_stage3.zip",
            "version": "v1.0.2"
        },
        "1.5b": {
            "name": "llava-fastvithd_1.5b_stage3",
            "url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_1.5b_stage3.zip",
            "version": "v1.0.2"
        },
        "7b": {
            "name": "llava-fastvithd_7b_stage3",
            "url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_7b_stage3.zip",
            "version": "v1.0.2"
        }
    }
}

def get_model_path(model_type, model_size):
    """
    Get the path to a model, checking user directory first, then project directory.
    
    Args:
        model_type: Type of model (e.g., "fastvlm")
        model_size: Size variant (e.g., "0.5b", "1.5b", "7b")
        
    Returns:
        Path to the model directory
    """
    if model_type not in MODELS:
        raise ValueError(f"Unknown model type: {model_type}")
    
    if model_size not in MODELS[model_type]:
        raise ValueError(f"Unknown model size: {model_size}")
    
    model_name = MODELS[model_type][model_size]["name"]
    
    # Check user directory first
    user_path = os.path.join(USER_MODEL_DIR, model_name)
    if os.path.exists(user_path):
        return user_path
    
    # Then check project directory
    project_path = os.path.join(PROJECT_MODEL_DIR, model_name)
    if os.path.exists(project_path):
        return project_path
    
    # If neither exists, return the user path as the preferred location
    return user_path

def download_model(model_type, model_size):
    """
    Download a model if it doesn't exist.
    
    Args:
        model_type: Type of model (e.g., "fastvlm")
        model_size: Size variant (e.g., "0.5b", "1.5b", "7b")
        
    Returns:
        Path to the downloaded model
    """
    import subprocess
    import tempfile
    import zipfile
    
    model_info = MODELS[model_type][model_size]
    model_name = model_info["name"]
    model_url = model_info["url"]
    
    target_dir = USER_MODEL_DIR
    target_path = os.path.join(target_dir, model_name)
    
    # If model already exists, return its path
    if os.path.exists(target_path):
        return target_path
    
    print(f"Downloading {model_name} to {target_dir}...")
    
    # Create a temporary file to download to
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Download the model
        subprocess.run(["curl", "-L", model_url, "-o", temp_path], check=True)
        
        # Extract the model
        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        
        # Remove the temporary file
        os.unlink(temp_path)
        
        return target_path
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise Exception(f"Failed to download model: {e}")

def get_model_info():
    """Returns information about available models"""
    models_info = {}
    
    # Check user directory
    for model_type, sizes in MODELS.items():
        models_info[model_type] = {}
        for size, info in sizes.items():
            model_name = info["name"]
            user_path = os.path.join(USER_MODEL_DIR, model_name)
            project_path = os.path.join(PROJECT_MODEL_DIR, model_name)
            
            models_info[model_type][size] = {
                "name": model_name,
                "version": info["version"],
                "user_path_exists": os.path.exists(user_path),
                "project_path_exists": os.path.exists(project_path),
                "active_path": get_model_path(model_type, size)
            }
    
    return models_info

if __name__ == "__main__":
    # Print model information when run directly
    info = get_model_info()
    print(json.dumps(info, indent=2))
    
    # Example usage
    print("\nExample usage:")
    print("To get the path to the FastVLM 0.5B model:")
    print("  from src.model_config import get_model_path")
    print("  model_path = get_model_path('fastvlm', '0.5b')")