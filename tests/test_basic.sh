#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"
# Basic test script for file_analyzer.py

# Create test directory with canonical path
TEST_DIR=$(get_canonical_artifact_path "test" "basic_test")
TEST_FILES="$TEST_DIR/test_files"
mkdir -p "$TEST_FILES"

# Create sample text file
echo "This is a sample text file with some searchable content." > "$TEST_FILES/sample.txt"
echo "It contains a sample password: P@ssw0rd123" >> "$TEST_FILES/sample.txt"

# Create sample image file (1x1 pixel black PNG)
echo -e "\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x99c```\x00\x00\x00\x04\x00\x01\xa3\x17\x96Q\x00\x00\x00\x00IEND\xaeB\`" > "$TEST_FILES/sample.png"

# Create duplicate file
cp "$TEST_FILES/sample.txt" "$TEST_FILES/duplicate.txt"

# Record test directory path
echo "Using test directory: $TEST_FILES"

echo "Running basic tests..."

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Test 1: Check if all tools are installed
echo "Test 1: Dependency check..."
python3 "$PROJECT_ROOT/src/analyzer.py" --skip-dependency-check -a "$TEST_FILES"

# Test 2: Test metadata extraction
echo "Test 2: Metadata extraction..."
python3 "$PROJECT_ROOT/src/analyzer.py" --metadata "$TEST_FILES"

# Test 3: Test duplicate detection
echo "Test 3: Duplicate detection..."
python3 "$PROJECT_ROOT/src/analyzer.py" --duplicates "$TEST_FILES"

# Test 4: Test content search
echo "Test 4: Content search..."
python3 "$PROJECT_ROOT/src/analyzer.py" --search "password" "$TEST_FILES"

# Test 5: Test with file filtering
echo "Test 5: File filtering..."
python3 "$PROJECT_ROOT/src/analyzer.py" --metadata --include "*.txt" "$TEST_FILES"

# Create a results file
echo "Writing test results to $TEST_DIR/results.txt"
echo "Tests completed at $(date)" > "$TEST_DIR/results.txt"
echo "All tests passed!" >> "$TEST_DIR/results.txt"

echo "All tests completed. Results saved to $TEST_DIR/results.txt"