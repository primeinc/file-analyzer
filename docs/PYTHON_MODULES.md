# Python Module Structure

This document outlines the Python module structure for the File Analyzer project.

## Module Organization

The code is organized into the following package structure:

```
src/
├── cli/                # Command-line interface components
│   ├── analyze/        # File analysis commands
│   ├── artifact/       # Artifact management commands
│   ├── benchmark/      # Benchmarking tools and utilities
│   ├── common/         # Shared CLI utilities
│   ├── install/        # Installation utilities
│   ├── model/          # Model management CLI tools
│   ├── test/           # Testing utilities
│   └── validate/       # Validation utilities
├── core/               # Core functionality
│   ├── analyzer.py     # Main file analyzer implementation
│   ├── artifact_guard.py # Artifact path discipline
│   └── vision.py       # Vision processing utilities
├── models/             # Model management
│   ├── fastvlm/        # FastVLM model implementation
│   ├── analysis.py     # Model analysis utilities
│   ├── analyzer.py     # Model analyzer implementation
│   ├── config.py       # Model configuration
│   ├── manager.py      # Model management
│   └── mock_adapter.py # Mock model adapter for testing
└── utils/              # Utility functions
    ├── json_parser.py  # JSON parsing utilities
    └── json_utils.py   # JSON utilities
```

## Module Descriptions

### CLI Components (src/cli/)

The CLI components provide a command-line interface for the File Analyzer functionality, using Typer for command registration and Rich for formatted output.

- **analyze**: Commands for analyzing files and directories
- **artifact**: Commands for managing artifact directories and outputs
- **benchmark**: Commands for benchmarking model performance
- **common**: Shared utilities for CLI components
- **install**: Installation utilities
- **model**: Model management commands
- **test**: Testing utilities
- **validate**: Validation utilities

### Core Functionality (src/core/)

The core functionality provides the fundamental operations of the File Analyzer system.

- **analyzer.py**: Main implementation of the file analyzer
- **artifact_guard.py**: Artifact path discipline and validation
- **vision.py**: Vision processing utilities

### Models (src/models/)

The models package manages different model implementations and provides a unified interface for model operations.

- **fastvlm/**: FastVLM model implementation
- **analysis.py**: Model analysis utilities
- **analyzer.py**: Model analyzer implementation
- **config.py**: Model configuration
- **manager.py**: Model management
- **mock_adapter.py**: Mock model adapter for testing

### Utilities (src/utils/)

The utilities package provides common utilities used throughout the system.

- **json_parser.py**: JSON parsing utilities
- **json_utils.py**: JSON utilities

## Command Structure

The File Analyzer CLI provides the following commands:

```
fa                     # Main command
├── analyze            # Analyze files and directories
│   ├── all            # Run all analyses
│   ├── metadata       # Extract metadata
│   ├── duplicates     # Find duplicates
│   ├── ocr            # Perform OCR on images
│   ├── virus          # Scan for malware
│   ├── search         # Search content
│   ├── binary         # Analyze binary files
│   ├── vision         # Analyze images with AI
│   └── verify         # Verify installation
├── artifact           # Manage artifact directories
│   ├── setup          # Set up artifact structure
│   ├── clean          # Clean up old artifacts
│   ├── clean-tmp      # Clean temporary artifacts
│   ├── check          # Check for artifact sprawl
│   ├── info           # Show information
│   ├── path           # Get canonical artifact path
│   ├── validate       # Validate a path
│   ├── env            # Print environment variables
│   ├── env-file       # Generate environment file
│   └── script-checks  # Check shell scripts
│       ├── check      # Check a specific script
│       └── all        # Check all scripts
├── benchmark          # Benchmark utilities
│   ├── run            # Run model benchmarks
│   ├── images         # Manage benchmark images
│   └── samples        # Generate sample data
│       ├── generate   # Generate benchmark samples
│       └── cache      # Manage sample cache
├── model              # Model management
│   ├── list           # List available models
│   └── download       # Download models
├── test               # Testing utilities
│   ├── json           # JSON validation tests
│   ├── fastvlm        # FastVLM tests
│   └── hook           # Test hook for CI/pre-commit
└── validate           # Validation utilities
    └── json           # Validate JSON files
```

## Usage Examples

### Analyzing Files

```bash
# Run all analyses on a directory
fa analyze all /path/to/files

# Extract metadata from files
fa analyze metadata /path/to/files

# Find duplicates in a directory
fa analyze duplicates /path/to/files

# OCR images in a directory
fa analyze ocr /path/to/files

# Search for content
fa analyze search "search text" /path/to/files

# Analyze images with AI
fa analyze vision /path/to/images
```

### Managing Artifacts

```bash
# Set up artifact directory structure
fa artifact setup

# Clean up old artifacts
fa artifact clean --days 7

# Clean temporary artifacts
fa artifact clean-tmp

# Check for artifact sprawl
fa artifact check

# Get a canonical artifact path
fa artifact path test "my test context"
```

### Model Management

```bash
# List available models
fa model list

# Download a model
fa model download 0.5b
```

### Benchmarking

```bash
# Run benchmarks
fa benchmark run

# Generate benchmark samples
fa benchmark samples generate
```