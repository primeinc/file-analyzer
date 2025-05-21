# Artifact Management System

This project employs a strict artifact management system to prevent uncontrolled sprawl of test outputs, results, and temporary files.

## Key Benefits

- **Clean Repository Structure**: No more timestamped directories scattered throughout the repo
- **Consistent Locations**: Predictable paths for all artifacts by type
- **Enforced Discipline**: Runtime enforcement of canonical artifact paths
- **Automatic IDs**: Unique identifiers with commit hash, timestamp, and context
- **Metadata Tracking**: Automatic manifest generation for all artifacts

## Mandatory Requirements

Every script MUST follow these non-negotiable requirements:

1. **Source the Guard**: All bash scripts MUST source artifact_guard_py_adapter.sh immediately after shebang
   ```bash
   #!/bin/bash
   source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"
   ```

2. **Use Canonical Paths Only**: All artifacts MUST use paths from get_canonical_artifact_path
   ```bash
   # Get a unique canonical path with auto-generated ID
   TEST_DIR=$(get_canonical_artifact_path test "my_test_context")
   ```

3. **No Manual Paths**: NO direct mkdir/touch/cp/mv to non-canonical artifact paths
   ```bash
   # This will fail if outside canonical structure:
   mkdir -p test_output_dir  # WILL FAIL
   touch my_results.txt      # WILL FAIL
   
   # This will work:
   mkdir -p "$TEST_DIR/subdirectory"  # Works because TEST_DIR is canonical
   touch "$TEST_DIR/results.txt"      # Works because TEST_DIR is canonical
   ```

## Directory Structure

```
artifacts/
├── analysis/  - Analysis results (metadata, duplicates, etc.)
├── vision/    - Vision model outputs
├── test/      - Test results and validation
├── benchmark/ - Performance benchmarks
├── tmp/       - Temporary files (auto-cleaned)
```

## Using the System

### Getting Canonical Artifact Paths

The only supported method for creating artifact directories:

```bash
# Get a canonical artifact path for test output
TEST_DIR=$(get_canonical_artifact_path test "descriptive_context")

# Get a canonical artifact path for analysis results
ANALYSIS_DIR=$(get_canonical_artifact_path analysis "meaningful_context")

# Get a canonical artifact path for temporary files
TMP_DIR=$(get_canonical_artifact_path tmp "temp_context")
```

### Path Structure and Identifiers

Canonical paths follow a consistent pattern:

```
artifacts/<type>/<context>_<git_hash>_<job_id>_<pid>_<timestamp>/
```

Example:
```
artifacts/test/path_enforcement_c0451da_local_will_22787_20250520_223409/
```

### Manifest Files

Each canonical artifact directory automatically includes a manifest.json file:

```json
{
  "created": "2025-05-20T22:34:09Z",
  "owner": "will",
  "git_commit": "c0451da",
  "ci_job": "local_will",
  "pid": "22787",
  "retention_days": 7,
  "context": {
    "script": "test_path_enforcement.sh",
    "full_path": "/Users/will/Dev/file-analyzer/test_path_enforcement.sh",
    "description": "path_enforcement_test"
  }
}
```

## Validation and Compliance

### Testing Path Enforcement

Use test_path_enforcement.sh to verify correct enforcement behavior:

```bash
./test_path_enforcement.sh
```

### Checking Script Conformity

Use check_script_conformity.sh to ensure all scripts source artifact_guard_py_adapter.sh:

```bash
./check_script_conformity.sh
```

### Example Script

For a complete example of the required pattern, see:

```bash
./strict_example_test.sh
```

## Security and Limitations

### Enhanced Security Features

The artifact management system now includes several enhanced security features:

1. **System Directory Protection**: 
   - Explicitly prevents writing to system directories like `/tmp`, `/var`, etc.
   - Rejects any path outside the artifacts directory structure
   - Guards against path traversal attacks

2. **Safe Directory Operations**:
   - Replaced dangerous `rm -rf` patterns with safer alternatives
   - Multiple safety checks before any destructive operations
   - Validation of paths before operations

3. **Cross-Platform Security**:
   - Consistent path validation across all platforms
   - Platform-specific implementations for subprocess handling
   - Same security guarantees on Windows, macOS, and Linux

4. **Python PathGuard Integration**:
   - Runtime interception of file operations
   - Validation of all file paths
   - Prevention of writes to non-canonical locations

### Current Limitations

- **No Redirection Guarding**: I/O redirection (>, >>) is not guarded automatically
- **No Multi-language Support**: Only Bash and Python are fully guarded (not other languages)
- **Not Self-Protected**: The artifact guard system itself doesn't protect system binaries

### Best Practices

1. Always use `get_canonical_artifact_path` for ALL artifact paths
2. Maintain subdirectories within canonical paths if needed
3. Use the TMP artifact type for ephemeral files 
4. Include descriptive context strings for better organization
5. Never bypass the enforcement system
6. Use PathGuard context manager for Python file operations
7. Always validate paths before destructive operations
8. Check if directories or paths are empty before attempting to use them
9. Use `find "$dir" -mindepth 1 -delete` instead of `rm -rf "$dir"/*`