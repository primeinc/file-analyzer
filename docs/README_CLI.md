# File Analyzer CLI Documentation

The File Analyzer CLI (`fa`) is a unified command-line interface for comprehensive file analysis. It combines multiple specialized tools and provides a modular, extensible architecture for managing file analysis operations.

## Installation

```bash
# Install from the project directory
pip install -e .

# Or install with specific dependencies for vision features
pip install -e ".[vision]"
```

## Basic Usage

```bash
# Run all analyses on a directory
fa analyze all /path/to/analyze

# Extract metadata from files
fa analyze metadata /path/to/analyze

# Find duplicate files
fa analyze duplicates /path/to/directory

# Perform OCR on images
fa analyze ocr /path/to/images

# Scan for malware
fa analyze virus /path/to/files

# Search file contents
fa analyze search "search text" /path/to/files

# Analyze binary files
fa analyze binary /path/to/file

# Analyze images with AI vision models
fa analyze vision --model fastvlm --mode describe /path/to/image
```

## Command Structure

The CLI is organized into subcommands, each with its own set of options:

- `fa analyze`: Run file analysis operations
- `fa test`: Run test suites and validation checks
- `fa validate`: Validate file analysis outputs

Each subcommand has additional subcommands and options. Use `--help` with any command to see available options:

```bash
fa --help
fa analyze --help
fa test --help
fa validate --help
```

## Common Options

These options are available for all commands:

```bash
--verbose, -v         Enable verbose output
--quiet, -q           Suppress all output except errors
--ci                  Run in non-interactive CI mode (disables progress bars)
--log-json            Output logs in JSON format
--log-file PATH       Path to log file
--no-color            Disable colored output
--version             Show version and exit
```

## Testing and Validation

The CLI provides built-in testing and validation capabilities:

```bash
# Run all tests
fa test run

# List available tests
fa test list

# Run a specific test
fa test run fastvlm.basic

# Run FastVLM tests with mock model
fa test fastvlm --mock

# Run JSON validation tests
fa test json --mock

# Validate a JSON file against a schema
fa validate schema output.json --type fastvlm

# Compare two images
fa validate images image1.png image2.png --method pixel

# Validate analysis artifacts
fa validate run /path/to/artifacts --type fastvlm
```

## Extensibility

The CLI is designed to be extensible through setuptools entry points. You can add new commands, tests, or validators by creating Python packages that register entry points:

```python
# setup.py or pyproject.toml
entry_points={
    'fa.commands': [
        'mycommand = my_package.my_module:app',
    ],
    'fa.tests': [
        'mytest = my_package.test_module:run_test',
    ],
}
```

## Architecture Overview

The File Analyzer CLI follows a modular architecture:

1. **Main CLI Entry Point** (`src/cli/main.py`):
   - Provides the `fa` command and global options
   - Discovers and loads subcommands via entry points
   - Configures logging and environment

2. **Subcommand Modules**:
   - `src/cli/analyze/`: File analysis commands
   - `src/cli/test/`: Test execution framework
   - `src/cli/validate/`: Validation tools

3. **Configuration Management** (`src/cli/common/config.py`):
   - Centralizes configuration from multiple sources
   - Manages model paths and artifact directories
   - Handles schema validation

4. **Shared Utilities**:
   - Artifact management with `src/artifact_guard.py`
   - Model configuration with `src/model_config.py`
   - JSON schema validation with schemas in `schemas/`

## JSON Schemas

The system includes versioned JSON schemas for validating outputs:

- `schemas/fastvlm/`: Schemas for FastVLM model outputs
- `schemas/analyzer/`: Schemas for file analyzer outputs
- `schemas/validate/`: Schemas for validation reports

Schemas are versioned (e.g., `v1.0`, `v1.1`) for backward compatibility.

## Environment Variables

The CLI respects the following environment variables:

- `FA_MODEL_DIR`: Base directory for model files
- `FA_CONFIG_FILE`: Path to configuration file
- `FA_LOG_LEVEL`: Default logging level
- `FA_ARTIFACT_DIR`: Base directory for artifacts

## Contributing

To contribute to the CLI:

1. Create a new branch for your changes
2. Add or modify functionality in the appropriate module
3. Write tests for your changes
4. Update documentation if necessary
5. Create a pull request

For adding new subcommands or plugins, see the section on Extensibility above.