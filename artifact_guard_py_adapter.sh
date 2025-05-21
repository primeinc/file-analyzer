#!/bin/bash
# artifact_guard_py_adapter.sh - Shim for artifact_guard.sh that uses Python implementation
# This file provides a drop-in replacement for artifact_guard.sh that shells out to Python

# Strict bash mode to catch more errors
set -euo pipefail

# Ensure we're in the project root directory
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Set ARTIFACT_QUIET=1 to suppress warnings
ARTIFACT_QUIET=${ARTIFACT_QUIET:-1}

# Import artifact paths from environment if available, otherwise create them
if [[ -z "${ARTIFACTS_ROOT:-}" ]]; then
  if [[ -f "$SCRIPT_DIR/artifacts.env" ]]; then
    source "$SCRIPT_DIR/artifacts.env"
  else
    # Run Python setup and create artifacts.env
    python "$SCRIPT_DIR/src/artifact_guard_cli.py" setup > /dev/null
    source "$SCRIPT_DIR/artifacts.env"
  fi
fi

# FUNCTION: get_canonical_artifact_path
# Shell wrapper for Python implementation
function get_canonical_artifact_path() {
  if [[ $# -ne 2 ]]; then
    echo "ERROR: get_canonical_artifact_path requires 2 arguments: type and context" >&2
    return 1
  fi
  
  local type="$1"
  local context="$2"
  
  # Call Python implementation
  python "$SCRIPT_DIR/src/artifact_guard_cli.py" create "$type" "$context"
}

# FUNCTION: validate_artifact_path
# Shell wrapper for Python implementation
function validate_artifact_path() {
  if [[ $# -ne 1 ]]; then
    echo "ERROR: validate_artifact_path requires 1 argument: path" >&2
    return 1
  fi
  
  local path="$1"
  
  # Call Python implementation (capture return code)
  if python "$SCRIPT_DIR/src/artifact_guard_cli.py" validate "$path" > /dev/null; then
    return 0  # Valid path (success)
  else
    return 1  # Invalid path (failure)
  fi
}

# FUNCTION: mkdir_guard
# Override mkdir to validate paths first
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
  
  # Validate each directory path
  for dir in "${dirs[@]}"; do
    # Get absolute path
    local abs_path
    if [[ "$dir" = /* ]]; then
      abs_path="$dir"
    else
      abs_path="$(pwd)/$dir"
    fi
    
    # For -p option with relative paths, we need special handling
    # but must still validate paths in artifacts directory
    local has_p_flag=false
    for opt in "${options[@]}"; do
      if [[ "$opt" == "-p" ]]; then
        has_p_flag=true
        break
      fi
    done
    
    if [[ "$has_p_flag" == true ]] && [[ ! "$dir" == /* ]]; then
      # Only allow relative paths within current directory that don't try
      # to escape to sensitive locations using ../
      if [[ "$dir" == *"../"* ]] || [[ "$abs_path" == *"/tmp"* ]] || [[ "$abs_path" == *"/var/tmp"* ]]; then
        echo "ERROR: Path traversal or temporary path not allowed: $dir" >&2
        echo "Use get_canonical_artifact_path to create canonical paths" >&2
        return 1
      fi
      
      # Check if path is attempting to write to artifacts directory
      if [[ "$abs_path" == *"/artifacts/"* ]]; then
        # For artifacts directory, continue with strict validation below
        :
      else
        # For other directories, allow if they are in project structure
        if [[ "$abs_path" == *"/src/"* ]] || [[ "$abs_path" == *"/tools/"* ]] || [[ "$abs_path" == *"/tests/"* ]]; then
          continue
        fi
      fi
    fi
    
    # Special case for temp dirs
    if [[ "$abs_path" == /tmp* ]] || [[ "$abs_path" == /var/tmp* ]] || [[ "$abs_path" == /private/tmp* ]]; then
      echo "ERROR: Temporary paths are not allowed: $dir" >&2
      echo "Use get_canonical_artifact_path tmp 'context' to create canonical temporary paths" >&2
      return 1
    fi
    
    # Continue with regular validation
    if ! validate_artifact_path "$dir"; then
      echo "ERROR: Non-canonical artifact path detected: $dir" >&2
      echo "All artifact directories must be created using get_canonical_artifact_path" >&2
      return 1
    fi
  done
  
  # If we get here, all paths are valid, execute the original command
  command mkdir $options "${dirs[@]}"
}

# FUNCTION: touch_guard
# Override touch to validate paths first
touch_guard() {
  local files=()
  local options=""
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -*)
        options+=" $1"
        shift
        ;;
      *)
        files+=("$1")
        shift
        ;;
    esac
  done
  
  # Validate each file path
  for file in "${files[@]}"; do
    if ! validate_artifact_path "$file"; then
      echo "ERROR: Non-canonical artifact path detected: $file" >&2
      echo "All artifact files must be created in canonical paths" >&2
      return 1
    fi
  done
  
  # If we get here, all paths are valid, execute the original command
  command touch $options "${files[@]}"
}

# FUNCTION: cp_guard
# Override cp to validate target path
cp_guard() {
  # Extract all arguments
  local args=()
  local target=""
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    args+=("$1")
    shift
  done
  
  # The last argument is the target
  target="${args[${#args[@]}-1]}"
  unset "args[${#args[@]}-1]"
  
  # Validate target path
  if ! validate_artifact_path "$target"; then
    echo "ERROR: Non-canonical artifact path detected for copy target: $target" >&2
    echo "All artifact files must be created in canonical paths" >&2
    return 1
  fi
  
  # If we get here, the target path is valid, execute the original command
  command cp "${args[@]}" "$target"
}

# FUNCTION: mv_guard
# Override mv to validate target path
mv_guard() {
  # Extract all arguments
  local args=()
  local target=""
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    args+=("$1")
    shift
  done
  
  # The last argument is the target
  target="${args[${#args[@]}-1]}"
  unset "args[${#args[@]}-1]"
  
  # Validate target path
  if ! validate_artifact_path "$target"; then
    echo "ERROR: Non-canonical artifact path detected for move target: $target" >&2
    echo "All artifact files must be moved to canonical paths" >&2
    return 1
  fi
  
  # If we get here, the target path is valid, execute the original command
  command mv "${args[@]}" "$target"
}

# Register the overridden commands
alias mkdir=mkdir_guard
alias touch=touch_guard
alias cp=cp_guard
alias mv=mv_guard

# Show warnings and info only if not in quiet mode
if [[ "$ARTIFACT_QUIET" != "1" ]]; then
  python "$SCRIPT_DIR/src/artifact_guard_cli.py" info
fi

# Echo success on load
if [[ "$ARTIFACT_QUIET" != "1" ]]; then
  echo "Artifact discipline loaded from Python implementation"
fi