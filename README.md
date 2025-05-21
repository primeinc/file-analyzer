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
- `-V, --vision`: Analyze images using AI vision models (outputs JSON by default)
- `--vision-model MODEL`: Select vision model (fastvlm, bakllava, qwen2vl)
- `--vision-mode MODE`: Vision analysis mode (describe, detect, document)
- `--vision-format FMT`: Vision output format (json, text, markdown) - json recommended
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

# Use custom format (JSON is default and recommended)
./analyze.sh -V --vision-format json ~/Pictures

# Examine the JSON output
cat analysis_results/vision_analysis_*.json
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
- `vision_analysis_[timestamp].json`: AI vision model analysis (JSON format)
- `vision_metrics_[timestamp].json`: Vision analysis performance metrics

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
    "output_format": "json",
    "max_retries": 3
  }
}
```

## Vision Model Analysis

The system includes advanced AI vision models for image analysis with robust JSON output:

### Available Models

- **FastVLM**: Apple's efficient vision model (default, fastest on Apple Silicon)
  - Model variants: 0.5B (fastest), 1.5B (default), 7B (highest quality)
  - Performance: Up to 85x faster Time-to-First-Token than alternatives
  
- **BakLLaVA**: Mature vision language model with good performance
  - Works well on all platforms
  - More mature with better handling of complex scenes
  
- **Qwen2-VL**: Document analysis specialist
  - Optimized for text extraction from documents
  - Good performance on structured content

### Analysis Modes

- **describe** (default): General image description with details and context
- **detect**: Object detection with locations and relationships
- **document**: Optimized for text extraction from documents/screenshots

### JSON Output Structure

All vision analysis results are provided in a structured JSON format:

```json
{
  "/path/to/image.jpg": {
    "description": "Detailed image description text...",
    "tags": ["tag1", "tag2", "tag3"],
    "metadata": {
      "response_time": 1.25,
      "model": "FastVLM 1.5B",
      "timestamp": "2025-05-20 15:30:45",
      "attempts": 1,
      "mode": "describe"
    }
  }
}
```

### JSON Validation Features

The system implements robust JSON validation for reliable output:

1. **Advanced Extraction and Validation**
   - Sophisticated JSON extraction with balanced bracket matching
   - Handles nested objects and arrays correctly
   - Multiple extraction strategies for different response patterns
   - Centralized validation through dedicated `json_utils` module

2. **Automatic Retry Logic**
   - Multiple retry attempts with progressively stronger JSON-forcing prompts
   - Ensures valid, well-structured output even when model responses vary
   - Graceful fallback to text output when JSON parsing fails completely
   - Detailed failure metadata for debugging purposes

3. **Extraction Capabilities**
   - Can extract valid JSON even from partially correct text responses
   - Uses intelligent pattern matching to find embedded JSON objects
   - Supports specialized patterns for different analysis modes (describe, detect, document)
   - Preserves context and field relationships in extraction

4. **Performance Metrics**
   - Tracks response time and other performance indicators
   - Records number of retry attempts needed for valid JSON
   - Provides detailed metrics in separate JSON file for benchmarking
   - Standardized metadata format across all output types

## FastVLM Integration

FastVLM is Apple's efficient vision language model designed specifically for Apple Silicon.

### Installation

```bash
# Install MLX framework and FastVLM model 
pip install mlx mlx-fastvlm

# Download the model (automatic when first used)
fastvlm download apple/fastvlm-1.5b-instruct
```

#### Alternative Manual Installation

If you prefer more control over the installation process:

1. Install MLX framework for Apple Silicon optimization:
   ```bash
   pip install mlx
   ```

2. Clone the FastVLM repository and install dependencies:
   ```bash
   git clone https://github.com/apple/ml-fastvlm.git
   cd ml-fastvlm
   pip install -e .
   ```

3. Download model weights:
   ```bash
   cd ml-fastvlm
   chmod +x get_models.sh
   ./get_models.sh
   ```

### Optimization

FastVLM includes several optimization features:

- **Image Preprocessing**: Automatically resizes and optimizes images
  - Description Mode: 512x512 resolution (default)
  - Object Detection: 384x384 resolution
  - Document Analysis: 768x768 resolution

- **Memory Optimization**: 
  - 4-bit quantization for efficient memory usage
  - Metal acceleration for Apple Silicon
  - Resolution customization based on analysis needs

### Troubleshooting

Common issues and solutions:

1. **Out of Memory Errors**: Use a smaller model or reduce batch size
2. **Slow Performance**: Ensure Metal acceleration is enabled
3. **Model Loading Failures**: Check model files with `fastvlm_errors.py`
4. **Image Format Errors**: Ensure images are in supported formats (JPG, PNG)

For more detailed error diagnostics, run:
```bash
./fastvlm_errors.py
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

# Test vision analysis capabilities with JSON validation
./test_vision.sh

# Test JSON output formatting and validation
./test_json_output.sh
```

The test suite verifies:
- Metadata extraction functionality
- Duplicate file detection
- Content searching capabilities  
- File filtering with include/exclude patterns
- Vision model integration with JSON validation
- Performance metrics collection

## Using the Python Script Directly

```bash
./file_analyzer.py [options] path_to_analyze
```

Options are the same as the shell wrapper but use full format (e.g., `--metadata` instead of `-m`).

## Contributing

### Adding New Features

When adding new capabilities to the File Analyzer system, please follow these conventions:

1. **Modular Design**: Add new analysis types as separate methods in the `FileAnalyzer` class.
2. **CLI Integration**: Update both `file_analyzer.py` and `analyze.sh` with new options.
3. **Documentation**: Update the README.md with descriptions and examples of the new feature.
4. **Tests**: Add appropriate test cases in the test suite.
5. **Configuration**: Add relevant configuration options in config.json.

### Code Conventions

- **Error Handling**: Use consistent error handling with try/except blocks.
- **Status Reporting**: Update the `self.results` dictionary with status information.
- **Output Format**: For structured data, prefer JSON output with consistent fields.
- **Dependencies**: Document any new external dependencies in INSTALL.md.
- **Performance**: Use multithreading for CPU-bound operations when appropriate.

### JSON Output Standards

When adding new analysis types that produce JSON output:

1. Include a `status` field ("success", "error", or "skipped")
2. Include a `timestamp` field with the analysis time
3. For ML models, include performance metrics
4. Implement validation to ensure output is always valid JSON
5. Use consistent field naming across different analysis types