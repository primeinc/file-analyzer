#!/bin/bash
# Test script for vision analysis

# Path to the test image
TEST_IMAGE="test_data/images/Layer 3 Merge.png"

# Create a test directory if it doesn't exist
mkdir -p test_dir

echo "Testing vision analyzer..."
echo "NOTE: This is a mock test since dependencies might not be installed"

# Run the vision analyzer directly
echo "Testing standalone vision analyzer with default model..."
./vision_analyzer.py --image "$TEST_IMAGE" --model fastvlm --mode describe

echo "Testing integration with file_analyzer.py..."
./file_analyzer.py --vision --skip-dependency-check --vision-model fastvlm "$TEST_IMAGE"

echo "Test complete!"
echo "Note: For actual testing, install the required dependencies:"
echo "- For FastVLM: pip install mlx mlx-fastvlm"
echo "- For BakLLaVA: llama.cpp with BakLLaVA-1-Q4_K_M.gguf model"
echo "- For Qwen2-VL: pip install mlx-vlm"