# File Analysis System

Unified tool for comprehensive file analysis combining:

- ExifTool: Metadata extraction
- rdfind: Duplicate detection
- Tesseract OCR: Text from images
- ClamAV: Malware scanning
- ripgrep: Content searching
- binwalk: Binary analysis
- Vision Models: AI-powered image analysis (FastVLM, BakLLaVA, Qwen2-VL)

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
- `-V, --vision`: Analyze images using AI vision models
- `--vision-model MODEL`: Select vision model (fastvlm, bakllava, qwen2vl)
- `--vision-mode MODE`: Vision analysis mode (describe, detect, document)
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

# Analyze images with AI vision models
./analyze.sh -V ~/Pictures

# Use a specific vision model
./analyze.sh -V --vision-model fastvlm ~/Pictures

# Use document analysis mode for extracting text
./analyze.sh -V --vision-mode document ~/Documents
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
- `vision_analysis_[timestamp].(txt|json)`: AI vision model analysis

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
  "default_exclude_patterns": ["*.log", "*.tmp", "*.bak"],
  "vision": {
    "model": "fastvlm",
    "max_images": 10,
    "description_mode": "standard",
    "output_format": "text"
  }
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

#### Vision Model Dependencies

For vision analysis capabilities, additional dependencies are required:

```bash
# For FastVLM (recommended for Apple Silicon)
pip install mlx mlx-fastvlm

# For Qwen2-VL (good for document analysis)
pip install mlx-vlm

# For BakLLaVA
# Requires llama.cpp with BakLLaVA-1-Q4_K_M.gguf model
git clone https://github.com/Fuzzy-Search/realtime-bakllava
cd realtime-bakllava && make
```

## Running Tests

The project includes a comprehensive test suite:

```bash
# Run the automated test suite
cd test_data && ./run_tests.sh

# Test vision analysis capabilities
./test_vision.sh
```

The test suite verifies:
- Metadata extraction functionality
- Duplicate file detection
- Content searching capabilities  
- File filtering with include/exclude patterns
- Vision model integration (when dependencies are installed)

## Using the Python Script Directly

```bash
./file_analyzer.py [options] path_to_analyze
```

Options are the same as the shell wrapper but use full format (e.g., `--metadata` instead of `-m`).