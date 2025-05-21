#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard.sh"
# Install script for file-analyzer

# Default installation directory
if [ -z "$1" ]; then
    INSTALL_DIR="$HOME/bin"
else
    INSTALL_DIR="$1"
fi

# Create installation directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Check if directory exists and is writable
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: Installation directory $INSTALL_DIR could not be created"
    exit 1
fi

if [ ! -w "$INSTALL_DIR" ]; then
    echo "Error: Installation directory $INSTALL_DIR is not writable"
    exit 1
fi

# Get absolute path to source directory
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create symbolic links for the analyzer tools
ln -sf "$SOURCE_DIR/tools/analyze.sh" "$INSTALL_DIR/analyze-files"
ln -sf "$SOURCE_DIR/src/analyzer.py" "$INSTALL_DIR/file-analyzer"

# Make the Python script executable
chmod +x "$SOURCE_DIR/src/analyzer.py"

# Check if installation was successful
if [ -L "$INSTALL_DIR/analyze-files" ] && [ -L "$INSTALL_DIR/file-analyzer" ]; then
    echo "Installation successful!"
    echo "The following commands are now available:"
    echo "  - analyze-files: Shell script wrapper"
    echo "  - file-analyzer: Python script"
    
    # Check if installation directory is in PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo ""
        echo "WARNING: $INSTALL_DIR is not in your PATH."
        echo "Add the following line to your ~/.bashrc or ~/.zshrc file:"
        echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    fi
    
    exit 0
else
    echo "Installation failed."
    exit 1
fi