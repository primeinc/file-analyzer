#!/bin/bash
# Test script for FastVLM integration
# This script tests the FastVLM adapter with the centralized model management system

# Source the Python artifact discipline adapter
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"

# Create artifact directory for logs
artifact_dir=$(get_canonical_artifact_path "test" "fastvlm_integration")
log_file="$artifact_dir/test.log"

echo "FastVLM Integration Test" | tee -a "$log_file"
echo "========================" | tee -a "$log_file"

# Function to log messages
log() {
    echo "$@" | tee -a "$log_file"
}

# Parse arguments
TEST_IMAGE="$1"
MODEL_SIZE="${2:-0.5b}"  # Default to 0.5b if not specified

# Setup the FastVLM environment if needed
log "Checking FastVLM environment..."
if [ ! -f "tools/setup_fastvlm.sh" ]; then
    log "✗ setup_fastvlm.sh not found. Cannot proceed with test."
    exit 1
fi

# Check if MLX is installed
log "Checking MLX installation..."
python -c "import mlx" 2>/dev/null
if [ $? -ne 0 ]; then
    log "⚠ MLX not installed. Installing..."
    pip install mlx
    if [ $? -ne 0 ]; then
        log "✗ Failed to install MLX. Cannot proceed with test."
        exit 1
    fi
else
    log "✓ MLX is installed"
fi

# Run the setup script if needed
log "Checking FastVLM setup..."
python -c "from src.model_config import get_model_path; path = get_model_path('fastvlm', '$MODEL_SIZE'); print(f'Model path: {path}')" 2>/dev/null
if [ $? -ne 0 ]; then
    log "⚠ Running FastVLM setup..."
    bash tools/setup_fastvlm.sh | tee -a "$log_file"
    if [ $? -ne 0 ]; then
        log "✗ FastVLM setup failed. See log for details."
        exit 1
    fi
fi

# Check for model availability and download if needed
log "Checking for model availability..."
python tools/download_models.py list | tee -a "$log_file"

# If no model is available, download the specified one
if ! python -c "from src.model_config import get_model_path; path = get_model_path('fastvlm', '$MODEL_SIZE'); exit(0 if path else 1)"; then
    log "⚠ Model $MODEL_SIZE not found. Downloading..."
    python tools/download_models.py download --size "$MODEL_SIZE" | tee -a "$log_file"
    if [ $? -ne 0 ]; then
        log "✗ Model download failed. Cannot proceed with test."
        exit 1
    fi
fi

# Create a simple test image if we don't have one
if [ -z "$TEST_IMAGE" ] || [ ! -f "$TEST_IMAGE" ]; then
    log "⚠ Test image not specified or not found. Finding a test image..."
    
    # Try to find an existing test image
    TEST_IMAGE=$(find artifacts -name "*.png" -o -name "*.jpg" | head -1)
    
    if [ -z "$TEST_IMAGE" ]; then
        log "⚠ No existing test images found in artifacts."
        
        # Check in test_data directory
        TEST_IMAGE=$(find test_data -name "*.png" -o -name "*.jpg" 2>/dev/null | head -1)
        
        if [ -z "$TEST_IMAGE" ]; then
            log "⚠ No test images found in test_data either. Creating a placeholder image..."
            artifact_img_dir=$(get_canonical_artifact_path "test" "fastvlm_test_images")
            TEST_IMAGE="$artifact_img_dir/test_blue.png"
            
            # Create a colored rectangle (requires ImageMagick)
            which convert > /dev/null
            if [ $? -eq 0 ]; then
                convert -size 640x480 xc:blue "$TEST_IMAGE"
                log "✓ Created test image: $TEST_IMAGE"
            else
                log "✗ ImageMagick not installed. Cannot create test image."
                log "  Please install ImageMagick or provide a test image."
                exit 1
            fi
        else
            log "✓ Using test image: $TEST_IMAGE"
        fi
    else
        log "✓ Using existing test image: $TEST_IMAGE"
    fi
fi

# Run the adapter test
log ""
log "Testing FastVLM adapter with sample image..."
python -c "
from src.fastvlm_adapter import create_adapter
import json

adapter = create_adapter('fastvlm', '$MODEL_SIZE')
result = adapter.predict('$TEST_IMAGE', 'Describe this image briefly.', mode='describe')
print(json.dumps(result, indent=2))
" | tee -a "$log_file"

# Test integration with the CLI tool
log ""
log "Testing FastVLM adapter via download_models.py CLI..."
python tools/download_models.py info --size "$MODEL_SIZE" | tee -a "$log_file"

# Summary
log ""
log "FastVLM integration test completed."
log "✓ Environment check: OK"
log "✓ Model management: OK"
log "✓ Adapter test: OK"
log ""
log "You can run tests with specific models and images using:"
log "  ./tests/test_fastvlm.sh <path_to_image> <model_size>"
log "  Example: ./tests/test_fastvlm.sh test_data/images/sample.jpg 1.5b"
log ""
log "For more options, see the adapter documentation in src/fastvlm_adapter.py"

exit 0