# Artifact Structure

This directory contains all outputs and artifacts produced by the file analyzer system.

## Structure Types

The artifact system supports two complementary approaches for organizing outputs:

### 1. Automated Canonical Paths (Recommended)

When using the `get_canonical_artifact_path()` function (as documented in ARTIFACTS.md), the system automatically creates unique directories with full context information:

```
artifacts/<type>/<context>_<git_hash>_<job_id>_<pid>_<timestamp>/
```

Example:
```
artifacts/test/path_enforcement_c0451da_local_will_22787_20250520_223409/
```

**Note:** If the `context` ends with an underscore (`_`), a double underscore (`__`) is used between the `context` and the hash.

Examples:
```
# Standard case
artifacts/test/path_enforcement_c0451da_local_will_22787_20250520_223409/

# Special case where context ends with an underscore
artifacts/test/path_enforcement__c0451da_local_will_22787_20250520_223409/
```

These paths are recommended for most use cases and provide full traceability with manifest files.

### 2. Simple Type-Based Structure

For simpler output needs, the system also supports a flatter structure where appropriate:

```
artifacts/
├── analysis/  - Main file analysis results (permanent output)
├── vision/    - Vision model analysis outputs
├── test/      - Test outputs and validation results
├── benchmark/ - Performance test results
├── tmp/       - Temporary files (cleared on every run)
```

## Best Practices

1. **Use Automated Canonical Paths**: For most artifacts, use `get_canonical_artifact_path()` to create fully traceable outputs
2. **Use Descriptive Context Names**: Choose clear, specific context strings that describe the artifact's purpose
3. **Clean Up After Tests**: Remove temporary test outputs when no longer needed
4. **Group Related Artifacts**: Keep related outputs in the same canonical artifact directory

## Example Patterns

✅ Best: `artifacts/test/vision_basic_5de7f1a_local_will_32156_20250520_162249/results.json`  
✅ Good: `artifacts/test/vision_basic_results.json`  
❌ Bad: `test_results_20250520_162249/vision_basic_test.json`

## Retention Policy

The `artifacts/tmp` directory is cleared automatically on every run.
Other directories follow these retention policies:

- `analysis`: Keep until manually cleaned (permanent output)
- `vision`: Keep latest N test run results, prune monthly
- `test`: Keep only latest passing test results
- `benchmark`: Keep historical results for trending