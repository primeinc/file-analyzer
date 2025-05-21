#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"
# Comprehensive test script for FastVLM integration

# Set up colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print section headers
print_header() {
  echo -e "\n${BLUE}=====================================${NC}"
  echo -e "${BLUE}  $1${NC}"
  echo -e "${BLUE}=====================================${NC}\n"
}

# Function to check if a command succeeded
check_result() {
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ $1 completed successfully${NC}"
  else
    echo -e "${RED}✗ $1 failed${NC}"
    if [ "$2" = "exit" ]; then
      exit 1
    fi
  fi
}

# Check test image exists
check_test_image() {
  TEST_IMAGE="test_data/images/Layer 3 Merge.png"
  if [ ! -f "$TEST_IMAGE" ]; then
    echo -e "${YELLOW}Warning: Default test image not found${NC}"
    # Find any image
    TEST_IMAGE=$(find test_data -name "*.png" -o -name "*.jpg" | head -1)
    if [ -z "$TEST_IMAGE" ]; then
      echo -e "${RED}No test images found. Exiting.${NC}"
      exit 1
    fi
    echo -e "${GREEN}Using alternative test image: $TEST_IMAGE${NC}"
  fi
  echo "$TEST_IMAGE"
}

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run preflight check to ensure artifact structure exists
"$SCRIPT_DIR/preflight.sh" --no-tmp-clean >/dev/null 2>&1

# Get canonical output directory
OUTPUT_DIR=$("$SCRIPT_DIR/cleanup.sh" --path vision fastvlm_tests)

# Clean directory to start fresh
rm -rf "$OUTPUT_DIR"/*
mkdir -p "$OUTPUT_DIR"

echo -e "${GREEN}Test results will be saved to $OUTPUT_DIR${NC}"

# Check environment
print_header "CHECKING ENVIRONMENT"
python "$PROJECT_ROOT/src/fastvlm_errors.py" | tee "$OUTPUT_DIR/environment_check.txt"
check_result "Environment check" "continue"

# Check FastVLM model
print_header "VERIFYING FASTVLM MODEL"
MODEL_DIR="libs/ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3"
if [ -d "$MODEL_DIR" ]; then
  echo -e "${GREEN}Found FastVLM model at $MODEL_DIR${NC}"
  ls -la "$MODEL_DIR" | tee "$OUTPUT_DIR/model_files.txt"
else
  echo -e "${RED}FastVLM model not found at $MODEL_DIR${NC}"
  echo -e "${YELLOW}You may need to run: cd libs/ml-fastvlm && ./get_models.sh${NC}"
fi

# Check test image
TEST_IMAGE=$(check_test_image)

# Basic vision analysis test
print_header "TESTING BASIC VISION ANALYSIS"
./file_analyzer.py --vision --vision-model fastvlm --skip-dependency-check "$TEST_IMAGE" | tee "$OUTPUT_DIR/basic_analysis.txt"
check_result "Basic vision analysis" "continue"

# Test different analysis modes
print_header "TESTING DIFFERENT ANALYSIS MODES"
echo -e "${YELLOW}Testing description mode...${NC}"
./file_analyzer.py --vision --vision-model fastvlm --vision-mode describe --skip-dependency-check "$TEST_IMAGE" | tee "$OUTPUT_DIR/describe_mode.txt"

echo -e "${YELLOW}Testing detection mode...${NC}"
./file_analyzer.py --vision --vision-model fastvlm --vision-mode detect --skip-dependency-check "$TEST_IMAGE" | tee "$OUTPUT_DIR/detect_mode.txt"

echo -e "${YELLOW}Testing document mode...${NC}"
./file_analyzer.py --vision --vision-model fastvlm --vision-mode document --skip-dependency-check "$TEST_IMAGE" | tee "$OUTPUT_DIR/document_mode.txt"

# Run benchmark (quick version)
print_header "RUNNING QUICK BENCHMARK"
python "$PROJECT_ROOT/src/benchmark_fastvlm.py" --output "$OUTPUT_DIR/benchmark_results.json" | tee "$OUTPUT_DIR/benchmark.txt"
check_result "Benchmark" "continue"

# Test direct script usage
print_header "TESTING DIRECT SCRIPT USAGE"
python "$PROJECT_ROOT/src/fastvlm_test.py" --image "$TEST_IMAGE" --prompt "Describe this image in detail" | tee "$OUTPUT_DIR/direct_usage.txt"
check_result "Direct script usage" "continue"

# Final summary
print_header "TEST SUMMARY"
echo -e "${GREEN}All tests completed${NC}"
echo -e "${BLUE}Test results saved to $OUTPUT_DIR${NC}"
echo -e "${YELLOW}For detailed information on using FastVLM, see FASTVLM.md${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Review the test results in $OUTPUT_DIR"
echo "2. Run a full benchmark with: python $PROJECT_ROOT/src/benchmark_fastvlm.py"
echo "3. Try batch processing with: python $PROJECT_ROOT/src/analyzer.py --vision --vision-model fastvlm test_data/images/"
echo ""