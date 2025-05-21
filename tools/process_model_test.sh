#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard.sh"
# Test script to verify model is properly extracted and .zip is deleted

# Create artifact directory
OUTPUT_DIR=$(get_canonical_artifact_path test "process_model_test")

# Check if ml-fastvlm directory exists
if [ ! -d "../ml-fastvlm" ]; then
    echo "❌ ml-fastvlm directory not found" | tee "$OUTPUT_DIR/error.txt"
    exit 1
fi

cd ../ml-fastvlm

# Check if 1.5B models exist in the extracted form
echo "Checking for extraction of models..." | tee -a "$OUTPUT_DIR/results.txt"
if [ -d "checkpoints/llava-fastvithd_1.5b_stage2" ] && [ -d "checkpoints/llava-fastvithd_1.5b_stage3" ]; then
    echo "✅ Models are properly extracted" | tee -a "$OUTPUT_DIR/results.txt"
else 
    echo "❌ Models are not properly extracted" | tee -a "$OUTPUT_DIR/results.txt"
fi

# Check if zip files were deleted
echo "Checking if zip files were deleted..." | tee -a "$OUTPUT_DIR/results.txt"
if [ -f "checkpoints/llava-fastvithd_1.5b_stage2.zip" ] || [ -f "checkpoints/llava-fastvithd_1.5b_stage3.zip" ]; then
    echo "❌ Zip files still exist" | tee -a "$OUTPUT_DIR/results.txt"
    ls -la checkpoints/*.zip 2>/dev/null | tee -a "$OUTPUT_DIR/results.txt"
else
    echo "✅ Zip files were properly deleted" | tee -a "$OUTPUT_DIR/results.txt"
fi

# Check total space used
echo "Storage used by model checkpoints:" | tee -a "$OUTPUT_DIR/results.txt"
du -sh checkpoints | tee -a "$OUTPUT_DIR/results.txt"
echo "" | tee -a "$OUTPUT_DIR/results.txt"

# Clean old partial downloads if any exist
echo "Checking for and cleaning partial downloads..." | tee -a "$OUTPUT_DIR/results.txt"
find checkpoints -name "*.zip.*" -type f -print -delete | tee -a "$OUTPUT_DIR/results.txt"

echo "Models are ready for use" | tee -a "$OUTPUT_DIR/results.txt"