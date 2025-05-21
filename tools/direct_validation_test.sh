#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard.sh"
# Direct test of exit code functionality 

# Create a test directory using canonical artifact path
TEMP_DIR=$(get_canonical_artifact_path test "validation_test")
echo "Test directory: $TEMP_DIR"

# Create an invalid JSON file to force a validation error
echo "NOT VALID JSON" > "$TEMP_DIR/invalid.json"

# Create a test script
cat > "$TEMP_DIR/test_exit.sh" << 'EOF'
#!/bin/bash
test_failures=0
# Test validation
if python -c "import json; json.load(open('invalid.json'))" 2>/dev/null; then
  echo "✓ Valid JSON"
else
  echo "✗ Invalid JSON"
  test_failures=$((test_failures + 1))
fi

# Return exit code based on failures
if [ $test_failures -gt 0 ]; then
  echo "Test failed with $test_failures errors"
  exit 1
else
  echo "All tests passed"
  exit 0
fi
EOF

chmod +x "$TEMP_DIR/test_exit.sh"

# Run the test script and check the exit code
(cd "$TEMP_DIR" && ./test_exit.sh)
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
if [ $EXIT_CODE -eq 1 ]; then
  echo "✓ Script correctly exited with non-zero status on JSON validation failure"
  exit 0
else
  echo "✗ Script did not exit with non-zero status on JSON validation failure"
  exit 1
fi