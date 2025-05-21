#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"
# Direct test script for FastVLM using the working approach

# Set up colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Test image
TEST_IMAGE="test_data/images/Layer 3 Merge.png"
MODEL_DIR="libs/ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3"

echo -e "${BLUE}=== FastVLM Direct Test ===${NC}"
echo -e "${BLUE}Model: ${MODEL_DIR}${NC}"
echo -e "${BLUE}Image: ${TEST_IMAGE}${NC}"

# Run direct test with different prompts
echo -e "\n${YELLOW}Testing with description prompt:${NC}"
python "$(dirname "${BASH_SOURCE[0]}")/../src/fastvlm_analyzer.py" --image "$TEST_IMAGE" --model "$MODEL_DIR" \
  --prompt "Describe this image in detail." --direct

echo -e "\n${YELLOW}Testing with architectural analysis prompt:${NC}"
python "$(dirname "${BASH_SOURCE[0]}")/../src/fastvlm_analyzer.py" --image "$TEST_IMAGE" --model "$MODEL_DIR" \
  --prompt "What architectural style is shown in this logo? Be specific." --direct

echo -e "\n${YELLOW}Testing with object detection prompt:${NC}"
python "$(dirname "${BASH_SOURCE[0]}")/../src/fastvlm_analyzer.py" --image "$TEST_IMAGE" --model "$MODEL_DIR" \
  --prompt "List all visual elements in this image and their positions." --direct

echo -e "\n${GREEN}Tests complete!${NC}"