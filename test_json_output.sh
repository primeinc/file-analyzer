#!/bin/bash
# Test script for FastVLM JSON output validation

# Set output directory
output_dir="analysis_results/json_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$output_dir"

# Test images from test data
echo "=== Testing FastVLM JSON Output Validation ==="
echo "Output directory: $output_dir"
echo ""

# Just use a direct list of test images
test_images=(
  "test_data/images/Layer 3 Merge.png"
  "test_data/images/Untitled_4x.png"
  "test_data/images/Untitled (27).png"
)
echo "Found ${#test_images[@]} test images:"
for img in "${test_images[@]}"; do
  echo "  - $img"
done
echo ""

# Pick a primary test image for individual tests
primary_test_image="test_data/images/Layer 3 Merge.png"

# Test 1: Basic JSON output with primary image
echo "1. Testing basic JSON output with primary image..."
python fastvlm_json.py --image "$primary_test_image" \
  --output "$output_dir/basic_json_output.json"
echo ""

# Test 2: Custom prompt with primary image
echo "2. Testing with custom prompt for JSON..."
python fastvlm_json.py --image "$primary_test_image" \
  --output "$output_dir/custom_prompt.json" \
  --prompt "Analyze this image and provide a JSON with 'description' and 'tags' fields."
echo ""

# Test 3: Test vision_analyzer integration
echo "3. Testing vision_analyzer integration with JSON format..."
python vision_analyzer.py --image "$primary_test_image" \
  --output "$output_dir/vision_analyzer.json" --format json
echo ""

# Test 4: Batch processing on multiple images
echo "4. Testing batch processing on multiple images..."
mkdir -p "$output_dir/batch"

# Process 3 different images to test variety
for i in {0..2}; do
  if [ $i -lt ${#test_images[@]} ]; then
    echo "  Processing ${test_images[$i]}..."
    
    # Use fastvlm_json.py for robust JSON output
    python fastvlm_json.py --image "${test_images[$i]}" \
      --output "$output_dir/batch/$(basename "${test_images[$i]}").json" \
      --quiet
  fi
done
echo ""

# Test 5: Validate all JSON output files
echo "5. Validating JSON files..."
for json_file in "$output_dir"/*.json "$output_dir"/batch/*.json; do
  if [ -f "$json_file" ]; then
    echo "Validating: $(basename "$json_file")"
    # Try to parse with jq if available
    if command -v jq &> /dev/null; then
      if jq empty "$json_file" 2>/dev/null; then
        echo "  ✓ Valid JSON"
        # Check for required fields
        if jq -e '.description and .tags' "$json_file" > /dev/null 2>&1; then
          echo "  ✓ Has required fields"
        else
          echo "  ✗ Missing required fields"
        fi
      else
        echo "  ✗ Invalid JSON"
      fi
    else
      # Fallback to python
      if python -m json.tool "$json_file" > /dev/null 2>&1; then
        echo "  ✓ Valid JSON"
      else
        echo "  ✗ Invalid JSON"
      fi
    fi
  fi
done

echo ""
echo "=== Test Complete ==="
echo "Results saved to: $output_dir"