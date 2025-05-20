#!/bin/bash
# Install script for File Analysis System

set -e

# Find script directory (where we're installed)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZE_SCRIPT="${SCRIPT_DIR}/analyze.sh"
ANALYZER_SCRIPT="${SCRIPT_DIR}/file_analyzer.py"

# Default installation location
DEFAULT_BIN_DIR="${HOME}/bin"

# Parse arguments
BIN_DIR="${1:-$DEFAULT_BIN_DIR}"

# Check if analyzer scripts exist
if [ ! -f "$ANALYZE_SCRIPT" ] || [ ! -f "$ANALYZER_SCRIPT" ]; then
    echo "Error: Unable to find analyze.sh or file_analyzer.py in $SCRIPT_DIR"
    exit 1
fi

# Make sure scripts are executable
chmod +x "$ANALYZE_SCRIPT" "$ANALYZER_SCRIPT"

# Create bin directory if it doesn't exist
if [ ! -d "$BIN_DIR" ]; then
    echo "Creating directory: $BIN_DIR"
    mkdir -p "$BIN_DIR"
fi

# Check if bin directory is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Warning: $BIN_DIR is not in your PATH."
    echo "Consider adding the following line to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$PATH:$BIN_DIR\""
fi

# Create symbolic link
echo "Creating symbolic links in $BIN_DIR"
ln -sf "$ANALYZE_SCRIPT" "$BIN_DIR/analyze-files"
ln -sf "$ANALYZER_SCRIPT" "$BIN_DIR/file-analyzer"

echo "Installation complete!"
echo "You can now run the tool using 'analyze-files' or 'file-analyzer' commands."

# Check for required dependencies
echo "Checking for required dependencies..."
missing_tools=()

for tool in exiftool rdfind tesseract clamscan rg binwalk; do
    if ! command -v "$tool" &> /dev/null; then
        missing_tools+=("$tool")
    fi
done

if [ ${#missing_tools[@]} -gt 0 ]; then
    echo "Warning: The following required tools are missing:"
    for tool in "${missing_tools[@]}"; do
        echo "  - $tool"
    done
    echo "Please install missing dependencies. See INSTALL.md for instructions."
fi

exit 0