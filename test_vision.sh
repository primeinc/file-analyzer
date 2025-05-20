#!/bin/bash
# Vision Model Test Script
# Tests vision analysis capabilities with JSON output

# Set output directory
output_dir="analysis_results/vision_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$output_dir"

# Banner
echo "===================================================="
echo "   Vision Model Analysis Test (JSON Output)          "
echo "===================================================="
echo

# Check if we have any test images
# Specify a known test image to avoid path issues
test_images=("test_data/images/Layer 3 Merge.png")

if [ ${#test_images[@]} -eq 0 ]; then
  echo "Error: No test images found in test_data directory"
  exit 1
fi

echo "Found ${#test_images[@]} test images"
echo

# Test 1: Basic vision analysis with JSON output
echo "Test 1: Basic Vision Analysis with JSON Output"
echo "---------------------------------------------"
echo "Running: ./analyze.sh -V \"${test_images[0]}\" -r \"$output_dir\""
./analyze.sh -V "${test_images[0]}" -r "$output_dir"

# Check result
if [ -f "$output_dir"/vision_analysis_*.json ]; then
  vision_file=$(ls -t "$output_dir"/vision_analysis_*.json | head -1)
  echo "✓ Generated JSON output: $(basename "$vision_file")"
  
  # Validate JSON
  if python -c "import json; json.load(open('$vision_file'))" 2>/dev/null; then
    echo "✓ Valid JSON format"
    
    # Check structure
    if python -c "import json; data=json.load(open('$vision_file')); keys=list(data.values())[0].keys(); assert 'description' in keys and 'tags' in keys and 'metadata' in keys" 2>/dev/null; then
      echo "✓ Correct JSON structure with description, tags, and metadata"
    else
      echo "✗ Incorrect JSON structure"
    fi
  else
    echo "✗ Invalid JSON format"
  fi
else
  echo "✗ No JSON output file generated"
fi
echo

# Test 2: Different vision modes
echo "Test 2: Vision Analysis Modes"
echo "---------------------------"

# Try different modes (always using the first test image)
if [ ${#test_images[@]} -gt 0 ]; then
  # Document mode
  echo "Running document mode: ./analyze.sh -V --vision-mode document \"${test_images[0]}\""
  ./analyze.sh -V --vision-mode document "${test_images[0]}" -r "$output_dir/document"
  
  # Check result
  if [ -f "$output_dir"/document/vision_analysis_*.json ]; then
    vision_file=$(ls -t "$output_dir"/document/vision_analysis_*.json | head -1)
    echo "✓ Generated JSON output for document mode: $(basename "$vision_file")"
  else
    echo "✗ No JSON output file generated for document mode"
  fi
fi
echo

# Test 3: Performance metrics
echo "Test 3: Performance Metrics"
echo "-------------------------"
metrics_file=$(ls -t "$output_dir"/vision_metrics_*.json 2>/dev/null | head -1)

if [ -n "$metrics_file" ]; then
  echo "✓ Generated performance metrics: $(basename "$metrics_file")"
  
  # Extract metrics
  python -c "
import json
with open('$metrics_file') as f:
    data = json.load(f)
print(f'Model: {data.get(\"model\", \"Unknown\")}')
print(f'Images processed: {data.get(\"images_processed\", 0)}')
print(f'Average time per image: {data.get(\"average_time\", 0):.2f}s')
"
else
  echo "✗ No performance metrics file generated"
fi

echo
echo "Test Complete! Results saved to $output_dir"