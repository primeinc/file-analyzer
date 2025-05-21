#!/usr/bin/env python3
"""
artifact_guard.py - Python implementation of artifact path discipline

This module enforces the use of canonical artifact paths in Python scripts,
ensuring that all outputs follow the standardized directory structure.
"""

import os
import json
import sys
import re
import time
import subprocess
import tempfile
import datetime
import uuid
import socket
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple

# Known artifact types that match directory structure
ARTIFACT_TYPES = ["analysis", "vision", "test", "benchmark", "tmp"]

# Determine project root and artifacts root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTIFACTS_ROOT = os.path.join(PROJECT_ROOT, "artifacts")

# Cache for canonical paths
_ARTIFACT_ROOTS_USED = []

def _get_git_commit() -> str:
    """Get the current git commit hash, or 'nogit' if not in a git repo."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], 
            stderr=subprocess.DEVNULL,
            universal_newlines=True
        ).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "nogit"

def _get_job_id() -> str:
    """Get the job ID for the current process."""
    # Try CI environment variables first
    if os.environ.get("CI_JOB_ID"):
        return f"ci_{os.environ['CI_JOB_ID']}"
    elif os.environ.get("GITHUB_RUN_ID"):
        return f"gh_{os.environ['GITHUB_RUN_ID']}"
    else:
        # Use local username
        import getpass
        return f"local_{getpass.getuser()}"

# Generate artifact ID components once on module import
ARTIFACT_GIT_COMMIT = _get_git_commit()
ARTIFACT_JOB_ID = _get_job_id()

def get_canonical_artifact_path(type_name: str, context: str) -> str:
    """
    Generate a canonical artifact path with auto-generated unique ID.
    
    Args:
        type_name: Artifact type (analysis, vision, test, benchmark, tmp)
        context: Description of the artifact context
        
    Returns:
        Canonical path to the artifact directory
        
    Raises:
        ValueError: If the artifact type is invalid
    """
    # Validate artifact type
    if type_name not in ARTIFACT_TYPES:
        raise ValueError(f"Invalid artifact type: {type_name}. Valid types: {', '.join(ARTIFACT_TYPES)}")
    
    # Clean context string (remove special chars, convert to lowercase)
    clean_context = re.sub(r'[^a-z0-9]', '_', context.lower())
    
    # Generate unique identifiers
    pid = os.getpid()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Generate canonical directory name
    dir_id = f"{ARTIFACT_GIT_COMMIT}_{ARTIFACT_JOB_ID}_{pid}_{timestamp}"
    if clean_context:
        dir_id = f"{clean_context}_{dir_id}"
    
    # Complete path
    artifact_path = os.path.join(ARTIFACTS_ROOT, type_name, dir_id)
    
    # Record this path as used
    _ARTIFACT_ROOTS_USED.append(artifact_path)
    
    # Create directory and manifest
    os.makedirs(artifact_path, exist_ok=True)
    _create_artifact_manifest(artifact_path, type_name, context)
    
    return artifact_path

def _create_artifact_manifest(artifact_dir: str, artifact_type: str, context: str) -> None:
    """
    Create a manifest file for an artifact directory.
    
    Args:
        artifact_dir: Path to the artifact directory
        artifact_type: Type of artifact (analysis, vision, test, benchmark, tmp)
        context: Description of the artifact context
    """
    manifest_file = os.path.join(artifact_dir, "manifest.json")
    
    # Default retention days
    retention_days = 7
    
    # Determine the calling script
    frame = sys._getframe(2)
    caller = frame.f_code.co_filename if frame else "unknown"
    
    # Create manifest JSON
    manifest = {
        "created": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "owner": os.getenv("USER", "unknown"),
        "git_commit": ARTIFACT_GIT_COMMIT,
        "ci_job": ARTIFACT_JOB_ID,
        "pid": os.getpid(),
        "retention_days": retention_days,
        "context": {
            "script": os.path.basename(caller),
            "full_path": caller,
            "description": context
        }
    }
    
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

def validate_artifact_path(path: str) -> bool:
    """
    Validate if a path is within the canonical artifact structure.
    
    Args:
        path: Path to validate
        
    Returns:
        True if the path is valid, False otherwise
    """
    # Convert to absolute path if needed
    abs_path = os.path.abspath(path)
    
    # Check if path is within artifacts root
    if abs_path.startswith(ARTIFACTS_ROOT):
        return True
    
    # Check if path is within project structure (src, tools, tests)
    for valid_dir in ['src', 'tools', 'tests', '.git', '.github', '.githooks']:
        if abs_path.startswith(os.path.join(PROJECT_ROOT, valid_dir)):
            return True
    
    # Check if path is a file directly in project root
    if os.path.dirname(abs_path) == PROJECT_ROOT:
        # Root directory files (README.md, etc.)
        base_name = os.path.basename(abs_path)
        # Prohibited patterns for files in root
        if (base_name.startswith('test_') or 
            '_results' in base_name or 
            base_name.startswith('fastvlm_test_') or
            base_name.startswith('analysis_')):
            return False
        # Basic file in root is okay
        return True
    
    # ===== IMPORTANT: We need to strictly limit system directory access =====
    # Only allow read access to core system directories, not write access
    # For artifact discipline, we should NOT allow writing to system temp dirs
    # as these bypass our artifact structure
    
    # Special case for system directories that should NEVER be valid for artifact output
    system_temp_dirs = ['/tmp/', tempfile.gettempdir()]
    if any(abs_path.startswith(d) for d in system_temp_dirs):
        # We explicitly reject temp directories for artifacts
        return False
    
    # System directories that should be readable but not writable for artifacts
    read_only_system_dirs = [
        '/dev/', '/proc/', '/sys/', '/var/', '/etc/',
        '/usr/', '/lib/', '/opt/', '/bin/'
    ]
    if any(abs_path.startswith(d) for d in read_only_system_dirs):
        # These directories are valid for the operating system but NOT for our artifacts
        return False
    
    # Not a valid artifact path
    return False

class PathGuard:
    """
    Context manager to ensure all file operations respect artifact discipline.
    
    Example:
        with PathGuard(artifact_dir):
            # All file operations within this block will be validated
            with open(os.path.join(artifact_dir, 'output.txt'), 'w') as f:
                f.write("Safe output")
    """
    def __init__(self, artifact_dir: str):
        self.artifact_dir = artifact_dir
        self.original_open = None
        self._enforce_validation = True
        
    def __enter__(self):
        # Override built-in open function
        import builtins
        self.original_open = builtins.open
        builtins.open = self._guarded_open
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original open function
        import builtins
        builtins.open = self.original_open
        
    def _guarded_open(self, file, mode='r', *args, **kwargs):
        # Check if this is a write operation
        if self._enforce_validation and ('w' in mode or 'a' in mode or '+' in mode):
            # Get absolute path for validation
            abs_path = os.path.abspath(file)
            
            # Check if the path is valid
            if not validate_artifact_path(abs_path):
                # Get caller information for better error message
                caller_frame = sys._getframe(1)
                caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
                
                # Provide detailed error message
                raise ValueError(
                    f"ERROR: Non-canonical artifact path detected: {abs_path}\n"
                    f"All artifact files must be created in {ARTIFACTS_ROOT}\n"
                    f"Called from: {caller_info}\n"
                    f"Hint: Use get_canonical_artifact_path() to generate valid artifact paths"
                )
                
        # If validation passes or it's a read operation, proceed with the original open
        return self.original_open(file, mode, *args, **kwargs)

# Function to shell out to the Bash implementation if needed
def get_bash_canonical_path(type_name: str, context: str) -> str:
    """
    Get a canonical artifact path using the Bash implementation.
    Useful for ensuring exact compatibility with the Bash version.
    
    Args:
        type_name: Artifact type (analysis, vision, test, benchmark, tmp)
        context: Description of the artifact context
        
    Returns:
        Canonical path to the artifact directory from Bash
        
    Raises:
        ValueError: If the bash command fails
    """
    bash_script = os.path.join(PROJECT_ROOT, "artifact_guard.sh")
    try:
        cmd = f'source "{bash_script}" && get_canonical_artifact_path {type_name} "{context}" && echo'
        result = subprocess.check_output(['bash', '-c', cmd], universal_newlines=True).strip()
        return result
    except subprocess.SubprocessError as e:
        raise ValueError(f"Failed to get canonical path from Bash: {e}")

def print_warning():
    """Print a warning about artifact discipline."""
    yellow = '\033[0;33m' if sys.stdout.isatty() else ''
    bold = '\033[1m' if sys.stdout.isatty() else ''
    reset = '\033[0m' if sys.stdout.isatty() else ''
    
    print(f"{yellow}{bold}WARNING: Python Artifact Discipline{reset}")
    print("Ensure all file operations respect the canonical artifact paths.")
    print("Always use get_canonical_artifact_path for artifact directories:")
    print("")
    print("    from src.artifact_guard import get_canonical_artifact_path")
    print("    artifact_dir = get_canonical_artifact_path('test', 'my_test')")
    print("    output_file = os.path.join(artifact_dir, 'output.txt')")
    print("")
    print(f"Valid artifact types: {', '.join(ARTIFACT_TYPES)}")

# Print warning when the module is imported, only if environment variable is not set to quiet
if os.environ.get("ARTIFACT_QUIET", "1") != "1":
    print_warning()