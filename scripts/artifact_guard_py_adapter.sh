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
    python3 "$SCRIPT_DIR/src/artifact_guard_cli.py" setup > /dev/null
    source "$SCRIPT_DIR/artifacts.env"
  fi
fi

# FUNCTION: get_canonical_artifact_path
# Shell wrapper for Python implementation
# Create a fifo pipe for more efficient communication with Python
PYTHON_PIPE="/tmp/artifact_guard_py_pipe_$$"
PYTHON_PROCESS_PID=""

# Function to initialize the Python process for batched commands
# Only called when needed to avoid unnecessary process creation
function _init_python_process() {
  # If we already have a running Python process, do nothing
  if [[ -n "$PYTHON_PROCESS_PID" && -d "/proc/$PYTHON_PROCESS_PID" ]]; then
    return 0
  fi
  
  # Create a fifo pipe for communication
  rm -f "$PYTHON_PIPE"
  mkfifo "$PYTHON_PIPE"
  
  # Start Python in the background, reading from the pipe
  python3 "$SCRIPT_DIR/src/artifact_guard_cli.py" batch < "$PYTHON_PIPE" &
  PYTHON_PROCESS_PID=$!
  
  # Register cleanup on exit
  trap "_cleanup_python_process" EXIT
}

# Function to clean up Python process and fifo pipe
function _cleanup_python_process() {
  if [[ -n "$PYTHON_PROCESS_PID" ]]; then
    kill $PYTHON_PROCESS_PID 2>/dev/null || true
    PYTHON_PROCESS_PID=""
  fi
  rm -f "$PYTHON_PIPE" 2>/dev/null || true
}

function get_canonical_artifact_path() {
  if [[ $# -ne 2 ]]; then
    echo "ERROR: get_canonical_artifact_path requires 2 arguments: type and context" >&2
    return 1
  fi
  
  local type="$1"
  local context="$2"
  
  # Use direct call for simplicity until batch mode is needed
  # For this simple case, the overhead of starting a new Python process
  # is likely less than the complexity of maintaining a long-running process
  python3 "$SCRIPT_DIR/src/artifact_guard_cli.py" create "$type" "$context"
  
  # NOTE: Batch mode implementation commented out for now as it would require
  # changes to the Python implementation to support a batch CLI mode
  # _init_python_process
  # echo "create $type $context" > "$PYTHON_PIPE"
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
  if python3 "$SCRIPT_DIR/src/artifact_guard_cli.py" validate "$path" > /dev/null; then
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
      # Even with -p flag, strictly validate relative paths to prevent path traversal
      # attacks or creation of directories outside the canonical structure
      
      # Block path traversal attempts or system temp directories
      if [[ "$dir" == *"../"* ]] || [[ "$abs_path" == *"/tmp"* ]] || [[ "$abs_path" == *"/var/tmp"* ]]; then
        echo "ERROR: Path traversal or temporary path not allowed: $dir" >&2
        echo "Use get_canonical_artifact_path to create canonical paths" >&2
        return 1
      fi
      
      # Check if path is attempting to write to artifacts directory
      if [[ "$abs_path" == *"/artifacts/"* ]]; then
        # For artifacts directory, always use strict validation (pass through to validation below)
        :
      else
        # For project structure directories, allow if they are within specific safe project directories
        if [[ "$abs_path" == "$SCRIPT_DIR/src/"* ]] || [[ "$abs_path" == "$SCRIPT_DIR/tools/"* ]] || [[ "$abs_path" == "$SCRIPT_DIR/tests/"* ]]; then
          # Allow but still verify no escaping to parent directories
          if [[ "$dir" != *"../"* ]]; then
            continue
          fi
        fi
        
        # Any other paths (especially those outside project dir) are potentially dangerous
        echo "ERROR: Non-canonical path outside project structure: $dir" >&2
        echo "Use get_canonical_artifact_path to create canonical artifact paths" >&2
        return 1
      fi
    fi
    
    # Special case for temp dirs
    # This is harmonized with Python implementation in artifact_guard.py
    # Both implementations now explicitly reject all temporary system directories
    if [[ "$abs_path" == /tmp* ]] || [[ "$abs_path" == /var/tmp* ]] || [[ "$abs_path" == /private/tmp* ]] || [[ "$abs_path" == /var/folders* ]]; then
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
  command mkdir "${options[@]}" "${dirs[@]}"
}

# FUNCTION: touch_guard
# Override touch to validate paths first
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
  
  # Validate each file path
  for file in "${files[@]}"; do
    if ! validate_artifact_path "$file"; then
      echo "ERROR: Non-canonical artifact path detected: $file" >&2
      echo "All artifact files must be created in canonical paths" >&2
      return 1
    fi
  done
  
  # If we get here, all paths are valid, execute the original command
  command touch "${options[@]}" "${files[@]}"
}

# FUNCTION: cp_guard
# Override cp to validate target path
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
  
  # Validate target path
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

# FUNCTION: mv_guard
# Override mv to validate target path
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
  
  # Validate target path
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

# Register the overridden commands
alias mkdir=mkdir_guard
alias touch=touch_guard
alias cp=cp_guard
alias mv=mv_guard

# Show warnings and info only if not in quiet mode
if [[ "$ARTIFACT_QUIET" != "1" ]]; then
  python3 "$SCRIPT_DIR/src/artifact_guard_cli.py" info
fi

# Echo success on load
if [[ "$ARTIFACT_QUIET" != "1" ]]; then
  echo "Artifact discipline loaded from Python implementation"
fi