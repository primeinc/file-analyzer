#!/usr/bin/env python3
"""
Shared utilities for benchmark command modules
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Check if PIL is available
PIL_AVAILABLE = False
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    pass

# Import artifact_guard utilities
from src.core.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard
)

def find_test_images():
    """
    Find test images in canonical artifact paths and test_data directory.
    
    Attempts multiple strategies to find suitable test images:
    1. Checks canonical benchmark test_images directory
    2. Checks test_data/images directory
    3. Downloads sample images if none found
    
    Returns:
        List of Path objects pointing to test images
    """
    # Look in canonical benchmark path
    benchmark_path = get_canonical_artifact_path("benchmark", "test_images")
    image_list = []
    
    # Check if directory exists and contains images
    if os.path.exists(benchmark_path):
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp"]:
            image_list.extend(list(Path(benchmark_path).glob(f"*{ext}")))
    
    # If no images found in benchmark path, check test_data directory
    if not image_list:
        # Get project root
        project_root = Path(__file__).resolve().parents[3]
        test_path = project_root / "test_data" / "images"
        
        if test_path.exists():
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp"]:
                image_list.extend(list(test_path.glob(f"*{ext}")))
            
    return image_list

def format_size(path):
    """Format file size nicely"""
    size_bytes = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def get_image_info(image_path):
    """Get image dimensions and size"""
    if not PIL_AVAILABLE:
        return {"size": format_size(image_path), "dimensions": "Unknown (PIL not available)"}
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            return {
                "size": format_size(image_path),
                "dimensions": f"{width}x{height}",
                "format": img.format
            }
    except Exception as e:
        return {"size": format_size(image_path), "dimensions": f"Error: {str(e)}"}