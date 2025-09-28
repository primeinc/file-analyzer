# Python Artifact Discipline

This document describes the Python implementation of artifact path discipline for the File Analyzer project.

## Migration from Bash to Python

The Python implementation provides a complete replacement for the bash-based `artifact_guard.sh` with improved error handling, better performance, and richer functionality. It serves as the **single source of truth** for artifact path discipline in this project.

## Key Components

The implementation consists of several key components:

1. **Core Module**: `src/artifact_guard.py` - The main implementation with path generation, validation, and utilities
2. **CLI Tool**: `src/artifact_guard_cli.py` - Command-line interface for artifact management
3. **Bash Adapter**: `artifact_guard_py_adapter.sh` - Compatibility layer for existing shell scripts

## Key Features

- **Canonical Path Generation**: Create standard, timestamped paths for artifacts
- **Path Validation**: Ensure paths conform to project standards
- **Runtime Enforcement**: Intercept and validate file operations
- **Safe File Operations**: Built-in utilities for safe file handling
- **Artifact Cleanup**: Manage retention of artifacts
- **Extensible Design**: Decorators and context managers for enforcement

## Usage

### Python Usage

```python
from src.artifact_guard import get_canonical_artifact_path, PathGuard

# Create canonical artifact path
artifact_dir = get_canonical_artifact_path("test", "my_test_context")

# Use PathGuard to enforce discipline
with PathGuard(artifact_dir):
    # All file operations within this context will be validated
    with open(os.path.join(artifact_dir, "output.txt"), "w") as f:
        f.write("Test output")
```

### CLI Usage

```bash
# Create canonical artifact path
path=$(python src/artifact_guard_cli.py create test "my test context")

# Validate a path against artifact discipline
python src/artifact_guard_cli.py validate /path/to/validate

# Clean up old artifacts
python src/artifact_guard_cli.py cleanup --days 7 --type test

# Set up artifact directory structure
python src/artifact_guard_cli.py setup

# Show information about artifact discipline
python src/artifact_guard_cli.py info
```

### Bash Adapter Usage

For existing shell scripts that source `artifact_guard.sh`, you can replace it with the Python-based adapter:

```bash
# Replace this line:
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard.sh"

# With this line:
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
```

The adapter provides the same functions as the original shell script:
- `get_canonical_artifact_path`: Generate a canonical artifact path
- `validate_artifact_path`: Validate a path against discipline
- Overridden shell commands: `mkdir`, `touch`, `cp`, `mv`

## Path Enforcement Methods

The module provides several ways to enforce path discipline:

1. **PathGuard Context Manager**: For temporary enforcement during a block of code
   ```python
   with PathGuard(artifact_dir):
       # File operations here are guarded
   ```

2. **@enforce_path_discipline Decorator**: For function-level enforcement
   ```python
   @enforce_path_discipline
   def write_data(output_file, data):
       with open(output_file, 'w') as f:
           f.write(data)
   ```

3. **Safe File Operations**: Pre-built functions with enforcement
   ```python
   # These automatically enforce path discipline
   safe_mkdir(directory)
   safe_write(file_path, content)
   safe_copy(source, destination)
   ```

## Testing

The implementation includes comprehensive tests:
- `tests/test_artifact_discipline.py`: End-to-end tests
- `tests/test_artifact_discipline_unittest.py`: Unittest-based tests
- `tests/verify_python_artifact_guard.py`: Verification of the full implementation

To run the tests:
```bash
python tests/verify_python_artifact_guard.py
```

## Migration Plan

The following steps outline the migration from shell scripts to Python:

1. **Immediate Replacement**:
   - Deploy `artifact_guard_py_adapter.sh` as a drop-in replacement for existing scripts

2. **Gradual Migration**:
   - Update tools and scripts to use Python implementation directly
   - Remove shell script dependencies in tools

3. **Complete Migration**:
   - All scripts use Python implementation
   - Remove `artifact_guard_py_adapter.sh`

## Benefits of Python Implementation

- **Robust Error Handling**: Better error messages and handling of edge cases
- **Cross-Platform Compatibility**: Works on all platforms that support Python
- **Extensibility**: Easier to add new features
- **Performance**: More efficient path validation and enforcement
- **Testing**: Comprehensive unittest-based testing
- **Simpler Maintenance**: Single source of truth for path discipline

## Artifact Types and Structure

The system supports the following artifact types:
- `analysis`: Analysis results
- `vision`: Vision model outputs
- `test`: Test outputs
- `benchmark`: Performance benchmarks
- `tmp`: Temporary files (auto-cleaned)

## Retention Policy

Artifacts are managed according to retention policies defined in their manifest files. By default, artifacts are retained for 7 days. You can clean up old artifacts using:

```bash
python src/artifact_guard_cli.py cleanup --days 7
```