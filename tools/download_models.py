#!/usr/bin/env python3
"""
download_models.py - Script to download model files to the central location

This script downloads the FastVLM models to the user's central storage location.
"""

import os
import sys
import argparse

# Add the parent directory to the path so we can import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model_config import MODELS, download_model, get_model_info

def main():
    parser = argparse.ArgumentParser(description="Download FastVLM models to the central location")
    parser.add_argument("--model", choices=["fastvlm"], default="fastvlm", help="Model type to download")
    parser.add_argument("--size", choices=["0.5b", "1.5b", "7b", "all"], default="all", 
                        help="Model size to download (default: all)")
    parser.add_argument("--info", action="store_true", help="Print model information without downloading")
    
    args = parser.parse_args()
    
    if args.info:
        info = get_model_info()
        print("Model Information:")
        for model_type, sizes in info.items():
            print(f"\n{model_type.upper()}:")
            for size, details in sizes.items():
                user_exists = "✓" if details["user_path_exists"] else "✗"
                project_exists = "✓" if details["project_path_exists"] else "✗"
                print(f"  {size}: {details['name']} (v{details['version']})")
                print(f"    User path: {user_exists}  Project path: {project_exists}")
        
        return
    
    if args.size == "all":
        sizes = list(MODELS[args.model].keys())
    else:
        sizes = [args.size]
    
    for size in sizes:
        try:
            print(f"Downloading {args.model} {size}...")
            path = download_model(args.model, size)
            print(f"Successfully downloaded to {path}")
        except Exception as e:
            print(f"Error downloading {args.model} {size}: {e}")

if __name__ == "__main__":
    main()