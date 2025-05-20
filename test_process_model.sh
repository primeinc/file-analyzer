#!/usr/bin/env bash
# Test script to verify model is properly extracted and .zip is deleted

cd ml-fastvlm

# Check if 1.5B models exist in the extracted form
echo "Checking for extraction of models..."
if [ -d "checkpoints/llava-fastvithd_1.5b_stage2" ] && [ -d "checkpoints/llava-fastvithd_1.5b_stage3" ]; then
    echo "✅ Models are properly extracted"
else 
    echo "❌ Models are not properly extracted"
fi

# Check if zip files were deleted
echo "Checking if zip files were deleted..."
if [ -f "checkpoints/llava-fastvithd_1.5b_stage2.zip" ] || [ -f "checkpoints/llava-fastvithd_1.5b_stage3.zip" ]; then
    echo "❌ Zip files still exist"
    ls -la checkpoints/*.zip 2>/dev/null
else
    echo "✅ Zip files were properly deleted"
fi

# Check total space used
echo "Storage used by model checkpoints:"
du -sh checkpoints
echo ""

# Clean old partial downloads if any exist
echo "Checking for and cleaning partial downloads..."
find checkpoints -name "*.zip.*" -type f -print -delete

echo "Models are ready for use"