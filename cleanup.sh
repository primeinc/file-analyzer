#!/bin/bash
# Centralized Artifact Cleanup Utility
# This script manages the lifecycle of all test artifacts and provides a single
# canonical directory structure for all output artifacts.

# Determine script directory even if run through a symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Constants
ARTIFACTS_ROOT="$(realpath "$SCRIPT_DIR/artifacts")"
CONFIG_FILE=".artifact-config.json"
LOG_FILE="$SCRIPT_DIR/cleanup.log"
DEFAULT_RETENTION_DAYS=7

# Color and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Create log function 
log() {
  local level="$1"
  local message="$2"
  echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" | tee -a "$LOG_FILE"
}

# Create directories if they don't exist
setup_artifact_structure() {
  mkdir -p "$ARTIFACTS_ROOT"
  mkdir -p "$ARTIFACTS_ROOT/test"
  mkdir -p "$ARTIFACTS_ROOT/analysis"
  mkdir -p "$ARTIFACTS_ROOT/vision"
  mkdir -p "$ARTIFACTS_ROOT/benchmark"
  mkdir -p "$ARTIFACTS_ROOT/json"
  mkdir -p "$ARTIFACTS_ROOT/tmp"

  # Create .gitignore in each directory to prevent git tracking
  for dir in "$ARTIFACTS_ROOT"/*; do
    if [ -d "$dir" ]; then
      echo "*" > "$dir/.gitignore"
    fi
  done

  # Create artifact config file if it doesn't exist
  if [ ! -f "$ARTIFACTS_ROOT/$CONFIG_FILE" ]; then
    cat > "$ARTIFACTS_ROOT/$CONFIG_FILE" << EOF
{
  "retention_days": $DEFAULT_RETENTION_DAYS,
  "structure": {
    "test": "Test outputs and results",
    "analysis": "File analysis results",
    "vision": "Vision model analysis outputs",
    "benchmark": "Performance benchmark results",
    "json": "JSON validation results",
    "tmp": "Temporary files (cleared on every run)"
  }
}
EOF
  fi

  log "INFO" "Artifact directory structure created at $ARTIFACTS_ROOT"
}

# Get a path in the artifacts directory without excessive timestamps
# Usage: get_artifact_path <type> <n>
# Example: get_artifact_path test vision_basic
get_artifact_path() {
  local type="$1"
  local name="${2:-output}"
  
  case "$type" in
    analysis|vision|test|benchmark|json|tmp)
      local artifact_path="$ARTIFACTS_ROOT/$type/$name"
      mkdir -p "$artifact_path"
      echo "$artifact_path"
      ;;
    *)
      echo "Unknown artifact type: $type" >&2
      echo "Valid types: analysis, vision, test, benchmark, json, tmp" >&2
      return 1
      ;;
  esac
}

# Prevent running more than one cleanup process at a time
LOCK_FILE="/tmp/file-analyzer-cleanup.lock"
cleanup_lock() {
  if [ -f "$LOCK_FILE" ]; then
    pid=$(cat "$LOCK_FILE")
    if ps -p "$pid" > /dev/null; then
      log "WARN" "Another cleanup process is already running (PID: $pid)"
      exit 1
    else
      log "WARN" "Removing stale lock file"
      rm -f "$LOCK_FILE"
    fi
  fi
  echo $$ > "$LOCK_FILE"
  trap 'rm -f "$LOCK_FILE"' EXIT
}

# Clean artifacts based on retention policy
clean_artifacts() {
  local default_retention_days=$DEFAULT_RETENTION_DAYS
  
  if [ -f "$ARTIFACTS_ROOT/$CONFIG_FILE" ]; then
    # Use Python JSON parser to extract retention_days value
    default_retention_days=$(python3 "$SCRIPT_DIR/src/json_parser.py" "$ARTIFACTS_ROOT/$CONFIG_FILE" "retention_days" "$DEFAULT_RETENTION_DAYS")
    # If empty result, use default
    if [ -z "$default_retention_days" ]; then
      default_retention_days=$DEFAULT_RETENTION_DAYS
    fi
  fi

  log "INFO" "Cleaning artifacts based on retention policies (default: $default_retention_days days)..."

  # Find all artifact directories
  find "$ARTIFACTS_ROOT" -type d -path "$ARTIFACTS_ROOT/*/*/*" | while read dir; do
    if [[ "$dir" == *".git"* ]]; then
      continue
    fi
    
    # Check for manifest file to get specific retention policy
    local manifest_file="$dir/manifest.json"
    local retention_days=$default_retention_days
    
    if [ -f "$manifest_file" ]; then
      # Extract retention_days from manifest using Python JSON parser
      local manifest_retention=$(python3 "$SCRIPT_DIR/src/json_parser.py" "$manifest_file" "retention_days" "")
      if [ -n "$manifest_retention" ]; then
        retention_days=$manifest_retention
      fi
    fi
    
    # Get age in days
    local creation_time=$(stat -c "%Y" "$dir" 2>/dev/null || stat -f "%m" "$dir" 2>/dev/null)
    local current_time=$(date +%s)
    local age_days=$(( (current_time - creation_time) / 86400 ))
    
    # Check if artifact is older than its specific retention period
    if [ $age_days -gt $retention_days ]; then
      log "INFO" "Removing old artifact: $dir (age: $age_days days, retention: $retention_days days)"
      rm -rf "$dir"
    else
      log "INFO" "Keeping artifact: $dir (age: $age_days days, retention: $retention_days days)"
    fi
  done

  # Always clean the tmp directory
  log "INFO" "Cleaning tmp directory"
  rm -rf "$ARTIFACTS_ROOT/tmp"/*
  mkdir -p "$ARTIFACTS_ROOT/tmp"

  log "INFO" "Artifact cleanup complete"
}

# Generate a report of current artifacts and disk usage
report_artifacts() {
  local total_size=0
  local dir_sizes=""
  
  log "INFO" "Generating artifact report..."
  
  echo -e "\n${BOLD}Artifact Report${NC}"
  echo "===================="
  
  # Get sizes of each category
  for dir in "$ARTIFACTS_ROOT"/*; do
    if [ -d "$dir" ] && [[ "$dir" != *".git"* ]]; then
      local dir_name=$(basename "$dir")
      local size=$(du -sh "$dir" | cut -f1)
      local count=$(find "$dir" -type d -mindepth 1 | wc -l | tr -d ' ')
      
      dir_sizes+="$dir_name: $size ($count runs)\n"
      total_size=$(( $total_size + $(du -sk "$dir" | cut -f1) ))
    fi
  done
  
  # Convert to human readable
  if [ $total_size -gt 1048576 ]; then
    total_size_hr="$(echo "scale=2; $total_size/1048576" | bc) GB"
  elif [ $total_size -gt 1024 ]; then
    total_size_hr="$(echo "scale=2; $total_size/1024" | bc) MB"
  else
    total_size_hr="$total_size KB"
  fi
  
  echo -e "Total size: ${BOLD}$total_size_hr${NC}"
  echo -e "Breakdown:"
  echo -e "$dir_sizes"
  
  # List the 5 largest artifact directories
  echo -e "\nLargest artifact directories:"
  find "$ARTIFACTS_ROOT" -type d -mindepth 2 | xargs du -sh 2>/dev/null | sort -hr | head -5
  
  echo ""
}

# Print environment paths and help
print_environment() {
  echo -e "${BOLD}Artifact Environment${NC}"
  echo "===================="
  echo -e "${BLUE}ARTIFACTS_ROOT${NC}=$ARTIFACTS_ROOT"
  
  # Print each artifact type directory
  if [ -f "$ARTIFACTS_ROOT/$CONFIG_FILE" ]; then
    for dir in $(find "$ARTIFACTS_ROOT" -type d -mindepth 1 -maxdepth 1 | sort); do
      local dir_name=$(basename "$dir")
      local var_name="ARTIFACTS_$(echo $dir_name | tr 'a-z' 'A-Z')"
      local description=$(grep -o "\"$dir_name\":[^,}]*" "$ARTIFACTS_ROOT/$CONFIG_FILE" 2>/dev/null | sed "s/\"$dir_name\"://;s/\"//g")
      echo -e "${BLUE}${var_name}${NC}=$dir ${YELLOW}# $description${NC}"
    done
  fi

  echo ""
  echo -e "${BOLD}Source the artifacts.env file in your scripts:${NC}"
  echo 'source ./artifacts.env'
  echo ""
}

# Generate a sourceable environment file for artifacts
generate_env_file() {
  local env_file="$SCRIPT_DIR/artifacts.env"
  
  # Create file header
  cat > "$env_file" << EOF
# Artifact environment variables
# Source this file to get standard artifact paths
# Generated by cleanup.sh on $(date)

export ARTIFACTS_ROOT="$ARTIFACTS_ROOT"
EOF

  # Add each artifact type
  if [ -f "$ARTIFACTS_ROOT/$CONFIG_FILE" ]; then
    for dir in $(find "$ARTIFACTS_ROOT" -type d -mindepth 1 -maxdepth 1 | sort); do
      local dir_name=$(basename "$dir")
      local var_name="ARTIFACTS_$(echo $dir_name | tr 'a-z' 'A-Z')"
      local description=$(grep -o "\"$dir_name\":[^,}]*" "$ARTIFACTS_ROOT/$CONFIG_FILE" 2>/dev/null | sed "s/\"$dir_name\"://;s/\"//g")
      
      # Add export with comment
      echo "export $var_name=\"$dir\" # $description" >> "$env_file"
    done
  fi
  
  # Add helper functions
  cat >> "$env_file" << 'EOF'

# Helper function to get specific artifact directories
get_artifact_path() {
  local type="$1"
  local name="$2"
  
  case "$type" in
    analysis|vision|test|benchmark|json|tmp)
      dir_var="ARTIFACTS_${type^^}"
      dir_path="${!dir_var}/$name"
      mkdir -p "$dir_path"
      echo "$dir_path"
      ;;
    *)
      echo "Unknown artifact type: $type" >&2
      echo "Valid types: analysis, vision, test, benchmark, json, tmp" >&2
      return 1
      ;;
  esac
}

# Clean temporary artifacts
clean_tmp_artifacts() {
  rm -rf "$ARTIFACTS_TMP"/*
  mkdir -p "$ARTIFACTS_TMP"
}
EOF

  echo "Generated environment file: $env_file"
  return 0
}

# Function to check for artifacts outside the standard directory
check_artifact_sprawl() {
  local check_dir="${1:-.}"
  local excluded_dirs="$ARTIFACTS_ROOT"
  
  log "INFO" "Checking for artifact sprawl in $check_dir..."
  
  # Temporary file for results
  local temp_file="/tmp/artifact-sprawl-$$.txt"
  
  # Find timestamp directories (anything under artifacts/)
  find "$check_dir" -type d -path "$check_dir/artifacts/*" -not -path "$excluded_dirs*" > "$temp_file"
  
  # Filter duplicates and report
  if [ -s "$temp_file" ]; then
    sort -u "$temp_file" > "${temp_file}.sorted"
    mv "${temp_file}.sorted" "$temp_file"
    
    echo -e "\n${BOLD}${RED}Artifact Sprawl Detected${NC}"
    echo "======================="
    echo -e "${YELLOW}The following directories outside the canonical artifact structure were found:${NC}"
    cat "$temp_file"
    echo ""
    
    log "WARN" "Artifact sprawl detected: $(wc -l < "$temp_file") directories"
    rm -f "$temp_file"
    return 1
  else
    echo -e "\n${BOLD}${GREEN}No Artifact Sprawl Detected${NC}"
    echo "All artifacts appear to be in the canonical structure."
    log "INFO" "No artifact sprawl detected"
    rm -f "$temp_file"
    return 0
  fi
}


# Show help
show_help() {
  echo -e "${BOLD}Artifact Cleanup Utility${NC}"
  echo "======================="
  echo "Manages artifacts in a centralized location with a simplified structure."
  echo ""
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --path TYPE NAME     Get a path in the artifact directory (creates if needed)"
  echo "  --clean              Remove old artifacts according to retention policy"
  echo "  --clean-tmp          Clean only temporary artifacts directory"
  echo "  --report             Generate a report of current artifacts"
  echo "  --check              Check for artifact sprawl outside canonical structure"
  echo "  --setup              Setup the artifact directory structure"
  echo "  --env                Print environment variables for scripts"
  echo "  --generate-env       Generate artifacts.env file for sourcing in scripts"
  echo "  --help               Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 --path test vision_basic    # Get path for vision test outputs"
  echo "  $0 --clean-tmp                 # Clean temporary artifacts"
  echo "  $0 --generate-env              # Create artifacts.env for sourcing"
  echo ""
}

# Clean only temporary artifacts
clean_tmp() {
  log "INFO" "Cleaning temporary artifacts directory"
  rm -rf "$ARTIFACTS_ROOT/tmp"/*
  mkdir -p "$ARTIFACTS_ROOT/tmp"
  log "INFO" "Temporary artifacts cleaned"
}

# Main processing
cleanup_lock

# Process command-line arguments
if [ $# -eq 0 ]; then
  show_help
  exit 0
fi

# Make sure artifact directory exists
if [ ! -d "$ARTIFACTS_ROOT" ]; then
  setup_artifact_structure
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --clean)
      clean_artifacts
      shift
      ;;
    --clean-tmp)
      clean_tmp
      shift
      ;;
    --report)
      report_artifacts
      shift
      ;;
    --check)
      check_artifact_sprawl
      shift
      ;;
    --path)
      if [ $# -lt 3 ]; then
        echo "Error: --path requires TYPE and NAME parameters"
        exit 1
      fi
      artifact_path=$(get_artifact_path "$2" "$3")
      echo "$artifact_path"
      shift 3
      ;;
    --setup)
      setup_artifact_structure
      shift
      ;;
    --env)
      print_environment
      shift
      ;;
    --generate-env)
      generate_env_file
      shift
      ;;
    --help)
      show_help
      shift
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

exit 0