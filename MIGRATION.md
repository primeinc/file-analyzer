# Migration Guide: Artifact Discipline

This document provides guidance for migrating from the Bash-based artifact discipline to the Python-based implementation.

## Quick Migration for Shell Scripts

For a quick, minimal-change migration of existing shell scripts, simply replace:

```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard.sh"
```

with:

```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
```

This adapter provides all the same functions as the original shell script while using the Python implementation under the hood:
- `get_canonical_artifact_path`
- `validate_artifact_path`
- Overridden commands: `mkdir`, `touch`, `cp`, `mv`

## Full Python Migration

For new scripts or complete rewrites, use the Python implementation directly:

```python
from src.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard,
    safe_copy,
    safe_mkdir,
    safe_write
)

# Create canonical artifact path
artifact_dir = get_canonical_artifact_path("test", "my_test_context")

# Use PathGuard to enforce discipline
with PathGuard(artifact_dir):
    # All file operations within this context will be validated
    with open(os.path.join(artifact_dir, "output.txt"), "w") as f:
        f.write("Test output")
```

## Python CLI Usage

For scripts that shell out to command-line operations, use the Python CLI:

```bash
# Create canonical artifact path
path=$(python src/artifact_guard_cli.py create test "my test context")

# Validate a path
python src/artifact_guard_cli.py validate "$path"
```

## Common Migration Patterns

### Shell Script Pattern 1: Creating artifact directories

**Before:**
```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard.sh"
ARTIFACT_DIR=$(get_canonical_artifact_path test "my_test")
mkdir -p "$ARTIFACT_DIR"
```

**After (adapter):**
```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
ARTIFACT_DIR=$(get_canonical_artifact_path test "my_test")
mkdir -p "$ARTIFACT_DIR"
```

**After (Python):**
```python
from src.artifact_guard import get_canonical_artifact_path, safe_mkdir
artifact_dir = get_canonical_artifact_path("test", "my_test")
```

### Shell Script Pattern 2: Writing to artifact files

**Before:**
```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard.sh"
ARTIFACT_DIR=$(get_canonical_artifact_path test "output_test")
echo "Test output" > "$ARTIFACT_DIR/output.txt"
```

**After (adapter):**
```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
ARTIFACT_DIR=$(get_canonical_artifact_path test "output_test")
echo "Test output" > "$ARTIFACT_DIR/output.txt"
```

**After (Python):**
```python
from src.artifact_guard import get_canonical_artifact_path, safe_write
artifact_dir = get_canonical_artifact_path("test", "output_test")
safe_write(os.path.join(artifact_dir, "output.txt"), "Test output")
```

### Shell Script Pattern 3: Copying files to artifacts

**Before:**
```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard.sh"
ARTIFACT_DIR=$(get_canonical_artifact_path test "copy_test")
cp source.txt "$ARTIFACT_DIR/copy.txt"
```

**After (adapter):**
```bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
ARTIFACT_DIR=$(get_canonical_artifact_path test "copy_test")
cp source.txt "$ARTIFACT_DIR/copy.txt"
```

**After (Python):**
```python
from src.artifact_guard import get_canonical_artifact_path, safe_copy
artifact_dir = get_canonical_artifact_path("test", "copy_test")
safe_copy("source.txt", os.path.join(artifact_dir, "copy.txt"))
```

## Enhanced Python Features

The Python implementation provides additional features not available in the shell script:

- **PathGuard Context Manager**: For enforcing discipline within a block
- **Decorators (@enforce_path_discipline)**: For function-level enforcement
- **Rich Error Messages**: More detailed error information
- **Artifact Cleanup**: Programmatic cleanup of old artifacts
- **Safe File Operations**: Built-in utilities for common operations

For more details, see the [Python Artifact Discipline](PYTHON_ARTIFACT_DISCIPLINE.md) documentation.