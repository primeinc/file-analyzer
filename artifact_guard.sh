#!/bin/bash
# artifact_guard.sh - Runtime enforcement of canonical artifact paths
# This script redefines key filesystem commands to enforce path discipline
# Source this file in all scripts to prevent non-canonical artifact usage

# Determine script directory even if run through a symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Ensure artifacts.env is sourced
if [[ -z "$ARTIFACTS_ROOT" ]]; then
  # Source the artifacts environment if not already loaded
  if [[ -f "$SCRIPT_DIR/artifacts.env" ]]; then
    source "$SCRIPT_DIR/artifacts.env"
  else
    echo "ERROR: artifacts.env not found at $SCRIPT_DIR/artifacts.env" >&2
    echo "Artifact enforcement cannot continue without canonical path definitions" >&2
    return 1
  fi
fi

# Generate canonical artifact ID components
if [[ -z "$ARTIFACT_GIT_COMMIT" ]]; then
  # Try to get git commit hash if in a git repo
  if command -v git &> /dev/null && git rev-parse --is-inside-work-tree &> /dev/null; then
    ARTIFACT_GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null)
  else
    ARTIFACT_GIT_COMMIT="nogit"
  fi
fi

# Use CI job ID if available, otherwise use local user/hostname
if [[ -n "$CI_JOB_ID" ]]; then
  ARTIFACT_JOB_ID="ci_${CI_JOB_ID}"
elif [[ -n "$GITHUB_RUN_ID" ]]; then
  ARTIFACT_JOB_ID="gh_${GITHUB_RUN_ID}"
else
  ARTIFACT_JOB_ID="local_$(whoami)"
fi

# Process ID for uniqueness
ARTIFACT_PID="$$"

# Known artifact types (must match directory structure)
ARTIFACT_TYPES=("analysis" "vision" "test" "benchmark" "tmp")

# Global array to store per-script artifact roots (associative array)
# Use declare without -A for bash 3 compatibility
ARTIFACT_ROOTS_USED=()

# Terminal colors for error messages
RED='\033[0;31m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Generate a canonical artifact root path
# Usage: get_canonical_artifact_path <type> <context>
# Returns: canonical artifact path with auto-generated unique ID
get_canonical_artifact_path() {
  local type="$1"
  local context="$2"
  
  # Validate artifact type
  local valid_type=false
  for allowed_type in "${ARTIFACT_TYPES[@]}"; do
    if [[ "$type" == "$allowed_type" ]]; then
      valid_type=true
      break
    fi
  done
  
  if [[ "$valid_type" == "false" ]]; then
    echo "ERROR: Invalid artifact type: $type" >&2
    echo "Valid types: ${ARTIFACT_TYPES[*]}" >&2
    return 1
  fi
  
  # Clean context string (remove special chars, convert to lowercase)
  local clean_context=$(echo "$context" | tr '[:upper:]' '[:lower:]' | tr -c '[:alnum:]' '_')
  
  # Timestamp for uniqueness (ISO8601 format with seconds precision)
  local timestamp=$(date '+%Y%m%d_%H%M%S')
  
  # Generate canonical directory name
  local dir_id="${ARTIFACT_GIT_COMMIT}_${ARTIFACT_JOB_ID}_${ARTIFACT_PID}_${timestamp}"
  if [[ -n "$clean_context" ]]; then
    dir_id="${clean_context}_${dir_id}"
  fi
  
  # Complete path
  local artifact_path="${ARTIFACTS_ROOT}/${type}/${dir_id}"
  
  # Record this path as used (no associative array in basic bash)
  ARTIFACT_ROOTS_USED+=("$artifact_path")
  
  # Create directory and manifest
  mkdir -p "$artifact_path"
  create_artifact_manifest "$artifact_path" "$type" "$context"
  
  echo "$artifact_path"
}

# Create a manifest file for an artifact directory
create_artifact_manifest() {
  local artifact_dir="$1"
  local artifact_type="$2"
  local context="$3"
  local manifest_file="${artifact_dir}/manifest.json"
  
  # Default retention days
  local retention_days=7
  
  # Determine the calling script (stack trace)
  local caller=""
  if [[ -n "${BASH_SOURCE[2]}" ]]; then
    caller="${BASH_SOURCE[2]}"
  else
    caller="unknown"
  fi
  
  # Create manifest JSON
  cat > "$manifest_file" << EOF
{
  "created": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "owner": "$(whoami)",
  "git_commit": "${ARTIFACT_GIT_COMMIT}",
  "ci_job": "${ARTIFACT_JOB_ID}",
  "pid": "${ARTIFACT_PID}",
  "retention_days": ${retention_days},
  "context": {
    "script": "$(basename "$caller")",
    "full_path": "$caller",
    "description": "$context"
  }
}
EOF
}

# Validate if a path is within the canonical artifact structure
# Returns: 0 if valid, 1 if invalid
validate_artifact_path() {
  local path="$1"
  local abs_path
  
  # Convert to absolute path if needed
  if [[ "$path" = /* ]]; then
    abs_path="$path"
  else
    abs_path="$(pwd)/$path"
  fi
  
  # Extract just the artifacts root part for comparison
  local artifacts_root_normalized=$(echo "$ARTIFACTS_ROOT" | sed 's|/$||')
  
  # Check if path is within artifacts root
  if [[ "$abs_path" == "$artifacts_root_normalized"* ]]; then
    # Path is within artifacts root, this is good
    return 0
  fi
  
  # Special case: allow paths that start with /, have common system dirs, and don't have 'artifact' in the name
  if [[ "$abs_path" == /* ]] && \
     [[ "$abs_path" != */artifact* ]] && \
     [[ "$abs_path" == */dev/* || "$abs_path" == */proc/* || "$abs_path" == */sys/* || "$abs_path" == */tmp/* || "$abs_path" == */var/* || "$abs_path" == */etc/* || "$abs_path" == */usr/* || "$abs_path" == */lib/* || "$abs_path" == */opt/* ]]; then
    # System path, allow it
    return 0
  fi
  
  # Special case: allow all other system or binary paths that don't look like user artifacts
  if [[ "$abs_path" == /* ]] && \
     [[ "$abs_path" != */test* ]] && \
     [[ "$abs_path" != */output* ]] && \
     [[ "$abs_path" != */result* ]] && \
     [[ "$abs_path" != */artifact* ]] && \
     [[ "$abs_path" != */vision* ]] && \
     [[ "$abs_path" != */analysis* ]] && \
     [[ "$abs_path" != */benchmark* ]]; then
    # Likely a system path, allow it
    return 0
  fi
  
  # Not a valid artifact path
  return 1
}

# Print a stack trace for debugging
print_stack_trace() {
  local i=0
  echo -e "${BOLD}Stack trace:${NC}" >&2
  while caller_info=$(caller $i); do
    IFS=' ' read -r line func file <<< "$caller_info"
    echo "  $i: $file:$line in function $func" >&2
    ((i++))
  done
}

# Override the mkdir command to enforce artifact discipline
mkdir_guard() {
  # Extract all directory arguments
  local dirs=()
  local options=""
  local parents_flag=false
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -p|--parents)
        parents_flag=true
        options+=" $1"
        shift
        ;;
      -*)
        options+=" $1"
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
    if ! validate_artifact_path "$dir"; then
      echo -e "${RED}${BOLD}ERROR: Non-canonical artifact path detected: $dir${NC}" >&2
      echo -e "${YELLOW}All artifact directories must be created using get_canonical_artifact_path or be in $ARTIFACTS_ROOT${NC}" >&2
      print_stack_trace
      return 1
    fi
  done
  
  # If we get here, all paths are valid, execute the original command
  command mkdir $options "${dirs[@]}"
}

# Override the touch command to enforce artifact discipline
touch_guard() {
  # Extract all file arguments
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
      echo -e "${RED}${BOLD}ERROR: Non-canonical artifact path detected: $file${NC}" >&2
      echo -e "${YELLOW}All artifact files must be created in $ARTIFACTS_ROOT${NC}" >&2
      print_stack_trace
      return 1
    fi
  done
  
  # If we get here, all paths are valid, execute the original command
  command touch $options "${files[@]}"
}

# Override the cp command to enforce artifact discipline for target files
cp_guard() {
  # Extract all arguments
  local args=()
  local target=""
  local options=""
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    args+=("$1")
    shift
  done
  
  # The last argument is the target
  target="${args[${#args[@]}-1]}"
  unset "args[${#args[@]}-1]"
  
  # Validate the target path
  if ! validate_artifact_path "$target"; then
    echo -e "${RED}${BOLD}ERROR: Non-canonical artifact path detected for copy target: $target${NC}" >&2
    echo -e "${YELLOW}All artifact files must be created in $ARTIFACTS_ROOT${NC}" >&2
    print_stack_trace
    return 1
  fi
  
  # If we get here, the target path is valid, execute the original command
  command cp "${args[@]}" "$target"
}

# Override the mv command to enforce artifact discipline for target location
mv_guard() {
  # Extract all arguments
  local args=()
  local target=""
  local options=""
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    args+=("$1")
    shift
  done
  
  # The last argument is the target
  target="${args[${#args[@]}-1]}"
  unset "args[${#args[@]}-1]"
  
  # Validate the target path
  if ! validate_artifact_path "$target"; then
    echo -e "${RED}${BOLD}ERROR: Non-canonical artifact path detected for move target: $target${NC}" >&2
    echo -e "${YELLOW}All artifact files must be moved to $ARTIFACTS_ROOT${NC}" >&2
    print_stack_trace
    return 1
  fi
  
  # If we get here, the target path is valid, execute the original command
  command mv "${args[@]}" "$target"
}

# Warn about usage of unprotected commands (e.g., redirections)
warn_artifact_discipline() {
  cat << EOF
${YELLOW}${BOLD}WARNING: Artifact Discipline${NC}
Remember that while mkdir, touch, cp, and mv are guarded against non-canonical paths,
other ways of writing to the filesystem are not protected, such as:

  - I/O redirection (>, >>)
  - echo "text" > file
  - cat file > output
  - printf "text" > file

For full artifact discipline, ensure all files are created within canonical directories
obtained via ${BOLD}get_canonical_artifact_path${NC}.

Example:
  # Get a canonical artifact path
  ARTIFACT_DIR=\$(get_canonical_artifact_path test "my_test_context")
  
  # Write all files within this directory
  echo "Test output" > "\$ARTIFACT_DIR/output.txt"
EOF
}

# Register the overridden commands
alias mkdir=mkdir_guard
alias touch=touch_guard
alias cp=cp_guard
alias mv=mv_guard

# Warn about artifact discipline when this script is sourced
warn_artifact_discipline

echo -e "${BOLD}Artifact path discipline enforced.${NC}"
echo -e "Use ${BOLD}get_canonical_artifact_path <type> \"context\"${NC} to create canonical paths."
echo -e "Valid artifact types: ${ARTIFACT_TYPES[*]}"