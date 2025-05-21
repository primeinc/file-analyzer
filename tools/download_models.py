#!/usr/bin/env python3
"""
Download Models Tool

This script provides a command-line interface for downloading FastVLM models
and storing them in the central model directory (~/.local/share/fastvlm).

Usage:
    download_models.py download --model fastvlm --size 0.5b
    download_models.py info --model fastvlm --size 0.5b
    download_models.py list

This script uses the centralized model configuration system and enforces
proper artifact discipline.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import model configuration
from src.model_config import (
    get_model_path, 
    get_model_info, 
    download_model, 
    list_available_models,
    MODEL_CHECKPOINTS,
    DEFAULT_MODEL_TYPE,
    DEFAULT_MODEL_SIZE
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Download and manage FastVLM models")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument("--model", default=DEFAULT_MODEL_TYPE, help=f"Model type (default: {DEFAULT_MODEL_TYPE})")
    download_parser.add_argument("--size", choices=["0.5b", "1.5b", "7b", "all"], default=DEFAULT_MODEL_SIZE, 
                                help=f"Model size (default: {DEFAULT_MODEL_SIZE})")
    download_parser.add_argument("--force", action="store_true", help="Force re-download even if model exists")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Get information about a model")
    info_parser.add_argument("--model", default=DEFAULT_MODEL_TYPE, help=f"Model type (default: {DEFAULT_MODEL_TYPE})")
    info_parser.add_argument("--size", choices=["0.5b", "1.5b", "7b", "all"], default="all", 
                             help="Model size to show info for (default: all)")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available models")
    
    # Path command
    path_parser = subparsers.add_parser("path", help="Get path to a model")
    path_parser.add_argument("--model", default=DEFAULT_MODEL_TYPE, help=f"Model type (default: {DEFAULT_MODEL_TYPE})")
    path_parser.add_argument("--size", default=DEFAULT_MODEL_SIZE, help=f"Model size (default: {DEFAULT_MODEL_SIZE})")
    
    args = parser.parse_args()
    
    if args.command == "download":
        if args.size == "all":
            # Download all sizes
            sizes = list(MODEL_CHECKPOINTS[args.model].keys())
            print(f"Downloading all {args.model} models: {', '.join(sizes)}...")
            
            for size in sizes:
                print(f"\nDownloading {args.model} {size} model...")
                success, message = download_model(args.model, size, args.force)
                if success:
                    print(f"✓ Success: {message}")
                else:
                    print(f"✗ Error: {message}")
        else:
            # Download single size
            print(f"Downloading {args.model} {args.size} model...")
            success, message = download_model(args.model, args.size, args.force)
            if success:
                print(f"✓ Success: {message}")
            else:
                print(f"✗ Error: {message}")
                sys.exit(1)
            
    elif args.command == "info":
        if args.size == "all":
            # Show info for all sizes
            print(f"Getting information about all {args.model} models...")
            
            for size in MODEL_CHECKPOINTS[args.model].keys():
                model_info = get_model_info(args.model, size)
                
                if "error" in model_info:
                    print(f"\n{args.model} {size}: Error: {model_info['error']}")
                    continue
                    
                print(f"\n{args.model} {size} Model Information:")
                print(f"Description: {model_info['description']}")
                print(f"Version: {model_info['version']}")
                print(f"Path: {model_info['path']}")
                print(f"Full Path: {model_info['full_path'] or 'Not found'}")
                print(f"Available: {'Yes' if model_info['available'] else 'No'}")
                print(f"Size: {model_info['file_size_bytes'] / (1024*1024):.2f} MB")
                
                if "files" in model_info and model_info["files"]:
                    print("Files:")
                    total_size = 0
                    for file in model_info["files"]:
                        print(f"  {file['name']}: {file['size_mb']:.2f} MB")
                        total_size += file['size_bytes']
                    print(f"Total size: {total_size / (1024*1024):.2f} MB")
        else:
            # Show info for single size
            print(f"Getting information about {args.model} {args.size} model...")
            model_info = get_model_info(args.model, args.size)
            
            if "error" in model_info:
                print(f"Error: {model_info['error']}")
                sys.exit(1)
                
            print("\nModel Information:")
            print(f"Description: {model_info['description']}")
            print(f"Version: {model_info['version']}")
            print(f"Path: {model_info['path']}")
            print(f"Full Path: {model_info['full_path'] or 'Not found'}")
            print(f"Available: {'Yes' if model_info['available'] else 'No'}")
            print(f"Size: {model_info['file_size_bytes'] / (1024*1024):.2f} MB")
            
            if "files" in model_info and model_info["files"]:
                print("\nFiles:")
                total_size = 0
                for file in model_info["files"]:
                    print(f"  {file['name']}: {file['size_mb']:.2f} MB")
                    total_size += file['size_bytes']
                print(f"Total size: {total_size / (1024*1024):.2f} MB")
            elif model_info['available']:
                print("\nModel directory exists but no files found")
            else:
                print("\nModel is not available locally. Download it with:")
                print(f"  python {os.path.basename(__file__)} download --model {args.model} --size {args.size}")
            
    elif args.command == "list":
        print("Checking available models...")
        available_models = list_available_models()
        
        print("\nAvailable Models:")
        for model_type, sizes in available_models.items():
            if sizes:
                print(f"✓ {model_type}: {', '.join(sizes)}")
            else:
                print(f"✗ {model_type}: None")
                
        # Provide instructions for downloading if no models found
        if not any(sizes for sizes in available_models.values()):
            print("\nNo models found. To download the default model:")
            print(f"  python {os.path.basename(__file__)} download")
            print("\nTo download a specific model:")
            print(f"  python {os.path.basename(__file__)} download --model fastvlm --size 0.5b")
            
    elif args.command == "path":
        model_path = get_model_path(args.model, args.size)
        if model_path:
            print(model_path)
        else:
            print(f"Error: Model {args.model} {args.size} not found")
            sys.exit(1)
            
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main()