#!/bin/bash
# New pattern with enforced artifact discipline
# This script demonstrates the recommended approach for all tests

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run preflight check with full enforcement - fail on violations
"$SCRIPT_DIR/preflight.sh" --allow-legacy-dirs --allow-legacy-scripts

# Source the artifact guard to enforce path discipline
source "$SCRIPT_DIR/artifact_guard.sh"

# Test metadata
TEST_NAME="strict_example"
TEST_DESCRIPTION="Example test using enforced artifact discipline"

# Get a canonical artifact path - automatic unique ID generation
TEST_DIR=$(get_canonical_artifact_path test "$TEST_NAME")
echo "Test output will be written to: $TEST_DIR"

# Create a test file - this is guarded and will fail if not in canonical path
touch "$TEST_DIR/output_data.txt"

# Write some test data - note that redirection isn't guarded, but the path is canonical
echo "Test data with timestamp $(date)" > "$TEST_DIR/output_data.txt"
echo "Another test output" > "$TEST_DIR/additional_output.txt"

# Get an analysis directory with proper enforcement
ANALYSIS_DIR=$(get_canonical_artifact_path analysis "$TEST_NAME")
echo "Analysis results will be written to: $ANALYSIS_DIR"

# Create a JSON result file
cat > "$ANALYSIS_DIR/result.json" << EOF
{
  "test_name": "$TEST_NAME",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "success",
  "metrics": {
    "execution_time": 0.42,
    "memory_usage": "12MB"
  }
}
EOF

# Use a temporary directory for intermediate files
TMP_DIR=$(get_canonical_artifact_path tmp "$TEST_NAME")
echo "Using temporary directory: $TMP_DIR"

# Create a temporary file
echo "Temporary data" > "$TMP_DIR/temp.txt"

# This would fail because it's not in a canonical path:
# mkdir -p non_canonical_dir
# touch not_allowed.txt

# Run a simulated test
echo "Running test..."
sleep 1

# Display test information from the manifest
echo ""
echo "Test manifest:"
cat "$TEST_DIR/manifest.json"

# Test completed
echo ""
echo "Test completed successfully."
echo "All outputs were written to canonical locations with proper discipline."
echo "The following directories contain the results:"
echo "- $TEST_DIR"
echo "- $ANALYSIS_DIR"
echo "- $TMP_DIR (temporary files)"

exit 0