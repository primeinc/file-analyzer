# Model Analysis System

This document describes the model analysis system for the File Analyzer project.

## Overview

The model analysis system provides a unified interface for analyzing files using various AI models. It supports different model types (vision, text, etc.) and analysis modes (describe, detect, document), with a standardized output format and robust error handling.

## Architecture

The system consists of the following components:

### 1. Model Manager (`model_manager.py`)

The model manager is responsible for:
- Managing different model types and adapters
- Handling model discovery and initialization
- Providing a unified interface for model creation and prediction
- Supporting both single file analysis and batch processing

### 2. Model Analyzer (`model_analyzer.py`)

The model analyzer builds on the model manager to provide:
- High-level analysis capabilities for files and directories
- Result tracking and summarization
- Output formatting and artifact management
- Parallel processing for batch operations

### 3. Model Adapters

Model adapters are adapters for specific model types that implement the standard interface:
- `fastvlm_adapter.py`: Adapter for FastVLM vision models
- `mock_model_adapter.py`: Mock adapter for testing and development

Each adapter implements the same core interface, including:
- `__init__`: Initialize the model with configuration
- `predict`: Run prediction on input data
- `get_info`: Get information about the model

## Usage

### Command-Line Interface

The model analysis system includes a command-line interface for easy access:

```bash
# Analyze a single image with FastVLM
python src/model_analysis.py image.jpg --model fastvlm --mode describe

# Batch process a directory with FastVLM
python src/model_analysis.py images/ --batch --model fastvlm --mode detect

# Use a specific model size
python src/model_analysis.py image.jpg --model fastvlm --size 1.5b

# Custom prompt
python src/model_analysis.py image.jpg --prompt "Describe this technical diagram"

# Save output to specific file
python src/model_analysis.py image.jpg --output results.json

# Get model information
python src/model_analysis.py --list-models
```

### Integration with File Analyzer

The model analysis system integrates with the file analyzer (`analyzer.py`) to provide:
- Combined analysis with other analysis tools (metadata, duplicates, OCR, etc.)
- Unified output format and artifact management
- Standardized command-line interface

```bash
# Run file analyzer with vision model analysis
python src/analyzer.py image.jpg -V

# Specify model type and mode
python src/analyzer.py image.jpg -V --vision-model fastvlm --vision-mode detect
```

## Creating a Custom Model Adapter

To create a custom model adapter, follow these steps:

1. Create a new adapter file (e.g., `my_model_adapter.py`) that implements:
   - `MyModelAdapter` class with `__init__`, `predict`, and `get_info` methods
   - `create_adapter` function that returns an adapter instance

2. Register the adapter with the model manager:
   ```python
   from src.my_model_adapter import create_adapter
   manager = create_manager()
   manager.adapters["my_model"] = create_adapter
   ```

3. Use the adapter through the model analyzer:
   ```python
   analyzer = ModelAnalyzer()
   result = analyzer.analyze_file(
       "input.jpg",
       model_name="my_model",
       mode="describe"
   )
   ```

## Testing

The model analysis system includes a test suite to ensure proper functionality:
- `test_model_analyzer.py`: Tests for the model analyzer and model manager
- `mock_model_adapter.py`: Mock adapter for testing without actual models

To run the tests:
```bash
python tests/test_model_analyzer.py
```

## Artifact Management

The model analysis system strictly adheres to artifact discipline to ensure:
- All output files are stored in canonical paths
- File operations respect the project's artifact discipline
- Results are properly organized and labeled

Output files are stored in:
- Single file analysis: `/artifacts/vision/model_mode_TIMESTAMP/filename_result.json`
- Batch processing: `/artifacts/vision/batch_model_mode_TIMESTAMP/filename_mode.json`