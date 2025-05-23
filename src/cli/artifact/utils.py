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
    project_root = os.path.abspath(os.path.join(os.path.dirname(ARTIFACTS_ROOT), ".."))
    root_artifacts_dir = os.path.join(project_root, "artifacts")
    
    # Skip project root artifacts dir if it's in .gitignore
    skip_root_artifacts = False
    gitignore_path = os.path.join(project_root, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            if any(line.strip() == "/artifacts/" for line in f):
                skip_root_artifacts = True
    
    # Walk the directory tree to find artifacts/ directories
    for root, dirs, _ in os.walk(check_dir):
        # Skip the canonical ARTIFACTS_ROOT
        if root == os.path.dirname(ARTIFACTS_ROOT) and "artifacts" in dirs:
            continue
            
        # Check for artifacts/ directories
        if "artifacts" in dirs:
            artifacts_dir = os.path.join(root, "artifacts")
            # Skip the canonical path
            if artifacts_dir == ARTIFACTS_ROOT:
                continue
            # Skip the root project artifacts if it's properly gitignored
            if skip_root_artifacts and artifacts_dir == root_artifacts_dir:
                continue
            # Otherwise add to non-canonical list
            non_canonical_dirs.append(artifacts_dir)
    
    # Return results
    return len(non_canonical_dirs) == 0, non_canonical_dirs