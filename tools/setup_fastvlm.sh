#!/bin/bash
# Setup script for FastVLM environment
#
# This script sets up the FastVLM environment by either:
# 1. Using pip to install the mlx-fastvlm package if available
# 2. Cloning the FastVLM repository and setting it up for use

set -e  # Exit immediately if a command exits with a non-zero status

# Use Python artifact system for logging
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(dirname "$script_dir")"

# Source the Python artifact discipline adapter
source "$project_root/artifact_guard_py_adapter.sh"

# Create artifact directory for logs
artifact_dir=$(get_canonical_artifact_path "tmp" "setup_fastvlm")
log_file="$artifact_dir/setup.log"

echo "Setting up FastVLM environment..."
echo "Logs will be saved to $log_file"

# Log function that writes to both console and log file
log() {
    echo "$@" | tee -a "$log_file"
}

log "Setup starting at $(date)"
log "Working directory: $(pwd)"

# Define directories
FASTVLM_DIR="$project_root/libs/ml-fastvlm"

# Check if mlx-fastvlm is available via pip
if pip show mlx-fastvlm &>/dev/null; then
    log "✓ mlx-fastvlm package is already installed"
    log "No further setup needed."
    # Still run the model check to ensure models are available
    python "$project_root/tools/download_models.py" list | tee -a "$log_file"
    exit 0
fi

# Check if MLX is installed (required for FastVLM)
if ! pip show mlx &>/dev/null; then
    log "⚠ MLX not found, installing..."
    pip install mlx | tee -a "$log_file"
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log "✗ Failed to install MLX. Please install it manually: pip install mlx"
        exit 1
    fi
    log "✓ MLX installed successfully"
fi

# Check if the FastVLM repository exists
if [ -d "$FASTVLM_DIR/.git" ]; then
    log "FastVLM repository already exists at $FASTVLM_DIR"
    
    # Check if we need to update it
    cd "$FASTVLM_DIR"
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    log "Current branch: $current_branch"
    
    # We'll use the main branch for now
    target_branch="main"
    
    if [ "$current_branch" != "$target_branch" ]; then
        log "Updating FastVLM repository to $target_branch branch..."
        git fetch origin | tee -a "$log_file"
        git checkout "$target_branch" | tee -a "$log_file"
        git pull origin "$target_branch" | tee -a "$log_file"
        log "✓ Updated FastVLM repository"
    else
        log "Pulling latest changes from $target_branch..."
        git pull origin "$target_branch" | tee -a "$log_file"
        log "✓ FastVLM repository updated"
    fi
else
    log "FastVLM repository not found, cloning..."
    mkdir -p "$project_root/libs"
    
    # Clean up existing directory if needed
    if [ -d "$FASTVLM_DIR" ]; then
      rm -rf "$FASTVLM_DIR"
    fi
    
    # Clone the repository
    git clone https://github.com/apple/ml-fastvlm.git "$FASTVLM_DIR" | tee -a "$log_file"
    if [ $? -ne 0 ]; then
        log "✗ Failed to clone FastVLM repository"
        exit 1
    fi
    
    log "✓ FastVLM repository cloned successfully"
fi

# Change to the repository directory
cd "$FASTVLM_DIR" || exit 1

# Check for a specific version or use main if not available
FASTVLM_VERSION="main"  # Default to main
log "Using FastVLM version $FASTVLM_VERSION..."
git checkout "$FASTVLM_VERSION" >> "$log_file" 2>&1
if [ $? -ne 0 ]; then
  log "Failed to checkout $FASTVLM_VERSION. See $log_file for details."
  exit 1
fi

# Check if we should install in development mode
if [ -f "$FASTVLM_DIR/setup.py" ]; then
    log "Installing FastVLM package in development mode..."
    pip install -e "$FASTVLM_DIR" | tee -a "$log_file"
    if [ $? -ne 0 ]; then
        log "✗ Failed to install FastVLM package"
        log "  Will continue with script-based approach instead"
    else
        log "✓ FastVLM package installed in development mode"
    fi
fi

# Check if the predict.py script exists
if [ ! -f "$FASTVLM_DIR/predict.py" ]; then
    log "✗ predict.py script not found in the FastVLM repository"
    log "Please check that the repository was cloned correctly"
    exit 1
fi

log "✓ FastVLM environment setup completed successfully"

# Download the default model
log "Checking for available models..."
python "$project_root/tools/download_models.py" list | tee -a "$log_file"

log "Downloading the default model (0.5b) if not already available..."
python "$project_root/tools/download_models.py" download --size 0.5b | tee -a "$log_file"

log "Setup completed at $(date)"
log "You can now use FastVLM through the file analyzer system."
log "To download additional models, run:"
log "  python $project_root/tools/download_models.py download --size 1.5b"
log "  python $project_root/tools/download_models.py download --size 7b"

exit 0