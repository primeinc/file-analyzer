# FastVLM Integration Guide

This guide provides detailed information on using FastVLM with the File Analyzer system.

## Overview

FastVLM is Apple's efficient vision language model designed specifically for Apple Silicon. It provides high-quality image analysis with extremely fast performance compared to other vision language models.

Key features:
- **Fast Time-to-First-Token (TTFT)**: Up to 85x faster than competitors
- **Optimized for Apple Silicon**: Takes full advantage of Metal acceleration
- **Efficient Resource Usage**: Works well even with limited memory (1.5B model)
- **Multi-Resolution Support**: Optimized processing for different image types

## Installation

### Prerequisites

- Apple Silicon Mac (M-series chip)
- macOS Ventura or newer
- Python 3.8+

### Installation Steps

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

3. Download model weights (improved script with better error handling and partial download support):
   ```bash
   cd ml-fastvlm
   chmod +x get_models.sh
   ./get_models.sh
   ```

4. Verify model files were successfully extracted:
   ```bash
   ls -la ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3
   ```

### Troubleshooting Installation

If you encounter issues during installation:

1. Run the error diagnostics:
   ```bash
   ./fastvlm_errors.py
   ```

2. Common solutions:
   - Update MLX: `pip install -U mlx`
   - Install Pillow: `pip install Pillow`
   - Clear temporary files: `./fastvlm_errors.py`

## Usage

### Basic Usage

To analyze a single image:

```bash
./fastvlm_test.py --image path/to/image.jpg --prompt "Describe this image in detail."
```

To run the file analyzer with FastVLM vision model:

```bash
./file_analyzer.py --vision --vision-model fastvlm path/to/image.jpg
```

### Analysis Modes

FastVLM supports different analysis modes:

1. **Description Mode**: General image description (default)
   ```bash
   ./file_analyzer.py --vision --vision-model fastvlm --vision-mode describe image.jpg
   ```

2. **Object Detection**: Identifies and locates objects in images
   ```bash
   ./file_analyzer.py --vision --vision-model fastvlm --vision-mode detect image.jpg
   ```

3. **Document Analysis**: Extracts and formats text from documents
   ```bash
   ./file_analyzer.py --vision --vision-model fastvlm --vision-mode document document.jpg
   ```

### Batch Processing

For analyzing multiple images at once:

```bash
./file_analyzer.py --vision --vision-model fastvlm path/to/image/directory
```

### Benchmarking

To test FastVLM performance on your system:

```bash
./benchmark_fastvlm.py
```

The benchmark will test various image types and report performance metrics.

## Optimization

### Image Preprocessing

The system automatically preprocesses images for optimal performance:

- **Description Mode**: 512x512 resolution (default)
- **Object Detection**: 384x384 resolution
- **Document Analysis**: 768x768 resolution

### Model Selection

Different models can be used based on your requirements:

- **FastVLM-0.5B**: Fastest, uses least resources
- **FastVLM-1.5B**: Good balance of speed and quality (default)
- **FastVLM-7B**: Highest quality, requires more resources

To select a model:

```bash
./file_analyzer.py --vision --vision-model fastvlm \
  --model-path /path/to/custom/model path/to/image.jpg
```

## Integration with File Analyzer

The File Analyzer system is fully integrated with FastVLM:

```bash
./analyze.sh -V path/to/analyze
```

Command-line options:
- `-V, --vision`: Use vision model analysis
- `--vision-model fastvlm`: Specify FastVLM as the vision model
- `--vision-mode MODE`: Vision analysis mode (describe, detect, document)

## Performance Considerations

- **Memory Usage**: The 1.5B model requires approximately 7GB of RAM
- **GPU Acceleration**: Metal is automatically used for acceleration
- **Batch Size**: Processing multiple images is faster with batch processing

## Troubleshooting

Common issues and solutions:

1. **Out of Memory Errors**: Use a smaller model or reduce batch size
2. **Slow Performance**: Ensure Metal acceleration is enabled (`-ngl 1` flag)
3. **Model Loading Failures**: Check model files with `fastvlm_errors.py`
4. **Image Format Errors**: Ensure images are in supported formats (JPG, PNG)

For more detailed error diagnostics, run:

```bash
./fastvlm_errors.py
```

## Additional Resources

- [Official FastVLM Repository](https://github.com/apple/ml-fastvlm)
- [MLX Framework Documentation](https://github.com/ml-explore/mlx)
- [File Analyzer Documentation](README.md)