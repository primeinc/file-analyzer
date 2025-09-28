# Model Management System

This document describes the model management system for the File Analyzer project.

## Overview

The model management system is designed to:

1. Provide a centralized location for storing and accessing AI model files
2. Prevent large model files from being committed to the git repository
3. Automate model discovery, download, and validation
4. Support both development and CI/CD environments
5. Enforce proper artifact discipline for model outputs

## Model Storage Locations

Models are stored in the following locations, in order of precedence:

1. **User-level storage** (preferred): `~/.local/share/fastvlm/`
   - Location for permanent model storage
   - Shared across multiple projects
   - Not affected by git operations

2. **Project-level storage**: `libs/ml-fastvlm/checkpoints/`
   - Intended for development and testing
   - Not committed to git (excluded by .gitignore)

3. **Alternative storage**: `checkpoints/`
   - Legacy location, provided for backward compatibility

## Supported Models

The system currently supports the following models:

| Model   | Sizes      | Description                      | Approx Size |
|---------|------------|----------------------------------|-------------|
| FastVLM | 0.5b       | Small model for testing          | 1 GB        |
| FastVLM | 1.5b       | Medium model for general use     | 3 GB        |
| FastVLM | 7b         | Large model for best performance | 14 GB       |

## Usage

### Setting Up the Environment

1. Run the setup script to prepare the environment:

```bash
./tools/setup_fastvlm.sh
```

This script will:
- Install required dependencies (MLX)
- Clone the ml-fastvlm repository if needed
- Set up the model paths and configuration

### Managing Models

1. **List available models**:

```bash
python tools/download_models.py list
```

2. **Get model information**:

```bash
python tools/download_models.py info --size 0.5b
```

3. **Download a model**:

```bash
python tools/download_models.py download --size 0.5b
```

4. **Download all models**:

```bash
python tools/download_models.py download --size all
```

### Using Models in Your Code

The `src/fastvlm_adapter.py` module provides a unified interface for using models:

```python
from src.fastvlm_adapter import create_adapter

# Create and initialize the adapter
adapter = create_adapter(model_type="fastvlm", model_size="0.5b")

# Use the model
result = adapter.predict(image_path="path/to/image.jpg", 
                         prompt="Describe this image.",
                         mode="describe")
```

### Command-line Interface

You can also use the adapter directly from the command line:

```bash
python src/fastvlm_adapter.py --image path/to/image.jpg --size 0.5b --mode describe
```

## CI/CD Integration

The model management system is integrated with GitHub Actions for CI/CD:

1. Models are cached between workflow runs to avoid redundant downloads
2. The smallest model size (0.5b) is used for CI/CD by default
3. The setup-dependencies workflow handles dependency and model setup
4. The model cache is identified by a hash of the model configuration file

## Development Workflow

When developing with FastVLM models:

1. Run `./tools/setup_fastvlm.sh` to set up the environment
2. Download the smallest model for development: `python tools/download_models.py download --size 0.5b`
3. Use the adapter API for model access: `from src.fastvlm_adapter import create_adapter`
4. Store model outputs in canonical artifact paths: `get_canonical_artifact_path("vision", "model_output")`

## Best Practices

1. Use the smallest model (0.5b) for development and testing
2. Only download larger models when needed for production-quality results
3. Always use the adapter API rather than direct model access
4. Ensure all model outputs are stored in canonical artifact paths
5. Don't forget to check available disk space before downloading models

## Troubleshooting

If you encounter issues with the model management system:

1. Check if MLX is installed: `pip install mlx`
2. Verify the model directories exist: `python tools/download_models.py list`
3. Run the test script: `./tests/test_fastvlm.sh`
4. Check the logs in the canonical artifact path: `artifacts/tmp/model_download_*/download.log`
5. Try downloading the model manually: `python tools/download_models.py download --size 0.5b --force`