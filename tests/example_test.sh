#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard.sh"
# Example test script using canonical artifact structure
# This demonstrates how to properly create and manage test artifacts.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run preflight check to ensure artifact structure is ready
echo "Running preflight check..."
$SCRIPT_DIR/preflight.sh --enforce

# Exit if preflight fails
if [ $? -ne 0 ]; then
  echo "Preflight check failed. Please fix issues before running tests."
  exit 1
fi

# Get canonical test directory
echo "Getting test directory..."
TEST_DIR=$($SCRIPT_DIR/cleanup.sh --path test example_results)

# Clean directory to start fresh
rm -rf "$TEST_DIR"/*
mkdir -p "$TEST_DIR"

echo "Test results will be saved to: $TEST_DIR"

# Run some example tests and save results to the canonical location
echo "Running tests..."
echo "This is test output" > "$TEST_DIR/output.txt"
echo "This is test result" > "$TEST_DIR/test_result.txt"

# Create subdirectories if needed for complex tests
mkdir -p "$TEST_DIR/subtest1"
echo "Subtest result" > "$TEST_DIR/subtest1/subtest_result.txt"

# Example for creating an analysis result
ANALYSIS_DIR=$($SCRIPT_DIR/cleanup.sh --path analysis example_results)

# Clean directory to start fresh
rm -rf "$ANALYSIS_DIR"/*
mkdir -p "$ANALYSIS_DIR"

echo "Analysis results will be saved to: $ANALYSIS_DIR"
echo '{"result": "example analysis", "status": "success"}' > "$ANALYSIS_DIR/analysis.json"

# Example for temporary artifacts that can be deleted after test
TMP_DIR=$($SCRIPT_DIR/cleanup.sh --path tmp example_tmp)
echo "Using temporary directory: $TMP_DIR"
echo "Temporary content" > "$TMP_DIR/temp_data.txt"

# Run your actual test commands here...
echo "Running actual test..."
sleep 1  # Placeholder for actual test

# Report test result
echo "Test completed successfully!"
echo "Results saved to: $TEST_DIR and $ANALYSIS_DIR"

exit 0