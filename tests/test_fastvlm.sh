#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard.sh"
# Test script for FastVLM integration

echo "FastVLM Integration Test"
echo "========================"

# Check if ML framework is installed
echo "Checking MLX installation..."
python -c "import mlx" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "MLX not installed. Installing..."
    pip install mlx
else
    echo "MLX is installed"
fi

# Check if ml-fastvlm repository exists
if [ ! -d "ml-fastvlm" ]; then
    echo "ml-fastvlm repository not found. Cloning..."
    git clone https://github.com/apple/ml-fastvlm.git
    cd ml-fastvlm && pip install -e .
    cd ..
else
    echo "ml-fastvlm repository found"
fi

# Check if the model weights directory exists
if [ ! -d "ml-fastvlm/checkpoints" ]; then
    echo "Creating checkpoints directory..."
    mkdir -p ml-fastvlm/checkpoints
fi

# Check if we have model files
ls ml-fastvlm/checkpoints/*fastvlm* 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Model files not found."
    echo "Note: You will need to download the model weights later using:"
    echo "cd ml-fastvlm && bash get_models.sh"
    echo ""
    echo "For now, we will test using a placeholder model."
else
    echo "Model weights found"
fi

# Create a simple test image if we don't have one
TEST_IMAGE="test_data/images/Layer 3 Merge.png"
if [ ! -f "$TEST_IMAGE" ]; then
    echo "Test image not found. Using a different test image..."
    # Find any image in the test directory
    TEST_IMAGE=$(find test_data -name "*.png" -o -name "*.jpg" | head -1)
    
    if [ -z "$TEST_IMAGE" ]; then
        echo "No test images found. Creating a placeholder image..."
        mkdir -p test_data/images
        # Create a colored rectangle (requires ImageMagick)
        which convert > /dev/null
        if [ $? -eq 0 ]; then
            convert -size 640x480 xc:blue test_data/images/test_blue.png
            TEST_IMAGE="test_data/images/test_blue.png"
            echo "Created test image: $TEST_IMAGE"
        else
            echo "ImageMagick not installed. Cannot create test image."
            echo "Please install ImageMagick or provide a test image."
            exit 1
        fi
    else
        echo "Using test image: $TEST_IMAGE"
    fi
fi

# Run the FastVLM test script
echo ""
echo "Testing FastVLM with sample image..."
./fastvlm_test.py --image "$TEST_IMAGE" --prompt "Describe this image in detail"

echo ""
echo "Testing integration with file_analyzer.py..."
./file_analyzer.py --vision --vision-model fastvlm --skip-dependency-check "$TEST_IMAGE"

echo ""
echo "FastVLM testing complete. Next steps:"
echo "1. Download model weights: cd ml-fastvlm && bash get_models.sh"
echo "2. Run with actual model: ./fastvlm_test.py --image test_data/images/Layer\ 3\ Merge.png --model ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3"
echo ""
echo "For detailed instructions, see the FastVLM documentation."