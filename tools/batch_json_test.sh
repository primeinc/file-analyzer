#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard.sh"
# Test script for batch JSON output validation

# Set output directory
OUTPUT_DIR=$(get_canonical_artifact_path analysis "batch_json_test")
echo "Output directory: $OUTPUT_DIR"

# Process all images in test_data/images directory
echo "=== Testing Batch JSON Output with Vision Analyzer ==="

# Run batch analysis
python ../src/vision.py --image "../test_data/images" --batch --output "$OUTPUT_DIR/batch_results" --format json

# Validate the JSON output
echo -e "\nValidating JSON files in $OUTPUT_DIR/batch_results..."
for json_file in "$OUTPUT_DIR/batch_results"/*.json; do
  if [ -f "$json_file" ]; then
    echo "Validating: $(basename "$json_file")"
    # Try to parse with Python's json module
    if python -c "import json; json.load(open('$json_file'))" 2>/dev/null; then
      echo "  ✓ Valid JSON"
    else
      echo "  ✗ Invalid JSON"
    fi
  fi
done

# Now try with analyze.sh
echo -e "\n=== Testing Batch JSON Output with analyze.sh ==="
./analyze.sh -V --vision-model fastvlm --vision-mode describe "../test_data/images"

# Create analysis artifact directory
ANALYSIS_DIR=$(get_canonical_artifact_path analysis "vision_analysis")

# Check the latest output file from artifacts dir
latest_file=$(find $ARTIFACTS_ROOT/analysis -type f -name "vision_analysis_*.json" | sort -r | head -1)
echo -e "\nChecking latest output file: $latest_file"

# Copy to our artifact directory for reference
cp "$latest_file" "$ANALYSIS_DIR/"

# Validate the JSON
if python -c "import json; json.load(open('$latest_file'))" 2>/dev/null; then
  echo "  ✓ Valid JSON"
  
  # Count the number of images analyzed
  image_count=$(python -c "import json; data=json.load(open('$latest_file')); print(len(data))")
  echo "  ✓ $image_count images successfully analyzed"
else
  echo "  ✗ Invalid JSON"
fi

echo -e "\n=== Test Complete ==="