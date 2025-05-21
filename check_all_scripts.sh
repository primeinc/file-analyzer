#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
# Check all scripts in our main project directories

echo "Checking all scripts in src, tools, and tests directories..."
# Create artifact directory for results
RESULTS_DIR=$(get_canonical_artifact_path test "script_check")

# Run check_script_conformity.sh once and use tee to display output while saving to file
echo "Saving detailed results to $RESULTS_DIR/results.txt"
./check_script_conformity.sh ./tools/*.sh ./tests/*.sh ./*.sh | tee "$RESULTS_DIR/results.txt"

# Check if any errors were found (PIPESTATUS captures exit code of command before the pipe)
STATUS=${PIPESTATUS[0]}
if [ $STATUS -eq 0 ]; then
  echo "All critical scripts conform to artifact discipline requirements!"
else
  echo "Some scripts need to be updated."
fi

exit $STATUS