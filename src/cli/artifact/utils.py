#!/usr/bin/env python3
"""
Shared utility functions for artifact management.

This module provides utility functions used by multiple modules
in the artifact management package.
"""

import os
from typing import List, Tuple

# Import artifact_guard utilities
from src.core.artifact_guard import ARTIFACTS_ROOT

def check_artifact_sprawl(check_dir: str = ".") -> Tuple[bool, List[str]]:
    """
    Check for artifacts outside the standard structure.
    
    Args:
        check_dir: Directory to check
        
    Returns:
        Tuple[bool, List[str]]: (no_sprawl_found, sprawl_paths)
    """
    # Convert to absolute path
    check_dir = os.path.abspath(check_dir)
    
    # Find artifact directories outside canonical structure
    non_canonical_dirs = []
    
    # Walk the directory tree to find artifacts/ directories
    for root, dirs, _ in os.walk(check_dir):
        # Skip the canonical ARTIFACTS_ROOT
        if root == os.path.dirname(ARTIFACTS_ROOT) and "artifacts" in dirs:
            continue
            
        # Check for artifacts/ directories
        if "artifacts" in dirs:
            artifacts_dir = os.path.join(root, "artifacts")
            if artifacts_dir != ARTIFACTS_ROOT:
                non_canonical_dirs.append(artifacts_dir)
    
    # Return results
    return len(non_canonical_dirs) == 0, non_canonical_dirs