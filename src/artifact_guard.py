#!/usr/bin/env python3
"""
artifact_guard.py - Canonical artifact path discipline enforcement

This module serves as the single source of truth for artifact path discipline,
ensuring that all outputs follow the standardized directory structure.

It provides:
1. Path generation with canonical structure (get_canonical_artifact_path)
2. Path validation against allowed patterns (validate_artifact_path)
3. Runtime enforcement via context manager (PathGuard)
4. CLI tools for artifact management (python -m src.artifact_guard)
5. Path utilities for creating, moving, and managing artifacts

Usage:
    from src.artifact_guard import get_canonical_artifact_path, PathGuard
    
    # Create canonical artifact directory
    artifact_dir = get_canonical_artifact_path("test", "my_test_context")
    
    # Use PathGuard to enforce discipline for file operations
    with PathGuard(artifact_dir):
        with open(os.path.join(artifact_dir, "output.txt"), "w") as f:
            f.write("Test output")
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
import argparse
import glob
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any, Callable

# Known artifact types that match directory structure
ARTIFACT_TYPES = ["analysis", "vision", "test", "benchmark", "json", "tmp"]

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
    
    # Use more robust regex patterns for system directories
    # Special case for system directories that should NEVER be valid for artifact output
    system_temp_patterns = [
        r'^/tmp(/|$)',
        r'^/var/tmp(/|$)',
        r'^/private/tmp(/|$)',
        r'^/var/folders(/|$)'
    ]
    if any(re.match(pattern, abs_path) for pattern in system_temp_patterns):
        # We explicitly reject temp directories for artifacts
        return False
    
    # System directories that should be readable but not writable for artifacts
    system_dir_patterns = [
        r'^/dev(/|$)', 
        r'^/proc(/|$)', 
        r'^/sys(/|$)', 
        r'^/var(/|$)', 
        r'^/etc(/|$)',
        r'^/usr(/|$)', 
        r'^/lib(/|$)', 
        r'^/opt(/|$)', 
        r'^/bin(/|$)',
        r'^/sbin(/|$)',
        r'^/Applications(/|$)',  # macOS applications
        r'^/Library(/|$)',       # macOS system library
        r'^/System(/|$)',        # macOS system
        r'^/Windows(/|$)',       # Windows system
        r'^/Program Files(/|$)', # Windows programs
        r'^/Users/[^/]+/AppData(/|$)' # Windows user app data
    ]
    if any(re.match(pattern, abs_path) for pattern in system_dir_patterns):
        # These directories are valid for the operating system but NOT for our artifacts
        return False
    
    # Also check for paths that look like temporary directories
    temp_path_patterns = [
        r'(/|^)temp(/|$)',
        r'(/|^)tmp(/|$)',
        r'(/|^)temporary(/|$)'
    ]
    if any(re.search(pattern, abs_path.lower()) for pattern in temp_path_patterns):
        # Also reject any directory that looks temporary but isn't in our canonical structure
        if not abs_path.startswith(os.path.join(ARTIFACTS_ROOT, "tmp")):
            return False
    
    # Not a valid artifact path
    return False

def enforce_path_discipline(func: Callable) -> Callable:
    """
    Decorator to enforce path discipline on functions that create or modify files.
    
    Args:
        func: Function to decorate
        
    Returns:
        Wrapped function that validates paths before execution
        
    Example:
        @enforce_path_discipline
        def write_data(output_file, data):
            with open(output_file, 'w') as f:
                f.write(data)
    """
    def wrapper(*args, **kwargs):
        # Get the function signature
        import inspect
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        
        # Inspect parameter names and look for path-like parameters
        for param_name, param_value in bound_args.arguments.items():
            if isinstance(param_value, (str, Path)) and any(kw in param_name.lower() for kw in 
                                                           ['path', 'file', 'dir', 'output', 'destination']):
                if not validate_artifact_path(str(param_value)):
                    # Get caller information for better error message
                    caller_frame = sys._getframe(1)
                    caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
                    
                    # Provide detailed error message
                    raise ValueError(
                        f"ERROR: Non-canonical artifact path detected: {param_value}\n"
                        f"All artifact files must be created in {ARTIFACTS_ROOT}\n"
                        f"Called from: {caller_info}\n"
                        f"Hint: Use get_canonical_artifact_path() to generate valid artifact paths"
                    )
        
        # Call the original function
        return func(*args, **kwargs)
    
    # Update wrapper metadata
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__module__ = func.__module__
    
    return wrapper


class PathGuard:
    """
    Context manager to ensure all file operations respect artifact discipline.
    
    Example:
        with PathGuard(artifact_dir):
            # All file operations within this block will be validated
            with open(os.path.join(artifact_dir, 'output.txt'), 'w') as f:
                f.write("Safe output")
                
    This manager intercepts all calls to the built-in open() function and validates
    paths to ensure they comply with artifact discipline.
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
# REMOVED: Dependency on bash implementation
# We no longer use the bash implementation - Python is now the single source of truth

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

# Add safe file operation functions that respect artifact discipline

def safe_copy(src: str, dst: str) -> str:
    """
    Copy a file with path discipline enforcement.
    
    Args:
        src: Source file path
        dst: Destination file path (must be in a canonical artifact location)
        
    Returns:
        The destination path
        
    Raises:
        ValueError: If the destination path violates artifact discipline
    """
    # Manually validate path here since the decorator sometimes misses validation
    # when the parameter name doesn't match common path patterns
    if not validate_artifact_path(str(dst)):
        caller_frame = sys._getframe(1)
        caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
        raise ValueError(
            f"ERROR: Non-canonical artifact path detected: {dst}\n"
            f"All artifact files must be created in {ARTIFACTS_ROOT}\n"
            f"Called from: {caller_info}\n"
            f"Hint: Use get_canonical_artifact_path() to generate valid artifact paths"
        )
        
    try:
        shutil.copy2(src, dst)
    except Exception as e:
        raise IOError(f"Failed to copy {src} to {dst}: {str(e)}")
    return dst

@enforce_path_discipline
def safe_move(src: str, dst: str) -> str:
    """
    Move a file with path discipline enforcement.
    
    Args:
        src: Source file path
        dst: Destination file path (must be in a canonical artifact location)
        
    Returns:
        The destination path
        
    Raises:
        ValueError: If the destination path violates artifact discipline
    """
    shutil.move(src, dst)
    return dst

@enforce_path_discipline
def safe_mkdir(directory: str, mode: int = 0o777) -> str:
    """
    Create a directory with path discipline enforcement.
    
    Args:
        directory: Directory path (must be in a canonical artifact location)
        mode: Directory permissions (default: 0o777)
        
    Returns:
        The directory path
        
    Raises:
        ValueError: If the directory path violates artifact discipline
    """
    os.makedirs(directory, mode=mode, exist_ok=True)
    return directory

@enforce_path_discipline
def safe_write(file_path: str, content: str, mode: str = 'w') -> str:
    """
    Write content to a file with path discipline enforcement.
    
    Args:
        file_path: File path (must be in a canonical artifact location)
        content: Content to write
        mode: File open mode (default: 'w')
        
    Returns:
        The file path
        
    Raises:
        ValueError: If the file path violates artifact discipline
    """
    with open(file_path, mode) as f:
        f.write(content)
    return file_path

def cleanup_artifacts(retention_days: int = 7, type_name: Optional[str] = None) -> int:
    """
    Clean up old artifacts based on retention policy.
    
    Args:
        retention_days: Number of days to keep artifacts (default: 7)
        type_name: Optional artifact type to clean up (if None, clean all types)
        
    Returns:
        Number of artifacts cleaned up
    """
    import time
    from datetime import datetime, timedelta
    
    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    cutoff_timestamp = cutoff_date.timestamp()
    
    # Get artifact types to clean up
    types_to_clean = [type_name] if type_name else ARTIFACT_TYPES
    
    # Count artifacts cleaned up
    cleaned_count = 0
    
    # Clean up each artifact type
    for artifact_type in types_to_clean:
        artifact_type_dir = os.path.join(ARTIFACTS_ROOT, artifact_type)
        if not os.path.exists(artifact_type_dir):
            continue
            
        # List all artifact directories of this type
        for artifact_dir in os.listdir(artifact_type_dir):
            artifact_path = os.path.join(artifact_type_dir, artifact_dir)
            
            # Skip if not a directory
            if not os.path.isdir(artifact_path):
                continue
                
            # Check manifest file for retention policy
            manifest_path = os.path.join(artifact_path, 'manifest.json')
            retention = retention_days  # Default retention
            
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                        # Get retention days from manifest
                        if 'retention_days' in manifest:
                            retention = manifest['retention_days']
                except (json.JSONDecodeError, IOError):
                    # Use default retention if manifest is invalid
                    pass
                    
            # Get artifact creation time
            try:
                created_time = os.path.getctime(artifact_path)
            except OSError:
                # Use directory modification time if creation time is not available
                created_time = os.path.getmtime(artifact_path)
                
            # Check if artifact is older than retention period
            if created_time < cutoff_timestamp:
                try:
                    # Remove the artifact directory
                    shutil.rmtree(artifact_path)
                    cleaned_count += 1
                except (OSError, IOError) as e:
                    print(f"Error cleaning up {artifact_path}: {str(e)}")
                    
    return cleaned_count

def setup_artifact_structure() -> None:
    """Create the artifact directory structure if it doesn't exist."""
    # Create artifacts root directory
    os.makedirs(ARTIFACTS_ROOT, exist_ok=True)
    
    # Create subdirectories for each artifact type
    for artifact_type in ARTIFACT_TYPES:
        os.makedirs(os.path.join(ARTIFACTS_ROOT, artifact_type), exist_ok=True)
        
    # Create artifacts.env file if it doesn't exist
    env_file = os.path.join(PROJECT_ROOT, "artifacts.env")
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write(f"# Artifact configuration\n")
            f.write(f"ARTIFACTS_ROOT={ARTIFACTS_ROOT}\n")
            f.write(f"ARTIFACT_QUIET=1\n")

def main() -> None:
    """Command-line interface for artifact_guard.py"""
    parser = argparse.ArgumentParser(description="Artifact path discipline management")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a canonical artifact path")
    create_parser.add_argument("type", choices=ARTIFACT_TYPES, help="Artifact type")
    create_parser.add_argument("context", help="Artifact context description")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a path against artifact discipline")
    validate_parser.add_argument("path", help="Path to validate")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old artifacts")
    cleanup_parser.add_argument("--days", type=int, default=7, help="Retention days (default: 7)")
    cleanup_parser.add_argument("--type", choices=ARTIFACT_TYPES, help="Artifact type to clean up")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up artifact directory structure")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "create":
        # Create canonical artifact path
        path = get_canonical_artifact_path(args.type, args.context)
        print(path)
    elif args.command == "validate":
        # Validate path against artifact discipline
        valid = validate_artifact_path(args.path)
        print(f"Path {'IS' if valid else 'is NOT'} valid according to artifact discipline.")
        sys.exit(0 if valid else 1)
    elif args.command == "cleanup":
        # Clean up old artifacts
        count = cleanup_artifacts(args.days, args.type)
        print(f"Cleaned up {count} artifact{'s' if count != 1 else ''}.")
    elif args.command == "setup":
        # Set up artifact directory structure
        setup_artifact_structure()
        print(f"Artifact directory structure set up at {ARTIFACTS_ROOT}")
    else:
        # Show help if no command specified
        parser.print_help()

# Print warning when the module is imported, only if environment variable is not set to quiet
if os.environ.get("ARTIFACT_QUIET", "1") != "1":
    print_warning()

# Execute main function if run as script
if __name__ == "__main__":
    main()