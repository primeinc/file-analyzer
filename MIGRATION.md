# Project Restructuring and Artifact Management Migration

This document outlines the plan for restructuring the project and migrating to a strict artifact management system.

## Current Implementation Status

- ✅ Artifact guard system for runtime path enforcement (Bash)
- ✅ Artifact guard system for Python modules (src/artifact_guard.py)
- ✅ Preflight check script with strict validation
- ✅ Canonical path structure with unique IDs
- ✅ Machine-readable manifest for each artifact
- ✅ Script validation tool (check_script_conformity.sh)
- ✅ End-to-end test for Python artifact discipline
- ✅ Secure path handling in all test scripts
- ✅ Enhanced security for file operations in Python modules
- ✅ System directory protection in artifact_guard
- ⏳ Git pre-commit hook enforcement (pending)
- ⏳ CI workflow validation (pending)
- ✅ Project directory restructuring (completed)

## Directory Structure Changes

We are reorganizing the project into a cleaner, more maintainable structure:

```
repo-root/
│
├── artifact_guard.sh           # Bash enforcement: sourced by ALL Bash scripts
├── preflight.sh                # Bash: must run before any tests/dev script
├── cleanup.sh                  # Bash: artifact cleaning & check
├── MIGRATION.md
├── migrate_artifacts.sh        # TEMP (delete after migration)
├── README.md
├── .githooks/
│   └── pre-commit
├── .github/
│   └── workflows/
│       └── artifact-discipline.yml
│
├── artifacts/                  # Canonical artifact storage, never manually created or modified
│   ├── analysis/
│   ├── test/
│   ├── vision/
│   ├── benchmark/
│   └── tmp/
│
├── src/                        # Core source code (Python modules and main business logic)
│   ├── __init__.py
│   ├── analyzer.py
│   ├── vision.py
│   └── ...                     # All real libraries go here
│
├── tools/                      # All command-line tools, CLI wrappers, and developer utilities
│   ├── analyze.sh
│   ├── analyze.py
│   ├── vision_test.sh
│   ├── vision_test.py
│   ├── run_fastvlm_tests.sh
│   └── ...                     # Any hybrid Python/Bash dev tool or wrapper script
│
└── tests/                      # All test scripts, fixtures, and validation harnesses (NO utility scripts here)
    ├── test_analyzer.sh
    ├── test_analyzer.py
    ├── test_vision.sh
    ├── test_vision.py
    ├── strict_example.sh
    └── test_path_enforcement.sh
```

## Migration Phases

### Phase 1: Structure Creation and Core Files (Current)

1. Create the new directory structure
2. Update artifact_guard.sh to handle restructuring
3. Create pre-commit hook for enforcement
4. Update ARTIFACTS.md documentation

### Phase 2: Source Code Migration (Next Week)

1. Move Python modules to `/src/`
2. Update import statements and paths
3. Create an `__init__.py` to establish module structure
4. Verify Python modules work after migration

### Phase 3: Tools and Test Migration (Week 2)

1. Move CLI tools and wrappers to `/tools/`
2. Move test scripts to `/tests/`
3. Update all scripts to source artifact_guard.sh
4. Fix paths and imports in all scripts

### Phase 4: Canonical Paths Enforcement (Week 3)

1. Update all Bash scripts to use get_canonical_artifact_path
2. Update Python scripts to use canonical artifact paths
3. Run validation tests to ensure everything works

### Phase 5: Legacy Cleanup (Week 4)

1. Identify all legacy files and directories
2. Move legacy content to archives if needed
3. Remove unused files and directories
4. Update README.md and documentation

## File Migration Plan

| Original Location | New Location | File Type |
|-------------------|-------------|-----------|
| file_analyzer.py | src/analyzer.py | Core module |
| vision_analyzer.py | src/vision.py | Core module |
| json_utils.py | src/json_utils.py | Core module |
| analyze.sh | tools/analyze.sh | CLI tool |
| run_fastvlm_tests.sh | tools/run_fastvlm_tests.sh | Dev utility |
| test_vision.sh | tools/vision_test.sh | Dev utility |
| test_json_output.sh | tools/json_test.sh | Dev utility |
| test_path_enforcement.sh | tests/test_path_enforcement.sh | Test harness |
| strict_example_test.sh | tests/strict_example.sh | Test harness |
| test_*.py | tests/ | Test harnesses |

## Script Migration Process

For each script:

1. Add the guard integration:
   ```bash
   # Source artifact guard for path enforcement
   source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard.sh"
   ```

2. Replace directory creation:
   ```bash
   # Old: 
   # output_dir="analysis_results/vision_test_$(date +%Y%m%d_%H%M%S)"
   # mkdir -p "$output_dir"
   
   # New:
   TEST_DIR=$(get_canonical_artifact_path test "vision_test")
   ```

3. Use unique context strings for artifact paths:
   ```bash
   ANALYSIS_DIR=$(get_canonical_artifact_path analysis "vision_$(basename "$image_path")")
   ```

4. Update all file paths to use the canonical directories:
   ```bash
   # Old: echo "Output" > "$output_dir/results.txt"
   # New: echo "Output" > "$TEST_DIR/results.txt"
   ```

## Python Artifact Path Discipline

The Python implementation of artifact path discipline (`src/artifact_guard.py`) provides the same functionality as the Bash version:

1. **Canonical Path Generation**: `get_canonical_artifact_path()` creates unique, consistently structured output directories with manifests.

2. **Path Validation**: `validate_artifact_path()` verifies paths against the canonical structure rules and prevents writes to system directories.

3. **Runtime Enforcement**: `PathGuard` context manager overrides Python's built-in `open()` function to intercept and validate file operations, preventing writes outside the artifact directory structure.

4. **Manifest Generation**: Automatically creates JSON manifests with metadata for each artifact.

### Key Features

- **Transparent Integration**: Most modules can simply import and use `get_canonical_artifact_path` without other changes.
- **Comprehensive Protection**: Detects and prevents all file write operations to non-canonical locations.
- **Helpful Error Messages**: When path discipline is violated, provides clear errors with suggestions.
- **Compatible API**: Uses the same argument structure as the Bash implementation for consistency.
- **System Directory Protection**: Explicitly prevents writing to system directories like /tmp or /var.

### End-to-End Testing

A comprehensive test suite (`tests/test_artifact_discipline.py`) validates:
- Canonical path generation in Python modules
- Path validation and rejection of invalid paths
- Runtime enforcement via PathGuard
- Output file creation in proper artifact directories
- Module import compatibility

## Strict Enforcement Rules

1. **All Bash scripts must**:
   - Source artifact_guard.sh immediately after the shebang
   - Use get_canonical_artifact_path for all artifact paths
   - No direct mkdir/touch/cp/mv to non-canonical artifact paths

2. **All Python scripts must**:
   - Import `get_canonical_artifact_path` from src.artifact_guard
   - Use only canonical artifact paths for all file outputs
   - No manually created directories
   - Use PathGuard context manager to enforce discipline:
     ```python
     # Example for using PathGuard to enforce discipline
     from src.artifact_guard import get_canonical_artifact_path, PathGuard
     
     # Get a canonical path for output
     output_dir = get_canonical_artifact_path("analysis", "example_analysis")
     
     # Use PathGuard to enforce all file operations within a block
     with PathGuard(output_dir):
         # All file operations in this block are validated
         with open(os.path.join(output_dir, "results.json"), "w") as f:
             json.dump(results, f, indent=2)
     ```

3. **Pre-commit Enforcement**:
   - Block commits with legacy path patterns
   - Block commits with scripts not sourcing artifact_guard.sh
   - No "soft transition" flags allowed

## CI/CD Integration

1. **Pull Request Checks**
   - Enforce artifact discipline in pull request builds
   - Block PRs that add non-canonical artifact code

2. **Build Pipeline Steps**
   - Add preflight check as first step in pipeline
   - Set `ARTIFACTS_ROOT` explicitly in CI environment
   - Clean up after test runs

3. **Reporting and Auditing**
   - Add artifact manifest verification
   - Report artifact disk usage in CI summary

## Risk Mitigation

- Add `--no-enforce` flag to preflight.sh for emergency bypasses
- Established rollback procedure in case of CI failures
- Document migration status for all scripts in `scripts-status.json`

## Success Criteria

- All scripts use canonical artifact paths
- No legacy directories exist in the codebase
- All artifacts have machine-readable manifests
- CI pipeline enforces discipline
- Git pre-commit hook prevents regressions
- Project structure follows the defined organization
- All modules and scripts work correctly after restructuring

## Implementation Notes and Findings

The implementation of Python artifact discipline revealed several important insights:

### Critical Path Verification Issues

1. **System Directory Protection**: The initial implementation incorrectly allowed writing to system directories like `/tmp`. This was fixed by explicitly rejecting system directories in `validate_artifact_path()`:

   ```python
   # Special case for system directories that should NEVER be valid for artifact output
   system_temp_dirs = ['/tmp/', tempfile.gettempdir()]
   if any(abs_path.startswith(d) for d in system_temp_dirs):
       # We explicitly reject temp directories for artifacts
       return False
   ```

2. **PathGuard Implementation**: The initial PathGuard implementation had issues with function reference handling that were fixed by:
   - Using direct `import builtins` instead of `sys.modules['builtins']`
   - Adding proper error context in the ValidationError
   - Ensuring proper cleanup in the context manager's exit method

3. **Module Import Issues**: Tool modules in separate directories needed special handling to import from src/. This was solved by:
   - Adding project root to sys.path
   - Using explicit and consistent import paths
   - Providing proper examples in documentation

### Security Boundaries

1. **Temporary Directory Escapes**: By default, Python utilities often use `/tmp` for temporary storage, which would bypass our artifact discipline. We now:
   - Explicitly check and reject any paths under system temp directories
   - Provide a canonical `get_canonical_artifact_path("tmp", "context")` alternative for temporary files

2. **Subprocess Output Validation**: When running external processes, their output locations need to be constrained to canonical paths:
   ```python
   # Create a canonical artifact path for the output
   output_dir = get_canonical_artifact_path("analysis", "subprocess_output")
   
   # Run the subprocess with output going to the canonical location
   result = subprocess.run(
       ["external_tool", "--input", input_file, "--output", os.path.join(output_dir, "result.txt")],
       check=True
   )
   ```

3. **External Libraries**: Libraries that create their own temporary files or output directories may bypass our controls. These should be:
   - Configured to use our canonical paths when possible
   - Monitored for escape attempts
   - Wrapped in utility functions that enforce our discipline

4. **Critical Shell Script Security Fixes**:
   - Eliminated dangerous `rm -rf $output_dir/*` patterns that could cause catastrophic data loss if $output_dir is empty
   - Replaced with safer alternatives like `find "$output_dir" -mindepth 1 -delete`
   - Added multiple safety checks before any destructive operations:
     ```bash
     # Safety check - NEVER continue if output_dir is empty
     if [ -z "$output_dir" ] || [ "$output_dir" = "/" ]; then
         echo "ERROR: Invalid or empty output directory path. Aborting for safety."
         exit 1
     fi
     
     # Verify the path is under artifacts directory before cleaning
     if [[ "$output_dir" == *"/artifacts/"* ]]; then
         # Clean directory to start fresh safely
         mkdir -p "$output_dir"
         find "$output_dir" -mindepth 1 -delete
     else
         echo "ERROR: Output directory is not in artifacts. Aborting for safety."
         exit 1
     fi
     ```
   - Implemented strict path validation for all file operations

5. **Platform-Specific Timeout Handling**:
   - Implemented unified timeout mechanism that works across all platforms
   - Windows-specific solution using subprocess timeout parameter
   - Unix/Linux/macOS solution using the `timeout` command:
     ```python
     if platform.system() != "Windows":
         full_cmd = ["timeout", str(timeout_seconds)] + cmd
         result = subprocess.run(full_cmd, capture_output=True, text=True)
         if result.returncode == 124:
             raise subprocess.TimeoutExpired(cmd, timeout_seconds)
     else:
         result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
     ```
   - Consistent error handling for timeout conditions

### End-to-End Testing Methodology

Our comprehensive test (`tests/test_artifact_discipline.py`) covers:

1. **Component Tests**:
   - Canonical path generation validation
   - Path validation for valid and invalid paths
   - PathGuard enforcement with proper error messages

2. **Integration Tests**:
   - Core library functions (VisionAnalyzer, etc.) using canonical paths
   - Module import compatibility
   - Default fallback to canonical paths when none specified

3. **Failure Mode Tests**:
   - Attempts to write outside canonical paths are caught
   - System directory protections work as expected
   - Non-canonical paths are properly detected and rejected

This testing methodology provides confidence that the Python artifact discipline is consistently enforced throughout the codebase.

## Modules Updated for Artifact Discipline

The following Python modules now fully enforce artifact discipline:

1. **src/vision.py**:
   - Uses canonical artifact paths for all outputs
   - Uses PathGuard to enforce discipline
   - Validates all output paths
   - Provides automatic fallback to canonical paths

2. **tools/fastvlm_json.py**:
   - Imports artifact_guard properly
   - Uses canonical paths for all outputs
   - Warns if user provides non-canonical output paths

Future work will extend this to all remaining Python modules in the codebase.