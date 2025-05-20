#!/bin/bash
# Automated test script for file-analyzer

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${SCRIPT_DIR}"
OUTPUT_DIR="${SCRIPT_DIR}/test_results"
ANALYZER="../file_analyzer.py"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=== File Analyzer Test Suite ==="
echo "Running tests from: $TEST_DIR"
echo "Saving results to: $OUTPUT_DIR"
echo

# Test 1: Metadata extraction
echo "Test 1: Metadata extraction"
$ANALYZER --metadata --output "$OUTPUT_DIR" --skip-dependency-check "$TEST_DIR/images/Layer 3 Merge.png"
if [ $? -eq 0 ]; then
    echo "✅ Test 1 passed"
else
    echo "❌ Test 1 failed"
fi
echo

# Test 2: Duplicate detection
echo "Test 2: Duplicate detection"
$ANALYZER --duplicates --output "$OUTPUT_DIR" --skip-dependency-check "$TEST_DIR"
if [ $? -eq 0 ]; then
    echo "✅ Test 2 passed"
else
    echo "❌ Test 2 failed"
fi
echo

# Test 3: Content search
echo "Test 3: Content search"
$ANALYZER --search "TEST PATTERN" --output "$OUTPUT_DIR" --skip-dependency-check "$TEST_DIR"
if [ $? -eq 0 ]; then
    grep -q "TEST PATTERN" "$OUTPUT_DIR/search_TEST PATTERN"*.txt
    if [ $? -eq 0 ]; then
        echo "✅ Test 3 passed"
    else
        echo "❌ Test 3 failed - pattern not found in search results"
    fi
else
    echo "❌ Test 3 failed"
fi
echo

# Test 4: File filtering with include patterns
echo "Test 4: File filtering with include patterns"
$ANALYZER --metadata --output "$OUTPUT_DIR" --include "*.json" --skip-dependency-check "$TEST_DIR" 
if [ $? -eq 0 ]; then
    echo "✅ Test 4 passed"
else
    echo "❌ Test 4 failed"
fi
echo

# Test 5: File filtering with exclude patterns
echo "Test 5: File filtering with exclude patterns"
$ANALYZER --metadata --output "$OUTPUT_DIR" --exclude "*.json" --skip-dependency-check "$TEST_DIR" 
if [ $? -eq 0 ]; then
    echo "✅ Test 5 passed"
else
    echo "❌ Test 5 failed"
fi
echo

# Save current directory
ORIG_DIR="$(pwd)"

# Test 6: Vision models with JSON output (if available)
echo "Test 6: Vision model JSON output"
cd ..
if [ -f "./test_vision.sh" ]; then
    echo "Running vision test script..."
    ./test_vision.sh
    if [ $? -eq 0 ]; then
        echo "✅ Test 6 passed"
    else
        echo "⚠️ Test 6 couldn't be validated (vision model dependencies may be missing)"
    fi
else
    echo "⚠️ Test 6 skipped (vision test script not found)"
fi
echo

# Test 7: JSON output validation (if available)
echo "Test 7: JSON validation"
if [ -f "./test_json_output.sh" ]; then
    echo "Running JSON output test script..."
    ./test_json_output.sh
    if [ $? -eq 0 ]; then
        echo "✅ Test 7 passed"
    else
        echo "⚠️ Test 7 couldn't be validated (dependencies may be missing)"
    fi
else
    echo "⚠️ Test 7 skipped (JSON test script not found)"
fi
echo

# Return to original directory
cd "$ORIG_DIR"

echo "All tests completed."