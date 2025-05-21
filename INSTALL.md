# Installation Guide

The File Analysis System requires several external tools to be installed on your system to function properly. This guide provides instructions for installing these dependencies on different operating systems.

## Required Tools

- **ExifTool**: Metadata extraction
- **rdfind**: Duplicate detection
- **Tesseract OCR**: Text from images
- **ClamAV**: Malware scanning
- **ripgrep (rg)**: Content searching
- **binwalk**: Binary analysis
- **Python 3.8+**: Required for vision model analysis

## macOS (using Homebrew)

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install exiftool rdfind tesseract clamav ripgrep binwalk

# Initialize ClamAV
sudo freshclam
```

## Ubuntu/Debian

```bash
# Update package lists
sudo apt update

# Install required tools
sudo apt install -y libimage-exiftool-perl rdfind tesseract-ocr clamav ripgrep binwalk

# Update virus definitions
sudo freshclam
```

## RHEL/CentOS/Fedora

```bash
# Install required tools
sudo dnf install -y perl-Image-ExifTool rdfind tesseract clamav ripgrep binwalk

# Update virus definitions
sudo freshclam
```

## Windows (using Chocolatey)

First, install [Chocolatey](https://chocolatey.org/install), then:

```powershell
# Open PowerShell as Administrator and run:
choco install exiftool tesseract ripgrep clamav

# For tools not available in Chocolatey:
# 1. rdfind: Available through Windows Subsystem for Linux (WSL) or native port
#    - WSL method: Install Ubuntu via Microsoft Store, then `sudo apt install rdfind`
#    - Native Windows version: Download from https://github.com/pauldreik/rdfind/releases
#      and add to your PATH
#
# 2. binwalk: Available through Windows Subsystem for Linux or native installation
#    - WSL method: Install Ubuntu via Microsoft Store, then `sudo apt install binwalk`
#    - Native Windows method: 
#      - Clone repository: `git clone https://github.com/ReFirmLabs/binwalk.git`
#      - Install: `cd binwalk && python setup.py install`
#      - Requires Python and dependencies from https://github.com/ReFirmLabs/binwalk/blob/master/INSTALL.md
```

## Verifying Installation

After installation, you can verify that all tools are properly installed and available in your PATH by running:

```bash
file-analyzer --verify

## Vision Model Dependencies (Optional)

For using the AI-powered vision analysis features, additional dependencies are required:

### FastVLM (Recommended for Apple Silicon)

```bash
# Install MLX framework and FastVLM model
pip install mlx mlx-fastvlm

# Download the model (automatic when first used)
fastvlm download apple/fastvlm-1.5b-instruct
```

### Qwen2-VL (Best for Document Analysis)

```bash
# Install MLX-VLM framework
pip install mlx-vlm
```

### BakLLaVA (For Video Processing)

Option 1: Using llama.cpp (recommended for most users):

```bash
# Clone and build llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make

# Download the required model files (manual step)
# - BakLLaVA-1-Q4_K_M.gguf: The main model
# - BakLLaVA-1-clip-model.gguf: The vision encoder
```

Option 2: Using Fuzzy-Search implementation (for video processing):

```bash
# Clone and build realtime-bakllava
git clone https://github.com/Fuzzy-Search/realtime-bakllava
cd realtime-bakllava
make
```

## Troubleshooting

If you encounter issues with any of the tools:

1. **Tool not found**: Ensure the tool is installed and in your PATH
2. **Permission issues**: Some tools may require elevated privileges
3. **ClamAV errors**: Make sure virus definitions are up-to-date using `freshclam`
4. **Tesseract language packs**: For OCR in languages other than English, install additional language packs:
   - macOS: `brew install tesseract-lang`
   - Debian/Ubuntu: `sudo apt install tesseract-ocr-all`
5. **Vision model errors**: Vision models require specific Python packages. If you encounter errors:
   - Ensure Python 3.8+ is installed
   - Install dependencies for your chosen model as described above
   - For faster performance on Apple Silicon, ensure MLX is properly installed