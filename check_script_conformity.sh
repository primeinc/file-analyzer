#!/bin/bash
# check_script_conformity.sh - Validate shell scripts for artifact guard sourcing
# This script enforces the requirement that all shell scripts must source artifact_guard_py_adapter.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD_SCRIPT="artifact_guard_py_adapter.sh"
ALLOWED_UNSOURCED=("$GUARD_SCRIPT" "preflight.sh" "cleanup.sh" "check_script_conformity.sh" "artifacts.env" "artifact_guard_py_adapter.sh")

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Check if a script properly sources artifact_guard_py_adapter.sh
check_script() {
  local script=$1
  local script_name=$(basename "$script")
  
  # Skip scripts that are allowed to not source the guard
  for allowed in "${ALLOWED_UNSOURCED[@]}"; do
    if [[ "$script_name" == "$allowed" ]]; then
      echo -e "${YELLOW}${BOLD}EXEMPT${NC}: $script (exempt from sourcing requirement)"
      return 0
    fi
  done
  
  # Look for any sourcing of artifact_guard.sh or artifact_guard_py_adapter.sh in the script
  if grep -q "source.*artifact_guard.sh" "$script" || grep -q "\. .*artifact_guard.sh" "$script" || grep -q "source.*artifact_guard_py_adapter.sh" "$script"; then
    echo -e "${GREEN}${BOLD}PASS${NC}: $script"
    return 0
  else
    echo -e "${RED}${BOLD}FAIL${NC}: $script (does not source artifact_guard.sh or artifact_guard_py_adapter.sh)"
    return 1
  fi
}

# Find all shell scripts in the project
find_scripts() {
  local count=0
  local failures=0
  
  echo -e "${BOLD}Checking all shell scripts for artifact_guard.sh sourcing:${NC}"
  echo "----------------------------------------"
  
  while IFS= read -r script; do
    check_script "$script"
    if [ $? -ne 0 ]; then
      ((failures++))
    fi
    ((count++))
  done < <(find "$SCRIPT_DIR" -type f -name "*.sh" | sort)
  
  echo "----------------------------------------"
  echo -e "${BOLD}Total scripts checked:${NC} $count"
  echo -e "${BOLD}Conforming scripts:${NC} $((count - failures))"
  echo -e "${BOLD}Non-conforming scripts:${NC} $failures"
  
  if [ $failures -gt 0 ]; then
    echo -e "\n${RED}${BOLD}ERROR:${NC} $failures script(s) do not conform to artifact discipline requirements."
    echo -e "Each script must source artifact_guard.sh immediately after the shebang line."
    echo -e "Example:"
    echo -e "#!/bin/bash"
    echo -e "source \"\$(dirname \"\${BASH_SOURCE[0]}\")/artifact_guard.sh\""
    return 1
  else
    echo -e "\n${GREEN}${BOLD}SUCCESS:${NC} All scripts conform to artifact discipline requirements."
    return 0
  fi
}

# Check for script paths passed as arguments, otherwise check all scripts
if [ $# -gt 0 ]; then
  echo -e "${BOLD}Checking specified scripts for artifact_guard.sh sourcing:${NC}"
  echo "----------------------------------------"
  
  failures=0
  for script in "$@"; do
    if [[ -f "$script" && "$script" == *.sh ]]; then
      check_script "$script"
      if [ $? -ne 0 ]; then
        ((failures++))
      fi
    else
      echo -e "${RED}ERROR:${NC} $script is not a shell script or does not exist."
      ((failures++))
    fi
  done
  
  echo "----------------------------------------"
  if [ $failures -gt 0 ]; then
    echo -e "${RED}${BOLD}ERROR:${NC} $failures script(s) do not conform to artifact discipline requirements."
    exit 1
  else
    echo -e "${GREEN}${BOLD}SUCCESS:${NC} All specified scripts conform to artifact discipline requirements."
    exit 0
  fi
else
  find_scripts
  exit $?
fi