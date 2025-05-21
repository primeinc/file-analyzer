#!/usr/bin/env python3
"""
Python to Bash adapter for artifact_guard.py

This module provides a Python CLI to bridge between shell scripts and the artifact_guard.py module.
It implements the functionality of artifact_guard_py_adapter.sh in pure Python.
"""

import os
import sys
import json
import argparse
import subprocess
from typing import List, Dict, Optional, Tuple, Any

# Import core artifact guard functionality
from src.core.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    cleanup_artifacts,
    setup_artifact_structure,
    ARTIFACTS_ROOT,
    ARTIFACT_TYPES
)

def shell_command(command: str) -> str:
    """
    Generates a shell command to be sourced by bash scripts.
    
    The implementation prioritizes performance by minimizing Python process spawning.
    Instead of calling back to Python for every path validation, it implements
    the validation logic directly in Bash for better performance in shell scripts.
    
    Args:
        command: Command to generate shell for
        
    Returns:
        Shell script as a string
    """
    if command == "mkdir_guard":
        return _generate_mkdir_guard()
    elif command == "touch_guard":
        return _generate_touch_guard()
    elif command == "cp_guard":
        return _generate_cp_guard()
    elif command == "mv_guard":
        return _generate_mv_guard()
    elif command == "aliases":
        return _generate_aliases()
    else:
        return f"echo 'Unknown command: {command}'"

def _generate_validate_path_function() -> str:
    """Generate a bash function to validate paths efficiently."""
    return """
# Function to validate paths without spawning a new Python process each time
# Uses a list of allowed patterns and common validation rules
validate_artifact_path() {
  local path="$1"
  
  # Get absolute path if it's not already
  if [[ ! "$path" = /* ]]; then
    path="$(pwd)/$path"
  fi
  
  # Check if path is in canonical artifact structure
  if [[ "$path" == "$ARTIFACTS_ROOT"* ]]; then
    # Path is in artifacts directory, check if it's in a valid subdirectory
    local valid_subdirs=("analysis" "vision" "test" "benchmark" "json" "tmp")
    local in_valid_subdir=false
    
    for subdir in "${valid_subdirs[@]}"; do
      if [[ "$path" == "$ARTIFACTS_ROOT/$subdir"* ]]; then
        in_valid_subdir=true
        break
      fi
    done
    
    if [[ "$in_valid_subdir" == "true" ]]; then
      return 0  # Valid canonical path
    fi
  fi
  
  # Check if path is in certain allowed directories
  local project_root="$(dirname "$ARTIFACTS_ROOT")"
  
  # Allow src, tools, tests directories
  if [[ "$path" == "$project_root/src"* ]] || 
     [[ "$path" == "$project_root/tools"* ]] || 
     [[ "$path" == "$project_root/tests"* ]]; then
    return 0  # Valid path in allowed directories
  fi
  
  # Allow some specific files in project root
  if [[ "$path" == "$project_root/.gitignore" ]] || 
     [[ "$path" == "$project_root/README.md" ]] || 
     [[ "$path" == "$project_root/CLAUDE.md" ]] || 
     [[ "$path" == "$project_root/pyproject.toml" ]] || 
     [[ "$path" == "$project_root/artifacts.env" ]]; then
    return 0  # Valid path for specific allowed files
  fi
  
  # If we got here, path is not valid
  return 1
}

validate_paths() {
  local paths=("$@")
  local invalid_paths=()
  
  for path in "${paths[@]}"; do
    if ! validate_artifact_path "$path"; then
      invalid_paths+=("$path")
    fi
  done
  
  if [[ ${#invalid_paths[@]} -gt 0 ]]; then
    echo "ERROR: Non-canonical artifact path(s) detected:" >&2
    for path in "${invalid_paths[@]}"; do
      echo "  - $path" >&2
    done
    echo "All artifact paths must use canonical paths from get_canonical_artifact_path" >&2
    return 1
  fi
  
  return 0
}
"""

def _generate_mkdir_guard() -> str:
    """Generate mkdir_guard function for bash."""
    return """
mkdir_guard() {
  local dirs=()
  local options=()
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -*)
        options+=("$1")
        shift
        ;;
      *)
        dirs+=("$1")
        shift
        ;;
    esac
  done
  
  # Validate all directory paths at once
  if ! validate_paths "${dirs[@]}"; then
    return 1
  fi
  
  # If we get here, all paths are valid, execute the original command
  command mkdir "${options[@]}" "${dirs[@]}"
}
"""

def _generate_touch_guard() -> str:
    """Generate touch_guard function for bash."""
    return """
touch_guard() {
  local files=()
  local options=()
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -*)
        options+=("$1")
        shift
        ;;
      *)
        files+=("$1")
        shift
        ;;
    esac
  done
  
  # Validate all file paths at once
  if ! validate_paths "${files[@]}"; then
    return 1
  fi
  
  # If we get here, all paths are valid, execute the original command
  command touch "${options[@]}" "${files[@]}"
}
"""

def _generate_cp_guard() -> str:
    """Generate cp_guard function for bash."""
    return """
cp_guard() {
  # Extract all arguments
  local args=()
  local target=""
  local has_t_option=false
  local t_target=""
  
  # Process arguments - handle special cases like -t option
  local i=0
  while [[ $# -gt 0 ]]; do
    # Check for -t option which specifies target directory before source files
    if [[ "$1" == "-t" ]]; then
      has_t_option=true
      args+=("$1")
      shift
      # The next argument is the target directory
      if [[ $# -gt 0 ]]; then
        t_target="$1"
        args+=("$1")
        shift
      fi
    else
      args+=("$1")
      shift
    fi
  done
  
  # Determine the target path based on options
  if [[ "$has_t_option" == "true" ]]; then
    # Target is specified with -t option
    target="$t_target"
  else
    # Standard case - last argument is the target
    target="${args[${#args[@]}-1]}"
    # Use array slicing instead of unset to avoid sparse arrays
    args=("${args[@]:0:${#args[@]}-1}")
  fi
  
  # Validate target path using the shell function
  if ! validate_artifact_path "$target"; then
    echo "ERROR: Non-canonical artifact path detected for copy target: $target" >&2
    echo "All artifact files must be created in canonical paths" >&2
    return 1
  fi
  
  # If we get here, the target path is valid, execute the original command
  if [[ "$has_t_option" == "true" ]]; then
    # Already have all arguments in place with the target
    command cp "${args[@]}"
  else
    # Standard form: command cp sources target
    command cp "${args[@]}" "$target"
  fi
}
"""

def _generate_mv_guard() -> str:
    """Generate mv_guard function for bash."""
    return """
mv_guard() {
  # Extract all arguments
  local args=()
  local target=""
  local has_t_option=false
  local t_target=""
  
  # Process arguments - handle special cases like -t option
  local i=0
  while [[ $# -gt 0 ]]; do
    # Check for -t option which specifies target directory before source files
    if [[ "$1" == "-t" ]]; then
      has_t_option=true
      args+=("$1")
      shift
      # The next argument is the target directory
      if [[ $# -gt 0 ]]; then
        t_target="$1"
        args+=("$1")
        shift
      fi
    else
      args+=("$1")
      shift
    fi
  done
  
  # Determine the target path based on options
  if [[ "$has_t_option" == "true" ]]; then
    # Target is specified with -t option
    target="$t_target"
  else
    # Standard case - last argument is the target
    target="${args[${#args[@]}-1]}"
    # Use array slicing instead of unset to avoid sparse arrays
    args=("${args[@]:0:${#args[@]}-1}")
  fi
  
  # Validate target path using the shell function
  if ! validate_artifact_path "$target"; then
    echo "ERROR: Non-canonical artifact path detected for move target: $target" >&2
    echo "All artifact files must be moved to canonical paths" >&2
    return 1
  fi
  
  # If we get here, the target path is valid, execute the original command
  if [[ "$has_t_option" == "true" ]]; then
    # Already have all arguments in place with the target
    command mv "${args[@]}"
  else
    # Standard form: command mv sources target
    command mv "${args[@]}" "$target"
  fi
}
"""

def _generate_aliases() -> str:
    """Generate bash aliases for guarded commands."""
    return """
# Register the overridden commands
alias mkdir=mkdir_guard
alias touch=touch_guard
alias cp=cp_guard
alias mv=mv_guard
"""

def create_env_script() -> str:
    """
    Generate an environment script for shell integration.
    
    Returns:
        Path to the generated file
    """
    env_file = os.path.join(os.path.dirname(ARTIFACTS_ROOT), "artifacts.env")
    
    with open(env_file, 'w') as f:
        f.write("# Artifact environment variables\n")
        f.write("# Source this file to get standard artifact paths\n")
        f.write(f"# Generated by Python adapter on {os.path.basename(__file__)}\n\n")
        f.write(f"export ARTIFACTS_ROOT=\"{ARTIFACTS_ROOT}\"\n")
        
        # Add exports for each artifact type
        for dir_name in ["analysis", "vision", "test", "benchmark", "json", "tmp"]:
            var_name = f"ARTIFACTS_{dir_name.upper()}"
            dir_path = os.path.join(ARTIFACTS_ROOT, dir_name)
            f.write(f"export {var_name}=\"{dir_path}\"\n")
        
        # Add helper functions
        f.write("""
# Helper function to get specific artifact directories
get_artifact_path() {
  local type="$1"
  local name="$2"
  
  # Check if it's a standard type that we can handle directly in bash
  local valid_types=("analysis" "vision" "test" "benchmark" "json" "tmp")
  local found=false
  
  for valid_type in "${valid_types[@]}"; do
    if [[ "$type" == "$valid_type" ]]; then
      found=true
      break
    fi
  done
  
  if [[ "$found" == "true" ]]; then
    # Sanitize the name for use in paths
    # Replace spaces and special characters with underscores
    local safe_name=$(echo "$name" | tr ' ' '_' | tr -c '[:alnum:]_-' '_')
    
    # Add timestamp for uniqueness
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local path="$ARTIFACTS_ROOT/$type/${safe_name}_${timestamp}"
    
    # Create the directory
    mkdir -p "$path"
    echo "$path"
  else
    # Use the Python implementation for non-standard types or complex cases
    python -m src.cli.artifact.adapter create "$type" "$name"
  fi
}

# Clean temporary artifacts
clean_tmp_artifacts() {
  rm -rf "$ARTIFACTS_TMP"/*
  mkdir -p "$ARTIFACTS_TMP"
}

# Load path guards
""")
        
        # Add validation and guard functions
        f.write(_generate_validate_path_function())
        f.write(_generate_mkdir_guard())
        f.write(_generate_touch_guard())
        f.write(_generate_cp_guard())
        f.write(_generate_mv_guard())
        f.write(_generate_aliases())
        
    return env_file

def main():
    """Command-line interface for artifact adapter."""
    parser = argparse.ArgumentParser(description="Python to Bash adapter for artifact_guard.py")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a canonical artifact path")
    create_parser.add_argument("type", choices=ARTIFACT_TYPES, 
                              help="Artifact type")
    create_parser.add_argument("context", help="Artifact context description")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a path against artifact discipline")
    validate_parser.add_argument("path", help="Path to validate")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up artifact directory structure")
    
    # Environment command
    env_parser = subparsers.add_parser("env", help="Generate environment script for shell integration")
    
    # Shell command generator
    shell_parser = subparsers.add_parser("shell", help="Generate shell commands for bash integration")
    shell_parser.add_argument("func", choices=["mkdir_guard", "touch_guard", "cp_guard", "mv_guard", "aliases"],
                             help="Shell function to generate")
    
    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Run commands from stdin in batch mode")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "create":
        # Create canonical artifact path
        path = get_canonical_artifact_path(args.type, args.context)
        print(path)
    elif args.command == "validate":
        # Validate path against artifact discipline
        valid = validate_artifact_path(args.path)
        sys.exit(0 if valid else 1)
    elif args.command == "setup":
        # Set up artifact directory structure
        setup_artifact_structure()
        print(f"Artifact directory structure set up at {ARTIFACTS_ROOT}")
    elif args.command == "env":
        # Generate environment script
        env_file = create_env_script()
        print(f"Generated environment script: {env_file}")
    elif args.command == "shell":
        # Generate shell command
        print(shell_command(args.func))
    elif args.command == "batch":
        # Run commands from stdin in batch mode
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            command = parts[0]
            
            if command == "create" and len(parts) >= 3:
                type_name = parts[1]
                context = " ".join(parts[2:])
                path = get_canonical_artifact_path(type_name, context)
                print(path)
            elif command == "validate" and len(parts) >= 2:
                path = " ".join(parts[1:])
                valid = validate_artifact_path(path)
                print("valid" if valid else "invalid")
            else:
                print(f"Unknown command: {line}")
    else:
        # Show help if no command specified
        parser.print_help()

if __name__ == "__main__":
    main()