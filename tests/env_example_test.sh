#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"
# Example test using the artifacts.env approach for simplicity

# Source the artifacts environment 
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/artifacts.env"

# Make sure artifact directories exist
"$SCRIPT_DIR/cleanup.sh" --setup >/dev/null 2>&1

# Create test directories
TEST_DIR=$(get_artifact_path test env_example)
echo "Using test directory: $TEST_DIR"

# Clean directory for fresh start
rm -rf "$TEST_DIR"/*
mkdir -p "$TEST_DIR"

# Create analysis directory
ANALYSIS_DIR=$(get_artifact_path analysis env_example)
echo "Using analysis directory: $ANALYSIS_DIR"

# Clean directory for fresh start
rm -rf "$ANALYSIS_DIR"/*
mkdir -p "$ANALYSIS_DIR"

# Use temporary directory
TMP_DIR=$(get_artifact_path tmp env_example)
echo "Using temporary directory: $TMP_DIR"

# Clean temporary directory (using helper function)
clean_tmp_artifacts

# Create test files 
echo "Creating test files..."
echo "Test data" > "$TEST_DIR/test.txt"
echo '{"result": "success"}' > "$ANALYSIS_DIR/result.json"
echo "Temporary data" > "$TMP_DIR/temp.txt"

# Run a simulated test
echo "Running test..."
sleep 1

# Test completed
echo "Test completed successfully."
echo "Results in:"
echo "- $TEST_DIR"
echo "- $ANALYSIS_DIR"
echo "- $TMP_DIR (temporary artifacts)"

exit 0