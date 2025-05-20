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

# Check if bin directory is in PATH and try to add it automatically on macOS
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    # Detect shell and profile file
    if [[ "$OSTYPE" == "darwin"* ]]; then  # macOS
        SHELL_NAME=$(basename "$SHELL")
        if [ "$SHELL_NAME" = "zsh" ]; then
            PROFILE_FILE="$HOME/.zshrc"
        elif [ "$SHELL_NAME" = "bash" ]; then
            PROFILE_FILE="$HOME/.bash_profile"
        fi
        
        if [ -n "$PROFILE_FILE" ]; then
            # Check if we already have a PATH line for this directory
            if ! grep -q "export PATH=.*$BIN_DIR" "$PROFILE_FILE" 2>/dev/null; then
                echo "Adding $BIN_DIR to your PATH in $PROFILE_FILE"
                echo "" >> "$PROFILE_FILE"
                echo "# Added by file-analyzer install script" >> "$PROFILE_FILE"
                echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$PROFILE_FILE"
                echo "PATH updated in $PROFILE_FILE. Please run: source $PROFILE_FILE"
            fi
        else
            echo "Warning: $BIN_DIR is not in your PATH."
            echo "Please add the following line to your shell profile:"
            echo "  export PATH=\"\$PATH:$BIN_DIR\""
        fi
    else
        echo "Warning: $BIN_DIR is not in your PATH."
        echo "Please add the following line to your shell profile:"
        echo "  export PATH=\"\$PATH:$BIN_DIR\""
    fi
fi

# Create symbolic links with absolute paths
echo "Creating symbolic links in $BIN_DIR"
ln -sf "$ANALYZE_SCRIPT" "$BIN_DIR/analyze-files"
ln -sf "$ANALYZER_SCRIPT" "$BIN_DIR/file-analyzer"

# Create a wrapper script for analyze-files to ensure it can find the Python script
WRAPPER_SCRIPT="$BIN_DIR/analyze-files-wrapper"
cat > "$WRAPPER_SCRIPT" << EOL
#!/bin/bash
# Wrapper script for analyze.sh that ensures correct directory resolution
"${ANALYZE_SCRIPT}" "\$@"
EOL
chmod +x "$WRAPPER_SCRIPT"

# Update the analyze-files symlink to point to the wrapper
ln -sf "$WRAPPER_SCRIPT" "$BIN_DIR/analyze-files"

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