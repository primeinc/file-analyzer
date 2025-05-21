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
    python "$project_root/src/download_models.py" list | tee -a "$log_file"
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

# Install required Python dependencies
log "Installing FastVLM dependencies..."
# Check if we should install in development mode
if [ -f "$FASTVLM_DIR/setup.py" ]; then
    log "Installing FastVLM package in development mode..."
    pip install -e "$FASTVLM_DIR" >> "$log_file" 2>&1
    if [ $? -ne 0 ]; then
        log "⚠ Warning: Could not install FastVLM via pip -e. Installing required libraries individually..."
        pip install transformers accelerate sentencepiece >> "$log_file" 2>&1
        if [ $? -ne 0 ]; then
            log "✗ Failed to install necessary dependencies"
            exit 1
        fi
    else
        log "✓ FastVLM package installed in development mode"
    fi
else
    log "⚠ Warning: No setup.py found, installing required libraries individually..."
    pip install transformers accelerate sentencepiece >> "$log_file" 2>&1
    if [ $? -ne 0 ]; then
        log "✗ Failed to install necessary dependencies"
        exit 1
    fi
    log "✓ Required dependencies installed"
fi

# Check if the predict.py script exists
if [ ! -f "$FASTVLM_DIR/predict.py" ]; then
    log "✗ predict.py script not found in the FastVLM repository"
    log "Please check that the repository was cloned correctly"
    exit 1
fi

# Create the get_models.sh script if it doesn't exist
if [ ! -f "$FASTVLM_DIR/get_models.sh" ]; then
    log "Creating get_models.sh script for model download..."
    cat > "$FASTVLM_DIR/get_models.sh" << 'EOF'
#!/bin/bash
# Script to download FastVLM models

set -e

MODEL_SIZE="${1:-0.5b}"  # Default to 0.5b if not specified
CHECKPOINTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/checkpoints"

# Create checkpoints directory
mkdir -p "$CHECKPOINTS_DIR"

# Download the specified model
if [ "$MODEL_SIZE" == "0.5b" ]; then
    MODEL_NAME="llava-fastvithd_0.5b_stage2"
    MODEL_URL="https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_0.5b_stage2.zip"
elif [ "$MODEL_SIZE" == "1.5b" ]; then
    MODEL_NAME="llava-fastvithd_1.5b_stage2"
    MODEL_URL="https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_1.5b_stage2.zip"
elif [ "$MODEL_SIZE" == "7b" ]; then
    MODEL_NAME="llava-fastvithd_7b_stage2"
    MODEL_URL="https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_7b_stage2.zip"
else
    echo "Unknown model size: $MODEL_SIZE"
    echo "Valid sizes are: 0.5b, 1.5b, 7b"
    exit 1
fi

MODEL_DIR="$CHECKPOINTS_DIR/$MODEL_NAME"
ZIP_PATH="$CHECKPOINTS_DIR/${MODEL_NAME}.zip"

# Check if model directory already exists and contains files
if [ -d "$MODEL_DIR" ] && [ "$(find "$MODEL_DIR" -type f | wc -l)" -gt 5 ]; then
    echo "Model already exists at $MODEL_DIR"
    echo "Skipping download"
    
    # Delete any existing zip files
    if [ -f "$ZIP_PATH" ]; then
        echo "Removing existing zip file $ZIP_PATH"
        rm -f "$ZIP_PATH"
    fi
    exit 0
fi

# Create model directory
mkdir -p "$MODEL_DIR"

# Check if we already have the zip file
if [ -f "$ZIP_PATH" ]; then
    echo "Using existing download at $ZIP_PATH"
else
    # Download model
    echo "Downloading $MODEL_SIZE model from $MODEL_URL"
    curl -L "$MODEL_URL" -o "$ZIP_PATH"
fi

# Extract model
echo "Extracting model to $MODEL_DIR"
unzip -o "$ZIP_PATH" -d "$MODEL_DIR"

# Remove zip file after successful extraction
echo "Removing zip file after extraction"
rm -f "$ZIP_PATH"

# Create necessary files for tokenizer
# Ensure required files exist
if [ ! -f "$MODEL_DIR/tokenizer_config.json" ]; then
    echo "Creating tokenizer config..."
    cat > "$MODEL_DIR/tokenizer_config.json" << 'TOKENIZER_EOF'
{
  "model_type": "llama",
  "pad_token": "<pad>",
  "bos_token": "<s>",
  "eos_token": "</s>",
  "unk_token": "<unk>"
}
TOKENIZER_EOF
fi

if [ ! -f "$MODEL_DIR/config.json" ]; then
    echo "Creating model config..."
    cat > "$MODEL_DIR/config.json" << 'CONFIG_EOF'
{
  "model_type": "llama",
  "architectures": ["LlamaForCausalLM"],
  "hidden_size": 4096,
  "intermediate_size": 11008,
  "num_attention_heads": 32,
  "num_hidden_layers": 32,
  "vocab_size": 32000
}
CONFIG_EOF
fi

echo "Model files ready at $MODEL_DIR"
echo "Total files:"
find "$MODEL_DIR" -type f | wc -l

exit 0
EOF
    chmod +x "$FASTVLM_DIR/get_models.sh"
    log "✓ Created get_models.sh script"
fi

# Create checkpoints directory
mkdir -p "$FASTVLM_DIR/checkpoints"

# Clean up duplicate downloads if they exist
log "Cleaning up any duplicate downloads..."
find "$FASTVLM_DIR/checkpoints" -name "*.zip.*" -type f -exec rm -f {} \;
[ $? -eq 0 ] && log "✓ Cleaned up duplicate downloads"

# Download the default model to the repository
log "Downloading the default model (0.5b) to the repository..."
if [ -x "$FASTVLM_DIR/get_models.sh" ]; then
    (cd "$FASTVLM_DIR" && ./get_models.sh 0.5b) | tee -a "$log_file"
    
    # Copy model files to user directory for centralized storage
    log "Copying model files to user model directory for centralized storage..."
    model_path=$(python -c "import os; from src.model_config import MODEL_CHECKPOINTS; print(os.path.join(os.path.expanduser('~/.local/share/fastvlm'), MODEL_CHECKPOINTS['fastvlm']['0.5b']['path']))" 2>/dev/null)
    
    if [ -n "$model_path" ]; then
        mkdir -p "$model_path"
        
        # Check if repo has the model files
        repo_model_dir="$FASTVLM_DIR/checkpoints/llava-fastvithd_0.5b_stage2"
        if [ -d "$repo_model_dir" ] && [ "$(find "$repo_model_dir" -type f | wc -l)" -gt 0 ]; then
            # Copy model files to user directory
            cp -r "$repo_model_dir"/* "$model_path"/ 2>/dev/null || true
            log "✓ Model files copied to user model directory: $model_path"
        else
            log "⚠ Model files not found in repository to copy to user directory"
        fi
    else
        log "⚠ Could not determine user model directory path"
    fi
else
    log "⚠ get_models.sh script not executable, using download_models.py instead..."
fi

log "✓ FastVLM environment setup completed successfully"

# Now check and download with our management system
log "Checking for available models..."
python "$project_root/src/download_models.py" list | tee -a "$log_file"

log "Ensuring model is available through model management system..."
python "$project_root/src/download_models.py" download --size 0.5b | tee -a "$log_file"

log "Setup completed at $(date)"
log "You can now use FastVLM through the file analyzer system."
log "To download additional models, run:"
log "  python $project_root/src/download_models.py download --size 1.5b"
log "  python $project_root/src/download_models.py download --size 7b"

exit 0