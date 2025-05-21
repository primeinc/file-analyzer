#!/bin/bash
# Artifact Migration Script
# This script migrates legacy artifacts to the canonical structure

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source artifact guard (for get_canonical_artifact_path)
source "$SCRIPT_DIR/artifact_guard.sh"

# Color and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Legacy directory patterns to migrate
LEGACY_DIRS=(
  "analysis_results"
  "test_output"
  "test_data/test_results"
  "fastvlm_test_results_*"
)

# Get confirmation before proceeding
echo -e "${BOLD}Artifact Migration Tool${NC}"
echo "=========================="
echo "This script will migrate legacy artifacts to the canonical structure."
echo
echo -e "${YELLOW}WARNING:${NC} This is a one-way operation and may take a long time."
echo 
echo -n "Do you want to proceed? [y/N] "
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
  echo "Operation cancelled."
  exit 0
fi

# Create migration log
MIGRATION_LOG="$SCRIPT_DIR/artifacts/migration_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/artifacts"
touch "$MIGRATION_LOG"

echo "Migration started at $(date)" | tee -a "$MIGRATION_LOG"
echo "--------------------------------------------" | tee -a "$MIGRATION_LOG"

# Function to migrate a directory
migrate_directory() {
  local source_dir="$1"
  local artifact_type="$2"
  local context="$3"
  
  if [ ! -d "$source_dir" ]; then
    echo "  Skipping: $source_dir doesn't exist" | tee -a "$MIGRATION_LOG"
    return 0
  fi
  
  echo -e "${BLUE}Migrating: $source_dir${NC}" | tee -a "$MIGRATION_LOG"
  
  # Create canonical destination directory
  local dest_dir
  dest_dir=$(get_canonical_artifact_path "$artifact_type" "$context")
  
  echo "  Destination: $dest_dir" | tee -a "$MIGRATION_LOG"
  
  # Copy contents 
  find "$source_dir" -type f -name "*.json" -o -name "*.txt" | while read -r file; do
    local rel_path="${file#$source_dir/}"
    local dest_file="$dest_dir/$rel_path"
    
    # Create destination directory if it doesn't exist
    mkdir -p "$(dirname "$dest_file")"
    
    # Copy the file
    cp "$file" "$dest_file"
    echo "  Copied: $file -> $dest_file" | tee -a "$MIGRATION_LOG"
  done
  
  # Create a migration note
  cat > "$dest_dir/MIGRATION_NOTE.txt" << EOF
This directory contains files migrated from legacy directory:
$source_dir

Migration performed on $(date) by $(whoami)
Original git commit: ${ARTIFACT_GIT_COMMIT}
EOF

  echo -e "${GREEN}✓ Migration complete for: $source_dir${NC}" | tee -a "$MIGRATION_LOG"
  
  # Ask if we should remove the original directory
  echo -n "  Remove original directory? [y/N] "
  read -r remove_response
  if [[ "$remove_response" =~ ^[Yy]$ ]]; then
    rm -rf "$source_dir"
    echo "  Removed original directory: $source_dir" | tee -a "$MIGRATION_LOG"
  fi
  
  return 0
}

# Migrate each legacy directory pattern
TOTAL_DIRS=0
MIGRATED_DIRS=0

for pattern in "${LEGACY_DIRS[@]}"; do
  echo -e "\n${BOLD}Processing pattern: $pattern${NC}" | tee -a "$MIGRATION_LOG"
  
  # Handle glob patterns
  if [[ "$pattern" == *"*"* ]]; then
    for dir in $pattern; do
      if [ -d "$dir" ]; then
        ((TOTAL_DIRS++))
        
        # Try to determine the appropriate artifact type from the directory name
        artifact_type="test"
        if [[ "$dir" == *"fastvlm"* || "$dir" == *"vision"* ]]; then
          artifact_type="vision"
        elif [[ "$dir" == *"json"* ]]; then
          artifact_type="json"
        elif [[ "$dir" == *"analysis"* ]]; then
          artifact_type="analysis"
        fi
        
        # Create context from directory name
        context="migrated_${dir//\//_}"
        
        # Migrate the directory
        migrate_directory "$dir" "$artifact_type" "$context"
        ((MIGRATED_DIRS++))
      fi
    done
  else
    # Handle exact directory names
    if [ -d "$pattern" ]; then
      ((TOTAL_DIRS++))
      
      # Determine the appropriate artifact type
      artifact_type="test"
      if [[ "$pattern" == "analysis_results" ]]; then
        artifact_type="analysis"
      fi
      
      # Migrate the directory
      migrate_directory "$pattern" "$artifact_type" "migrated_${pattern//\//_}"
      ((MIGRATED_DIRS++))
    fi
  fi
done

echo -e "\n${BOLD}Migration Summary${NC}" | tee -a "$MIGRATION_LOG"
echo "--------------------------------------------" | tee -a "$MIGRATION_LOG"
echo "Total directories processed: $TOTAL_DIRS" | tee -a "$MIGRATION_LOG"
echo "Directories migrated: $MIGRATED_DIRS" | tee -a "$MIGRATION_LOG"
echo "Migration log: $MIGRATION_LOG" | tee -a "$MIGRATION_LOG"
echo -e "${GREEN}${BOLD}Migration completed at $(date)${NC}" | tee -a "$MIGRATION_LOG"

# Run cleanup check to verify no legacy directories remain
echo -e "\n${BOLD}Verifying migration${NC}"
"$SCRIPT_DIR/cleanup.sh" --check

exit 0