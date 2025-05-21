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
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo "Performs strict preflight validation of artifact discipline."
      echo ""
      echo "Options:"
      echo "  --no-enforce         Don't fail on artifact sprawl (DISCOURAGED)"
      echo "  --no-tmp-clean       Don't clean the tmp directory"
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
ARTIFACT_GUARD_PYTHON="$SCRIPT_DIR/src/artifact_guard.py"
ARTIFACT_GUARD_ADAPTER="$SCRIPT_DIR/artifact_guard_py_adapter.sh"

# Check if required scripts exist
if [ ! -f "$CLEANUP_SCRIPT" ]; then
  echo -e "${RED}Error: cleanup.sh not found at $CLEANUP_SCRIPT${NC}" >&2
  exit 1
fi

# Use the Python implementation or adapter - the original artifact_guard.sh is deprecated
if [ ! -f "$ARTIFACT_GUARD_PYTHON" ]; then
  echo -e "${RED}Error: artifact_guard.py not found at $ARTIFACT_GUARD_PYTHON${NC}" >&2
  exit 1
fi

if [ ! -f "$ARTIFACT_GUARD_ADAPTER" ]; then
  echo -e "${YELLOW}Warning: artifact_guard_py_adapter.sh not found at $ARTIFACT_GUARD_ADAPTER${NC}" >&2
  echo -e "${YELLOW}You should use the Python implementation directly${NC}" >&2
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

# Search for scripts without artifact_guard_py_adapter.sh sourcing
echo -e "\n${BOLD}Checking scripts for artifact_guard_py_adapter.sh sourcing:${NC}"
SCRIPT_FAILURES=0
# Exclude libs/ directory from script checks as it contains third-party libraries
SCRIPT_FILES=$(find . -name "*.sh" -type f | grep -v "artifact_guard.sh" | grep -v "artifact_guard_py_adapter.sh" | grep -v "cleanup.sh" | grep -v "preflight.sh" | grep -v "./libs/")

for script in $SCRIPT_FILES; do
  EXEMPT=false
  
  # List of scripts exempt from the sourcing requirement
  EXEMPT_SCRIPTS=("./install.sh" "./check_script_conformity.sh" "./check_all_scripts.sh")
  for exempt in "${EXEMPT_SCRIPTS[@]}"; do
    if [ "$script" = "$exempt" ]; then
      EXEMPT=true
      break
    fi
  done
  
  if [ "$EXEMPT" = true ]; then
    echo -e "${YELLOW}${BOLD}EXEMPT${NC}: $(basename "$script") (exempt from sourcing requirement)"
    continue
  fi
  
  echo -e "----------------------------------------"
  
  # Check if script sources artifact_guard_py_adapter.sh
  if ! grep -q "source.*artifact_guard_py_adapter.sh" "$script" && ! grep -q "\. .*artifact_guard_py_adapter.sh" "$script"; then
    echo -e "${RED}✗ ${BOLD}FAIL${NC}: $script does not source artifact_guard_py_adapter.sh"
    ((SCRIPT_FAILURES++))
  else
    echo -e "${GREEN}✓ ${BOLD}PASS${NC}: $script correctly sources artifact_guard_py_adapter.sh"
  fi
  
  echo -e "----------------------------------------"
done

if [ $SCRIPT_FAILURES -eq 0 ]; then
  echo -e "${GREEN}${BOLD}SUCCESS:${NC} All specified scripts conform to artifact discipline requirements."
else
  echo -e "${RED}${BOLD}ERROR:${NC} Found $SCRIPT_FAILURES scripts without artifact_guard_py_adapter.sh sourcing!"
  if [ "$ENFORCE" = true ]; then
    echo -e "${RED}${BOLD}ERROR: Scripts must be updated to use artifact_guard_py_adapter.sh${NC}"
    exit 1
  fi
fi

# Check for artifact sprawl using cleanup.sh
echo -e "\n${BOLD}Checking for artifact sprawl...${NC}"
$CLEANUP_SCRIPT --check

# If enforcing and sprawl detected, exit with error
if [ $? -ne 0 ] && [ "$ENFORCE" = true ]; then
  echo -e "${RED}${BOLD}Error: Artifact sprawl detected.${NC}" >&2
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
echo -e "1. Source ${YELLOW}artifact_guard_py_adapter.sh${NC} or import ${YELLOW}src.artifact_guard${NC}"
echo -e "2. Use ${YELLOW}get_canonical_artifact_path <type> \"context\"${NC} for generating paths"
echo -e "3. Write all files in canonical locations with manifests"
echo -e "4. NOT bypass the artifact guard with manual paths"
echo ""
echo -e "Run ${BOLD}./cleanup.sh --help${NC} for more options."
echo ""

exit 0