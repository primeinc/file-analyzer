#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard.sh"
# Test the exit code functionality with forced error

# Create an artifact directory for test results
TEST_DIR=$(get_canonical_artifact_path test "exit_codes_forced_test")

# Create a temporary directory with no images
TMP_DIR=$(get_canonical_artifact_path tmp "empty_dir_test")

# Run test with the empty directory which should fail
../tools/vision_test.sh "$TMP_DIR" > "$TEST_DIR/output.log" 2>&1
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE" | tee -a "$TEST_DIR/results.txt"

if [ $EXIT_CODE -eq 1 ]; then
  echo "✓ vision_test.sh correctly exited with non-zero status on failure" | tee -a "$TEST_DIR/results.txt"
  exit 0
else
  echo "✗ vision_test.sh did not exit with non-zero status on failure" | tee -a "$TEST_DIR/results.txt"
  exit 1
fi