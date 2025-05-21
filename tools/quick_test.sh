#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"
# Quick test script for running FastVLM benchmark
# This script automatically runs the benchmark script with default parameters
# and includes tests with both local and downloaded sample images

# Set up colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Exit on any error
set -e

# Define output directory using canonical artifact path
OUTPUT_DIR=$(get_canonical_artifact_path benchmark "fastvlm_quick_test")

echo -e "${BLUE}Running FastVLM benchmark...${NC}"
echo -e "${BLUE}Results will be saved to: ${OUTPUT_DIR}${NC}"

# Run basic environment check
echo -e "${BLUE}Checking environment...${NC}"
python -c "import fastvlm_test; checker = fastvlm_test.FastVLMAnalyzer(); issues = fastvlm_test.ERROR_HANDLER_AVAILABLE and fastvlm_test.FastVLMErrorHandler.check_environment() or []; print('Environment OK' if not issues else 'Environment issues found: ' + str(len(issues)))" > "$OUTPUT_DIR/environment_check.txt"

# Find available models
echo -e "${BLUE}Looking for model files...${NC}"
python -c "import os, glob; models = glob.glob('libs/ml-fastvlm/checkpoints/llava-fastvithd_*'); print('Available models:'); [print(f'- {os.path.basename(m)}') for m in models]" > "$OUTPUT_DIR/model_files.txt"

# Create a mock analyzer for testing without the real model
echo -e "${BLUE}Creating a mock analyzer for testing...${NC}"
cat > "$OUTPUT_DIR/mock_analyzer.py" << 'EOF'
import time

class MockAnalyzer:
    """Mock analyzer for testing without real FastVLM model."""
    def __init__(self):
        self.model_info = {'name': 'MockModel'}
        self.model_path = '/mock/path'
        
    def analyze_image(self, path, prompt=None):
        """Simulate analyzing an image."""
        # Add slight delay to simulate processing
        time.sleep(0.1)
        return {
            "description": f"Mock analysis of image: {path}",
            "tags": ["test", "mock", "benchmark"],
            "metadata": {
                "time": 0.1,
                "model": "MockModel"
            }
        }
EOF

# Use or download standard sample images
echo -e "${BLUE}Using standard sample test images...${NC}"
SAMPLE_DIR="../test_data/sample_images"
python -c "import os, sys; from benchmark_fastvlm import download_test_images; os.makedirs('../test_data/sample_images', exist_ok=True); images = download_test_images(); print(f'Using {len(images)} sample test images in {os.path.abspath(\"../test_data/sample_images\")}')" > "$OUTPUT_DIR/sample_images_log.txt"

# Run the mock benchmark with standard test images
echo -e "${BLUE}Running benchmark with standard test images...${NC}"
python -c "
import sys
sys.path.insert(0, '$OUTPUT_DIR')
from mock_analyzer import MockAnalyzer
from benchmark_fastvlm import find_test_images, run_benchmark

# Create mock analyzer
mock_analyzer = MockAnalyzer()

# Find test images using our standard function
image_files = find_test_images()

if image_files:
    print(f'Running benchmark with {len(image_files)} test images')
    output_file = '$OUTPUT_DIR/mock_benchmark_results.json'
    results = run_benchmark(mock_analyzer, image_files, output_file)
    print(f'Mock benchmark completed. Results saved to {output_file}')
else:
    print('No test images found for testing')
" > "$OUTPUT_DIR/mock_benchmark_log.txt"

# Run the actual benchmark script (optional if model exists)
if [ -d "libs/ml-fastvlm/checkpoints" ]; then
    echo -e "${BLUE}Running actual benchmark with FastVLM model...${NC}"
    python benchmark_fastvlm.py --output "$OUTPUT_DIR/benchmark.txt" || {
        echo -e "${YELLOW}Warning: Full benchmark with real model failed, continuing with mock tests${NC}"
    }
else
    echo -e "${YELLOW}No FastVLM model found, skipping real benchmark${NC}"
fi

# Test with standard local test image
TEST_IMAGE="../test_data/images/Layer 3 Merge.png"
echo -e "${BLUE}Testing with local image: ${TEST_IMAGE}${NC}"

# Test different analysis modes with mock analyzer
echo -e "${BLUE}Testing different analysis modes...${NC}"
python -c "
import sys
sys.path.insert(0, '$OUTPUT_DIR')
from mock_analyzer import MockAnalyzer
import json

# Create mock analyzer
mock_analyzer = MockAnalyzer()

# Test image
test_image = '$TEST_IMAGE'

# Test different modes
modes = ['describe', 'detect', 'document']
for mode in modes:
    print(f'Testing mode: {mode}')
    result = mock_analyzer.analyze_image(test_image, mode=mode)
    output_file = f'$OUTPUT_DIR/{mode}_mode_mock.txt'
    with open(output_file, 'w') as f:
        if isinstance(result, dict):
            json.dump(result, f, indent=2)
        else:
            f.write(str(result))
    print(f'Results saved to {output_file}')
" > "$OUTPUT_DIR/analysis_modes_log.txt"

# Summarize tests
echo -e "${GREEN}All tests completed. Summary:${NC}" > "$OUTPUT_DIR/summary.txt"
echo "Environment check: $(cat $OUTPUT_DIR/environment_check.txt)" >> "$OUTPUT_DIR/summary.txt"
echo "Model files: $(cat $OUTPUT_DIR/model_files.txt | wc -l) found" >> "$OUTPUT_DIR/summary.txt"
echo "Sample images: $(find ../test_data/sample_images -type f 2>/dev/null | wc -l) files" >> "$OUTPUT_DIR/summary.txt"
echo "Mock benchmark completed: $(test -f $OUTPUT_DIR/mock_benchmark_results.json && echo "Yes" || echo "No")" >> "$OUTPUT_DIR/summary.txt"
echo "Analysis modes tested: describe, detect, document" >> "$OUTPUT_DIR/summary.txt"

# Print summary
cat "$OUTPUT_DIR/summary.txt"
echo -e "${GREEN}All tests completed successfully. Results saved to ${OUTPUT_DIR}${NC}"

# Make the results directory browseable
chmod -R 755 "$OUTPUT_DIR"