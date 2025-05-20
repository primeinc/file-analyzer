# File Analysis System

Unified tool for comprehensive file analysis combining:

- ExifTool: Metadata extraction
- rdfind: Duplicate detection
- Tesseract OCR: Text from images
- ClamAV: Malware scanning
- ripgrep: Content searching
- binwalk: Binary analysis

## Usage

```bash
./analyze.sh [options] path_to_analyze
```

### Options

- `-a, --all`: Run all analyses
- `-m, --metadata`: Extract metadata
- `-d, --duplicates`: Find duplicates
- `-o, --ocr`: Perform OCR on images
- `-v, --virus`: Scan for malware
- `-s, --search TEXT`: Search content
- `-b, --binary`: Analyze binary files
- `-r, --results DIR`: Output directory
- `-i, --include PATTERN`: Include only files matching pattern
- `-x, --exclude PATTERN`: Exclude files matching pattern
- `-c, --config FILE`: Path to custom configuration file
- `--skip-checks`: Skip dependency checks
- `-q, --quiet`: Quiet mode with minimal output

### Examples

```bash
# Run all analyses on a directory
./analyze.sh -a ~/Documents

# Extract metadata and scan for duplicates
./analyze.sh -m -d ~/Pictures

# Search for specific content
./analyze.sh -s "password" ~/Downloads

# OCR images in a directory
./analyze.sh -o ~/Screenshots

# Include only specific file types
./analyze.sh -a -i "*.jpg" -i "*.png" ~/Pictures

# Exclude specific patterns
./analyze.sh -a -x "*.log" -x "*.tmp" ~/Documents

# Use a custom config file
./analyze.sh -a -c ~/my_config.json ~/Documents
```

## Output

Results are saved to the current directory (or specified output directory):

- `analysis_summary_[timestamp].json`: Overall summary
- `metadata_[timestamp].json`: File metadata
- `duplicates_[timestamp].txt`: Duplicate files
- `ocr_results_[timestamp].json`: Text from images
- `malware_scan_[timestamp].txt`: Malware scan results
- `search_[text]_[timestamp].txt`: Content search results
- `binary_analysis_[timestamp].txt`: Binary analysis

## Configuration

The system supports custom configuration files in JSON format. Create a `config.json` file in the current directory or specify a custom path with the `-c` option.

Example configuration:

```json
{
  "default_output_dir": "analysis_results",
  "max_threads": 4,
  "max_ocr_images": 50,
  "file_extensions": {
    "images": [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"]
  },
  "default_exclude_patterns": ["*.log", "*.tmp", "*.bak"]
}
```

## Installation

### Tool Installation

You can install the File Analysis System to your PATH using the provided install script:

```bash
# Install to ~/bin (default)
./install.sh

# Or specify a custom installation directory
./install.sh /usr/local/bin
```

This creates symbolic links to the tool in the specified directory. After installation, you can run the tool using:

- `analyze-files` - for the shell script wrapper
- `file-analyzer` - for the Python script directly

### Dependencies Installation

See [INSTALL.md](INSTALL.md) for detailed instructions on installing all required dependencies.

## Running Tests

Basic tests can be run using:

```bash
./tests/test_basic.sh
```

## Using the Python Script Directly

```bash
./file_analyzer.py [options] path_to_analyze
```

Options are the same as the shell wrapper but use full format (e.g., `--metadata` instead of `-m`).