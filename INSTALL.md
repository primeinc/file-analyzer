# Installation Guide

The File Analysis System requires several external tools to be installed on your system to function properly. This guide provides instructions for installing these dependencies on different operating systems.

## Required Tools

- **ExifTool**: Metadata extraction
- **rdfind**: Duplicate detection
- **Tesseract OCR**: Text from images
- **ClamAV**: Malware scanning
- **ripgrep (rg)**: Content searching
- **binwalk**: Binary analysis

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
# 1. rdfind: Use Windows Subsystem for Linux (WSL)
# 2. binwalk: Use Windows Subsystem for Linux (WSL)
```

## Verifying Installation

After installation, you can verify that all tools are properly installed and available in your PATH by running:

```bash
./analyze.sh --skip-checks -a <path_to_analyze>
```

If any tools are missing, the system will show an error message indicating which tools need to be installed.

## Troubleshooting

If you encounter issues with any of the tools:

1. **Tool not found**: Ensure the tool is installed and in your PATH
2. **Permission issues**: Some tools may require elevated privileges
3. **ClamAV errors**: Make sure virus definitions are up-to-date using `freshclam`
4. **Tesseract language packs**: For OCR in languages other than English, install additional language packs:
   - macOS: `brew install tesseract-lang`
   - Debian/Ubuntu: `sudo apt install tesseract-ocr-all`