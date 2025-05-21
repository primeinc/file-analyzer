#!/bin/bash
# Preflight check with strict enforcement of artifact discipline
# This script validates the repository state before test execution:
# 1. Enforces canonical artifact structure 
# 2. Detects and reports rogue artifacts outside canonical paths
# 3. Enforces clean state requirements
# 4. FAILS BUILD if artifact discipline is violated

# Default options - ENFORCE IS NOW TRUE BY DEFAULT
ENFORCE=true
CLEAN_TMP=true
FAIL_ON_LEGACY_DIRS=true
FAIL_ON_LEGACY_SCRIPTS=true

# Process command-line arguments
while [ $# -gt 0 ]; do
  case "$1" in
    --no-enforce)
      ENFORCE=false
      shift
      ;;
    --no-tmp-clean)
      CLEAN_TMP=false
      shift
      ;;
    --allow-legacy-dirs)
      FAIL_ON_LEGACY_DIRS=false
      shift
      ;;
    --allow-legacy-scripts)
      FAIL_ON_LEGACY_SCRIPTS=false
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo "Performs strict preflight validation of artifact discipline."
      echo ""
      echo "Options:"
      echo "  --no-enforce         Don't fail on artifact sprawl (DISCOURAGED)"
      echo "  --no-tmp-clean       Don't clean the tmp directory"
      echo "  --allow-legacy-dirs  Don't fail on legacy directories (TEMPORARY)"
      echo "  --allow-legacy-scripts Don't fail on scripts with legacy paths (TEMPORARY)" 
      echo "  --help               Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Color and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS_ROOT="$SCRIPT_DIR/artifacts"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup.sh"
ARTIFACT_GUARD="$SCRIPT_DIR/artifact_guard.sh"

# Check if required scripts exist
if [ ! -f "$CLEANUP_SCRIPT" ]; then
  echo -e "${RED}Error: cleanup.sh not found at $CLEANUP_SCRIPT${NC}" >&2
  exit 1
fi

if [ ! -f "$ARTIFACT_GUARD" ]; then
  echo -e "${RED}Error: artifact_guard.sh not found at $ARTIFACT_GUARD${NC}" >&2
  exit 1
fi

# Ensure artifact directory structure exists
if [ ! -d "$ARTIFACTS_ROOT" ]; then
  echo -e "${YELLOW}Creating artifact directory structure...${NC}"
  $CLEANUP_SCRIPT --setup
fi

# Always clean the tmp directory for a fresh start
if [ "$CLEAN_TMP" = true ]; then
  echo -e "${YELLOW}Cleaning temporary artifact directory...${NC}"
  rm -rf "$ARTIFACTS_ROOT/tmp"/*
  mkdir -p "$ARTIFACTS_ROOT/tmp"
fi

# Validation failures counter
FAILURES=0

# Find known legacy directories
echo -e "\n${BOLD}Checking for legacy artifact directories...${NC}"
LEGACY_DIRS=(
  "analysis_results"
  "test_output"
  "test_data/test_results"
  "fastvlm_test_results_*"
  "vision_test_*"
  "json_test_*"
)

for pattern in "${LEGACY_DIRS[@]}"; do
  # Use find for exact directories and shell expansion for patterns with globs
  if [[ "$pattern" == *"*"* ]]; then
    # Pattern with glob, use shell expansion
    for dir in $pattern; do
      if [ -d "$dir" ]; then
        echo -e "${RED}✗ Legacy directory detected: $dir${NC}"
        ((FAILURES++))
      fi
    done
  else
    # Exact directory, use find
    if [ -d "$pattern" ]; then
      echo -e "${RED}✗ Legacy directory detected: $pattern${NC}"
      ((FAILURES++))
    fi
  fi
done

if [ $FAILURES -eq 0 ]; then
  echo -e "${GREEN}✓ No legacy directories found${NC}"
else
  echo -e "${RED}${BOLD}Found $FAILURES legacy directories!${NC}"
  if [ "$FAIL_ON_LEGACY_DIRS" = true ] && [ "$ENFORCE" = true ]; then
    echo -e "${RED}${BOLD}ERROR: Legacy directories must be migrated. Run ./cleanup.sh --migrate${NC}"
    exit 1
  fi
fi

# Search for non-canonical artifact paths in scripts
echo -e "\n${BOLD}Checking scripts for non-canonical artifact paths...${NC}"
SCRIPT_FAILURES=0
# Exclude ml-fastvlm from script checks as it's a third-party library
SCRIPT_FILES=$(find . -name "*.sh" -type f | grep -v "artifact_guard.sh" | grep -v "artifact_guard_py_adapter.sh" | grep -v "cleanup.sh" | grep -v "preflight.sh" | grep -v "./ml-fastvlm/")

LEGACY_PATTERNS=(
  "analysis_results"
  "test_output"
  "test_data/test_results"
  "fastvlm_test_results_"
  "mkdir -p.*_\$(date"
  "output_dir=.*\$(date"
  "OUTPUT_DIR=.*\$(date"
)

for script in $SCRIPT_FILES; do
  VIOLATIONS=0
  echo -e "${BLUE}Checking $script...${NC}"
  
  for pattern in "${LEGACY_PATTERNS[@]}"; do
    if grep -q "$pattern" "$script"; then
      echo -e "  ${RED}✗ Contains pattern: $pattern${NC}"
      ((VIOLATIONS++))
    fi
  done
  
  # Check if script sources artifact_guard.sh
  if ! grep -q "source.*artifact_guard.sh" "$script" && ! grep -q "\. .*artifact_guard.sh" "$script"; then
    echo -e "  ${YELLOW}⚠ Does not source artifact_guard.sh${NC}"
    ((VIOLATIONS++))
  fi
  
  if [ $VIOLATIONS -gt 0 ]; then
    echo -e "  ${RED}$script has $VIOLATIONS violations${NC}"
    ((SCRIPT_FAILURES++))
  else
    echo -e "  ${GREEN}✓ No violations${NC}"
  fi
done

if [ $SCRIPT_FAILURES -eq 0 ]; then
  echo -e "${GREEN}✓ All scripts use canonical artifact paths${NC}"
else
  echo -e "${RED}${BOLD}Found $SCRIPT_FAILURES scripts with non-canonical artifact paths!${NC}"
  if [ "$FAIL_ON_LEGACY_SCRIPTS" = true ] && [ "$ENFORCE" = true ]; then
    echo -e "${RED}${BOLD}ERROR: Scripts must be updated to use artifact_guard.sh${NC}"
    exit 1
  fi
fi

# Check for artifact sprawl using cleanup.sh
echo -e "\n${BOLD}Checking for artifact sprawl...${NC}"
$CLEANUP_SCRIPT --check

# If enforcing and sprawl detected, exit with error
if [ $? -ne 0 ] && [ "$ENFORCE" = true ]; then
  echo -e "${RED}${BOLD}Error: Artifact sprawl detected. Run ./cleanup.sh --migrate to fix.${NC}" >&2
  exit 1
fi

# Check presence of artifact.env and make sure all required scripts update it
if [ ! -f "$SCRIPT_DIR/artifacts.env" ]; then
  echo -e "${YELLOW}Generating artifacts.env file...${NC}"
  $CLEANUP_SCRIPT --generate-env
else
  echo -e "${GREEN}✓ artifacts.env file exists${NC}"
fi

# Success message
echo -e "\n${GREEN}${BOLD}Preflight check completed successfully.${NC}"
echo -e "${BOLD}IMPORTANT:${NC} All scripts must:"
echo -e "1. Source ${YELLOW}artifact_guard.sh${NC} for path enforcement"
echo -e "2. Use ${YELLOW}get_canonical_artifact_path <type> \"context\"${NC} for generating paths"
echo -e "3. Write all files in canonical locations with manifests"
echo -e "4. NOT bypass the artifact guard with manual paths"
echo ""
echo -e "Run ${BOLD}./cleanup.sh --help${NC} for more options."
echo ""

exit 0