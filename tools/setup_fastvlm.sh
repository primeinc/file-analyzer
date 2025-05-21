#!/bin/bash
# Setup script for FastVLM repository and dependencies
# This script checks for FastVLM in the libs directory and sets it up if needed

source "$(dirname "${BASH_SOURCE[0]}")/../artifact_guard_py_adapter.sh"

# Define directories
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTVLM_DIR="$PROJECT_ROOT/libs/ml-fastvlm"
LOG_DIR=$(get_canonical_artifact_path "tmp" "fastvlm_setup")
LOG_FILE="$LOG_DIR/setup.log"

echo "Setting up FastVLM dependencies in $FASTVLM_DIR"
echo "Logs will be written to $LOG_FILE"

mkdir -p "$LOG_DIR"

# Check if FastVLM repository exists
if [ ! -d "$FASTVLM_DIR/.git" ]; then
  echo "Cloning FastVLM repository..."
  
  # Clean up existing directory if needed
  if [ -d "$FASTVLM_DIR" ]; then
    rm -rf "$FASTVLM_DIR"
  fi
  
  # Clone the repository
  mkdir -p "$FASTVLM_DIR"
  git clone https://github.com/apple/ml-fastvlm.git "$FASTVLM_DIR" >> "$LOG_FILE" 2>&1
  
  # Check if clone was successful
  if [ $? -ne 0 ]; then
    echo "Failed to clone FastVLM repository. See $LOG_FILE for details."
    exit 1
  fi
fi

# Change to the repository directory
cd "$FASTVLM_DIR" || exit 1

# Check for a specific version or use main if not available
FASTVLM_VERSION="main"  # Default to main
echo "Using FastVLM version $FASTVLM_VERSION..."
git checkout "$FASTVLM_VERSION" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
  echo "Failed to checkout $FASTVLM_VERSION. See $LOG_FILE for details."
  exit 1
fi

# Install the package in development mode
echo "Installing FastVLM package..."
pip install -e . >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
  echo "Failed to install FastVLM package. See $LOG_FILE for details."
  exit 1
fi

# Run our model configuration checker
echo "Checking model configuration..."
python "$PROJECT_ROOT/tools/download_models.py" --info

echo "FastVLM setup completed successfully!"