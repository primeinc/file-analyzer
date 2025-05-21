#!/bin/bash
# Test script to verify path enforcement

# Source the artifact guard
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"

echo "Attempting to create a directory outside the canonical structure..."
mkdir -p test_bad_path 2>&1 || echo "CORRECTLY PREVENTED: Directory creation outside canonical structure"

echo "Attempting to touch a file outside the canonical structure..."
touch bad_file.txt 2>&1 || echo "CORRECTLY PREVENTED: File creation outside canonical structure"

echo "Attempting to copy to a location outside the canonical structure..."
echo "Test" > artifacts/tmp/test.txt
cp artifacts/tmp/test.txt bad_copy.txt 2>&1 || echo "CORRECTLY PREVENTED: Copy to non-canonical location"

# Now test a valid canonical path
echo "Creating files in a canonical location (should work)..."
TEST_DIR=$(get_canonical_artifact_path test "path_enforcement_test")
echo "Using test directory: $TEST_DIR"

echo "Creating a file in the canonical location..."
touch "$TEST_DIR/good_file.txt" && echo "✓ Successfully created file in canonical location"

exit 0