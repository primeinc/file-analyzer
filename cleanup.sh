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
ARTIFACTS_ROOT="$SCRIPT_DIR/artifacts"
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
  },
  "legacy_patterns": [
    "analysis_results/",
    "test_output/",
    "test_data/test_results/",
    "fastvlm_test_results_*/"
  ]
}
EOF
  fi

  log "INFO" "Artifact directory structure created at $ARTIFACTS_ROOT"
}

# Get a path in the artifacts directory without excessive timestamps
# Usage: get_artifact_path <type> <name>
# Example: get_artifact_path test vision_basic
get_artifact_path() {
  local type="$1"
  local name="${2:-output}"
  local artifact_path="$ARTIFACTS_ROOT/$type/$name"
  
  mkdir -p "$artifact_path"
  echo "$artifact_path"
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
  local retention_days=$DEFAULT_RETENTION_DAYS
  
  if [ -f "$ARTIFACTS_ROOT/$CONFIG_FILE" ]; then
    retention_days=$(grep -o '"retention_days":[^,}]*' "$ARTIFACTS_ROOT/$CONFIG_FILE" | sed 's/"retention_days"://')
  fi

  log "INFO" "Cleaning artifacts older than $retention_days days..."

  # Find and remove old run directories within artifacts structure
  find "$ARTIFACTS_ROOT" -type d -path "$ARTIFACTS_ROOT/*/*/*" -mtime +$retention_days | while read dir; do
    if [[ "$dir" != *".git"* ]]; then
      log "INFO" "Removing old artifact: $dir"
      rm -rf "$dir"
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

# Search existing legacy artifact directories that need migration
find_legacy_artifacts() {
  local legacy_dirs=()
  
  if [ -f "$ARTIFACTS_ROOT/$CONFIG_FILE" ]; then
    legacy_patterns=$(grep -o '"legacy_patterns":\s*\[[^]]*\]' "$ARTIFACTS_ROOT/$CONFIG_FILE" | 
      sed 's/"legacy_patterns":\s*\[\(.*\)\]/\1/' | 
      sed 's/"//g' | 
      sed 's/,/ /g')
    
    for pattern in $legacy_patterns; do
      # Find directories matching pattern
      if [[ "$pattern" == *"*"* ]]; then
        # For glob patterns
        for dir in $pattern; do
          if [ -d "$dir" ]; then
            legacy_dirs+=("$dir")
          fi
        done
      else
        # For exact directory names
        if [ -d "$pattern" ]; then
          legacy_dirs+=("$pattern")
        fi
      fi
    done
  fi
  
  echo "${legacy_dirs[@]}"
}

# Migrate legacy artifacts to the new structure
migrate_legacy_artifacts() {
  log "INFO" "Checking for legacy artifacts to migrate..."
  
  local legacy_dirs=$(find_legacy_artifacts)
  if [ -z "$legacy_dirs" ]; then
    log "INFO" "No legacy artifacts found"
    return
  fi
  
  for dir in $legacy_dirs; do
    log "INFO" "Migrating legacy artifacts from $dir"
    
    # Determine appropriate destination based on directory name
    local dest="$ARTIFACTS_ROOT/test"
    if [[ "$dir" == *"analysis"* ]]; then
      dest="$ARTIFACTS_ROOT/analysis"
    elif [[ "$dir" == *"vision"* || "$dir" == *"fastvlm"* ]]; then
      dest="$ARTIFACTS_ROOT/vision"
    elif [[ "$dir" == *"json"* ]]; then
      dest="$ARTIFACTS_ROOT/json"
    fi
    
    # Create migration directory with timestamp
    local migration_dir="$dest/migrated_$(date '+%Y%m%d_%H%M%S')"
    mkdir -p "$migration_dir"
    
    # Copy contents to new location
    cp -r "$dir"/* "$migration_dir"/ 2>/dev/null
    
    # Add a migration note
    echo "Migrated from $dir on $(date)" > "$migration_dir/MIGRATION_NOTE.txt"
    
    log "INFO" "Migrated $dir to $migration_dir"
    
    # Optionally remove the original directory after migration
    # Uncomment the following line when you're confident in the migration process
    # rm -rf "$dir"
  done
  
  log "INFO" "Legacy artifact migration complete"
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
    analysis|vision|test|benchmark|tmp)
      dir_var="ARTIFACTS_${type^^}"
      dir_path="${!dir_var}/$name"
      mkdir -p "$dir_path"
      echo "$dir_path"
      ;;
    *)
      echo "Unknown artifact type: $type" >&2
      echo "Valid types: analysis, vision, test, benchmark, tmp" >&2
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

# Function to enforce artifact standards in a directory
# Checks for artifacts outside the standard directory
check_artifact_sprawl() {
  local check_dir="${1:-.}"
  local excluded_dirs="$ARTIFACTS_ROOT"
  
  log "INFO" "Checking for artifact sprawl in $check_dir..."
  
  # Get legacy patterns
  if [ -f "$ARTIFACTS_ROOT/$CONFIG_FILE" ]; then
    legacy_patterns=$(grep -o '"legacy_patterns":\s*\[[^]]*\]' "$ARTIFACTS_ROOT/$CONFIG_FILE" | 
      sed 's/"legacy_patterns":\s*\[\(.*\)\]/\1/' | 
      sed 's/"//g' | 
      sed 's/,/ /g')
  else
    legacy_patterns="analysis_results/ test_output/ test_data/test_results/ fastvlm_test_results_*/"
  fi
  
  # Temporary file for results
  local temp_file="/tmp/artifact-sprawl-$$.txt"
  
  # Find timestamp directories
  find "$check_dir" -type d -path "$check_dir/*" -not -path "$excluded_dirs*" | 
    grep -E '_[0-9]{8}_[0-9]{6}' > "$temp_file"
  
  # Find directories matching legacy patterns
  for pattern in $legacy_patterns; do
    # Convert glob pattern to find pattern
    find_pattern=$(echo "$pattern" | sed 's/\*/.*/g')
    find "$check_dir" -type d -path "$check_dir/*" -not -path "$excluded_dirs*" | 
      grep -E "$find_pattern" >> "$temp_file"
  done
  
  # Filter duplicates and report
  if [ -s "$temp_file" ]; then
    sort -u "$temp_file" > "${temp_file}.sorted"
    mv "${temp_file}.sorted" "$temp_file"
    
    echo -e "\n${BOLD}${RED}Artifact Sprawl Detected${NC}"
    echo "======================="
    echo -e "${YELLOW}The following directories outside the canonical artifact structure were found:${NC}"
    cat "$temp_file"
    echo ""
    echo -e "${BLUE}Recommendation:${NC} Migrate these artifacts to the canonical structure:"
    echo "  ./cleanup.sh --migrate"
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
  echo "Manages the lifecycle of all test artifacts in a canonical location."
  echo ""
  echo "Usage: $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --clean               Clean old artifacts according to retention policy"
  echo "  --migrate             Migrate legacy artifacts to canonical structure"
  echo "  --report              Generate a report of current artifacts"
  echo "  --check               Check for artifact sprawl outside canonical structure"
  echo "  --new-run TYPE NAME   Create a new run directory for a specific type"
  echo "  --setup               Setup the artifact directory structure"
  echo "  --env                 Print environment variables for scripts"
  echo "  --help                Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 --clean            # Clean up old artifacts"
  echo "  $0 --new-run test vision_test    # Create a new test run directory"
  echo "  $0 --report           # Show artifact usage report"
  echo "  $0 --check            # Check for artifacts outside canonical structure"
  echo "  $0 --migrate          # Migrate legacy artifacts to canonical structure"
  echo ""
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
  echo "  --migrate            Migrate legacy artifacts to canonical structure"
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
    --migrate)
      migrate_legacy_artifacts
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