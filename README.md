# File Analysis System

Unified tool for comprehensive file analysis combining:

- ExifTool: Metadata extraction
- rdfind: Duplicate detection
- Tesseract OCR: Text from images
- ClamAV: Malware scanning
- ripgrep: Content searching
- binwalk: Binary analysis
- Vision Models: AI-powered image analysis (FastVLM, BakLLaVA, Qwen2-VL)

## Project Structure

```
├── src/                        # Core source code (Python modules)
│   ├── analyzer.py             # Main analyzer module
│   ├── vision.py               # Vision analysis module
│   ├── json_utils.py           # JSON processing utilities
│   ├── model_config.py         # Model management configuration
│   ├── fastvlm_adapter.py      # FastVLM model adapter
│   └── artifact_guard.py       # Artifact path discipline
│
├── tools/                      # Command-line tools and utilities
│   ├── analyze.sh              # Main CLI wrapper
│   ├── vision_test.sh          # Vision model testing
│   ├── json_test.sh            # JSON output testing
│   ├── download_models.py      # Model download utility
│   ├── setup_fastvlm.sh        # FastVLM environment setup
│   ├── benchmark_fastvlm.py    # Model benchmarking tools
│   └── ...                     # Other utility scripts
│
├── tests/                      # Test scripts and validation
│   ├── test_path_enforcement.sh
│   ├── strict_example.sh       
│   ├── test_fastvlm.sh
│   └── ...                     # Test harnesses
│
├── artifacts/                  # Canonical storage for outputs
│   ├── analysis/               # Analysis results
│   ├── vision/                 # Vision model outputs
│   ├── test/                   # Test results
│   ├── benchmark/              # Performance benchmarks
│   └── tmp/                    # Temporary files
│
├── artifact_guard_py_adapter.sh # Runtime path enforcement
└── libs/                      # External libraries
    └── ml-fastvlm/              # FastVLM vision library (CODE ONLY)
    
Model files are stored in ~/.local/share/fastvlm/ (see MODELS.md)
```

## Usage

```bash
./tools/analyze.sh [options] path_to_analyze
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
./tools/analyze.sh -a ~/Documents

# Extract metadata and scan for duplicates
./tools/analyze.sh -m -d ~/Pictures

# Search for specific content
./tools/analyze.sh -s "password" ~/Downloads

# OCR images in a directory
./tools/analyze.sh -o ~/Screenshots

# Include only specific file types
./tools/analyze.sh -a -i "*.jpg" -i "*.png" ~/Pictures

# Exclude specific patterns
./tools/analyze.sh -a -x "*.log" -x "*.tmp" ~/Documents

# Use a custom config file
./tools/analyze.sh -a -c ~/my_config.json ~/Documents

# Analyze images with AI vision models
./tools/analyze.sh -V ~/Pictures

# Use a specific vision model
./tools/analyze.sh -V --vision-model fastvlm ~/Pictures

# Use document analysis mode for extracting text
./tools/analyze.sh -V --vision-mode document ~/Documents

# Use custom format (JSON is default and recommended)
./tools/analyze.sh -V --vision-format json ~/Pictures
```

## Output

Results are saved to the canonical artifacts directory structure:

- `artifacts/analysis/<context>_<unique_id>/summary.json`: Overall summary
- `artifacts/analysis/<context>_<unique_id>/metadata.json`: File metadata
- `artifacts/analysis/<context>_<unique_id>/duplicates.txt`: Duplicate files
- `artifacts/analysis/<context>_<unique_id>/ocr_results.json`: Text from images
- `artifacts/analysis/<context>_<unique_id>/malware_scan.txt`: Malware scan results
- `artifacts/analysis/<context>_<unique_id>/search_results.txt`: Content search results
- `artifacts/analysis/<context>_<unique_id>/binary_analysis.txt`: Binary analysis
- `artifacts/vision/<context>_<unique_id>/vision_analysis.json`: AI vision model analysis
- `artifacts/vision/<context>_<unique_id>/vision_metrics.json`: Vision analysis performance metrics

## Configuration

The system supports custom configuration files in JSON format. Create a `config.json` in the current directory or specify a custom path with the `-c` option.

Example configuration:

```json
{
  "default_output_dir": "artifacts/analysis",
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

## Model Management System

The File Analyzer uses a centralized model management system for handling AI model files. This system keeps large model files outside the git repository while providing a consistent interface for model access.

For complete details, see [MODELS.md](MODELS.md).

### Key Features

- **Centralized storage**: Models are stored in `~/.local/share/fastvlm/`
- **Automatic download**: Models are downloaded automatically when needed
- **Multiple model sizes**: Support for 0.5B (small), 1.5B (medium), and 7B (large) models
- **CI integration**: GitHub Actions workflows for model caching

### Setup and Usage

```bash
# Set up the environment
./tools/setup_fastvlm.sh

# List available models
python tools/download_models.py list

# Download a specific model
python tools/download_models.py download --size 0.5b

# Get model information
python tools/download_models.py info --size 0.5b
```

### Model Adapter

The system includes a unified adapter interface for model access:

```python
from src.fastvlm_adapter import create_adapter

# Create adapter
adapter = create_adapter(model_size="0.5b")

# Run prediction
result = adapter.predict(image_path="path/to/image.jpg", 
                         prompt="Describe this image.",
                         mode="describe")
```

## FastVLM Integration

FastVLM is Apple's efficient vision language model designed specifically for Apple Silicon.

### Installation

The simplest way to set up FastVLM is to use our setup script:

```bash
# Run the setup script
./tools/setup_fastvlm.sh

# This will:
# 1. Install MLX if needed
# 2. Clone the FastVLM repository
# 3. Download the 0.5B model by default
```

For more advanced options, see [MODELS.md](MODELS.md).

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
3. **Model Loading Failures**: Check model files with `tools/fastvlm_errors.py`
4. **Image Format Errors**: Ensure images are in supported formats (JPG, PNG)

For more detailed error diagnostics, run:
```bash
./tools/fastvlm_errors.py
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
./tests/test_fastvlm.sh

# Test vision analysis capabilities with JSON validation
./tests/test_vision_integrations.py

# Test JSON output formatting and validation (secure path handling)
./tools/json_test.sh
```

The test suite verifies:
- Metadata extraction functionality
- Duplicate file detection
- Content searching capabilities  
- File filtering with include/exclude patterns
- Vision model integration with JSON validation
- Performance metrics collection
- Path validation and enforcement
- Secure file operations with PathGuard

### Security Features in Tests

All test scripts implement robust security measures:

1. **Path Validation and Clean-up**: 
   - Strict validation of output paths before any file operations
   - Use of path guard pattern to prevent accidental writes to system directories
   - Safe directory cleaning with `find "$output_dir" -mindepth 1 -delete` instead of dangerous `rm -rf`
   - Multiple safety checks before performing destructive operations

2. **Output Directory Safety**:
   - Canonical artifact paths with automatic validation
   - Directory existence checks before all operations
   - Explicit rejection of empty paths, root paths, and system directories
   - Guards against path traversal attacks

## Using the Python Module Directly

```python
from src.analyzer import FileAnalyzer
from src.artifact_guard import get_canonical_artifact_path, PathGuard

# Get a canonical artifact path for output
output_dir = get_canonical_artifact_path("analysis", "my_analysis")

# Create analyzer with canonical output path
analyzer = FileAnalyzer("/path/to/analyze", output_dir=output_dir)

# Use PathGuard to enforce artifact discipline for all file operations
with PathGuard(output_dir):
    analyzer.extract_metadata()
    analyzer.find_duplicates()
    results = analyzer.get_results()
```

## Artifact Management

This project uses a strict artifact management system to prevent file sprawl and ensure consistent output locations. See [ARTIFACTS.md](ARTIFACTS.md) for details on the artifact system.

Key benefits:
- Consistent output paths with unique identifiers
- Runtime enforcement of path discipline
- Automatic manifest generation
- Centralized cleanup and management
- Protection against accidental writes to system directories
- Secure path validation to prevent path traversal vulnerabilities

## Contributing

### Adding New Features

When adding new capabilities to the File Analyzer system, please follow these conventions:

1. **Modular Design**: Add new analysis types as separate methods in the `FileAnalyzer` class.
2. **CLI Integration**: Update both `src/analyzer.py` and `tools/analyze.sh` with new options.
3. **Documentation**: Update the README.md with descriptions and examples of the new feature.
4. **Tests**: Add appropriate test cases in the tests directory.
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

### Project Structure

Please adhere to the following directory structure when contributing:

- `src/`: Core Python modules and libraries
- `tools/`: Command-line tools and developer utilities
- `tests/`: Test scripts and validation harnesses
- `artifacts/`: Output directory for all generated files

All Bash scripts must source artifact_guard_py_adapter.sh and follow the canonical path discipline.

### External Libraries

External libraries are stored in the `libs/` directory and should NEVER be modified directly. If changes are needed to library functionality, create wrapper functions instead.