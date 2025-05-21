#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
# Check all scripts in our main project directories

echo "Checking all scripts in src, tools, and tests directories..."
./check_script_conformity.sh ./tools/*.sh ./tests/*.sh ./*.sh

# Check if any errors were found
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo "All critical scripts conform to artifact discipline requirements!"
else
  echo "Some scripts need to be updated."
fi

# Create artifact directory for results
RESULTS_DIR=$(get_canonical_artifact_path test "script_check")

# Save the results
echo "Saving detailed results to $RESULTS_DIR/results.txt"
./check_script_conformity.sh ./tools/*.sh ./tests/*.sh ./*.sh > "$RESULTS_DIR/results.txt" 2>&1

exit $STATUS