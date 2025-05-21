#!/usr/bin/env python3
"""
FastVLM Model Download Utility

This script handles downloading and managing FastVLM model files:
- List available models
- Download models by size
- Check model integrity
- Update existing models
"""

import os
import sys
import argparse
import json
import subprocess
import shutil
import logging
from pathlib import Path
import urllib.request
import hashlib
import tempfile
import zipfile

from artifact_guard import get_canonical_artifact_path, validate_artifact_path, PathGuard

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Model information - size, URL, checksum
MODEL_INFO = {
    "0.5b": {
        "name": "llava-fastvithd_0.5b_stage3",
        "size_mb": 580,
        "url": "https://huggingface.co/apple/ml-fastvlm/resolve/main/checkpoints/llava-fastvithd_0.5b_stage3.zip",
        "md5": "5ee58683b47c8ac1cf68ced7dd48b7c3"
    },
    "1.5b": {
        "name": "llava-fastvithd_1.5b_stage3",
        "size_mb": 1720,
        "url": "https://huggingface.co/apple/ml-fastvlm/resolve/main/checkpoints/llava-fastvithd_1.5b_stage3.zip",
        "md5": "9cd651417e5c0b764df33c3b552eedf9"
    },
    "7b": {
        "name": "llava-fastvithd_7b_stage3",
        "size_mb": 7500,
        "url": "https://huggingface.co/apple/ml-fastvlm/resolve/main/checkpoints/llava-fastvithd_7b_stage3.zip",
        "md5": "f3a83ac0c05f889195b0c761b44d1cf2"
    }
}

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.absolute()

def get_model_dir():
    """Get the directory where models are stored."""
    project_root = get_project_root()
    return project_root / "libs" / "ml-fastvlm" / "checkpoints"

def list_models():
    """List available models and their status."""
    print("\n=== FastVLM Models ===")
    
    model_dir = get_model_dir()
    if not model_dir.exists():
        print(f"Model directory does not exist: {model_dir}")
        print("Run 'python download_models.py download' to download models.")
        return False
    
    print(f"Model directory: {model_dir}")
    
    # Check each model size
    for size, info in MODEL_INFO.items():
        model_name = info["name"]
        model_path = model_dir / model_name
        
        if model_path.exists():
            # Check if model is complete by looking for tokenizer config
            tokenizer_config = model_path / "tokenizer_config.json"
            model_config = model_path / "config.json"
            
            if tokenizer_config.exists() and model_config.exists():
                print(f"✓ {model_name} ({size}) - Installed and ready")
            else:
                print(f"⚠ {model_name} ({size}) - Installed but may be incomplete")
        else:
            print(f"✗ {model_name} ({size}) - Not installed")
            print(f"  Download size: {info['size_mb']}MB")
    
    return True

def calculate_md5(file_path):
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def download_file(url, dest_path, desc=None):
    """Download a file with progress indicator."""
    class DownloadProgressBar:
        def __init__(self, total_size, desc):
            self.total_size = total_size
            self.downloaded = 0
            self.desc = desc or "Downloading"
            
        def __call__(self, count, block_size, total_size):
            self.downloaded += block_size
            percent = min(100, self.downloaded * 100 / self.total_size)
            mb_downloaded = self.downloaded / (1024 * 1024)
            mb_total = self.total_size / (1024 * 1024)
            sys.stdout.write(f"\r{self.desc}: {percent:.1f}% ({mb_downloaded:.1f}MB / {mb_total:.1f}MB)")
            sys.stdout.flush()
    
    # Create temporary download path in artifacts directory
    download_dir = get_canonical_artifact_path("tmp", "model_downloads")
    temp_path = os.path.join(download_dir, os.path.basename(dest_path))
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # Download file with progress bar
        urllib.request.urlretrieve(
            url, 
            temp_path,
            reporthook=DownloadProgressBar(MODEL_INFO[desc]["size_mb"] * 1024 * 1024, f"Downloading {desc} model")
        )
        print()  # New line after progress bar
        
        # Move file to destination after successful download
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.move(temp_path, dest_path)
        
        return True
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False

def extract_zip(zip_path, extract_dir):
    """Extract ZIP file to directory."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return True
    except Exception as e:
        logger.error(f"Error extracting {zip_path}: {e}")
        return False

def download_model(size):
    """Download and install a model by size."""
    if size not in MODEL_INFO:
        logger.error(f"Unknown model size: {size}")
        print(f"Available sizes: {', '.join(MODEL_INFO.keys())}")
        return False
    
    model_info = MODEL_INFO[size]
    model_name = model_info["name"]
    model_url = model_info["url"]
    model_md5 = model_info["md5"]
    
    model_dir = get_model_dir()
    model_path = model_dir / model_name
    
    # Check if model already exists
    if model_path.exists():
        print(f"Model {model_name} already exists at {model_path}")
        print("Checking for completeness...")
        
        # Check if model is complete
        tokenizer_config = model_path / "tokenizer_config.json"
        model_config = model_path / "config.json"
        
        if tokenizer_config.exists() and model_config.exists():
            print(f"✓ Model {model_name} is already installed and complete")
            return True
        else:
            print(f"⚠ Model {model_name} exists but may be incomplete")
            print("Removing existing model directory and downloading again...")
            shutil.rmtree(model_path)
    
    # Create model directory
    os.makedirs(model_dir, exist_ok=True)
    
    # Download ZIP file
    print(f"Downloading {model_name} model ({model_info['size_mb']}MB)...")
    zip_path = model_dir / f"{model_name}.zip"
    
    if not download_file(model_url, zip_path, size):
        logger.error(f"Failed to download {model_name}")
        return False
    
    # Verify checksum
    print("Verifying checksum...")
    actual_md5 = calculate_md5(zip_path)
    if actual_md5 != model_md5:
        logger.error(f"Checksum verification failed for {model_name}")
        logger.error(f"Expected: {model_md5}")
        logger.error(f"Actual: {actual_md5}")
        os.remove(zip_path)
        return False
    
    # Extract ZIP file
    print(f"Extracting {model_name}...")
    if not extract_zip(zip_path, model_dir):
        logger.error(f"Failed to extract {model_name}")
        return False
    
    # Clean up ZIP file
    os.remove(zip_path)
    
    print(f"✓ Successfully installed {model_name}")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FastVLM Model Download Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available models")
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("--size", choices=["0.5b", "1.5b", "7b"], default="0.5b",
                              help="Model size to download (default: 0.5b)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Default to list if no command specified
    if not args.command:
        args.command = "list"
    
    # Execute command
    if args.command == "list":
        if not list_models():
            return 1
    elif args.command == "download":
        if not download_model(args.size):
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())