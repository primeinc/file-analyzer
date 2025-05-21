# Simplified Artifact Structure

This directory contains all outputs and artifacts produced by the file analyzer system. 

## Key Design Principles

1. **Simplified Organization**: We use distinct subdirectories for logical artifact types. Timestamps in directory names are generally discouraged but may be used in specific cases, such as for retention purposes.
2. **No Ephemeral Timestamps**: Files are versioned with dates only when needed for retention.
3. **Standard Locations**: Each script uses consistent, predictable paths.
4. **Flat Structure**: Avoid nested timestamp-based directories when possible.

## Directory Structure

```
artifacts/
├── analysis/  - Main file analysis results (permanent output)
├── vision/    - Vision model analysis outputs
├── test/      - Test outputs and validation results
├── benchmark/ - Performance test results
├── tmp/       - Temporary files (cleared on every run)
```

## Best Practices

1. **Avoid Timestamps in Directories**: Use descriptive names instead of timestamps for directories
2. **Use Namespaces in Filenames**: Include a scope/component prefix in filenames
3. **Use Timestamp Suffixes When Needed**: Add date suffix to filenames only when needed for versioning
4. **Clean Up After Tests**: Remove temporary test outputs when done

## Example Patterns

✅ Good: `artifacts/test/vision_basic_results.json`  
❌ Bad: `artifacts/test/vision_test_20250520_162249/basic_test.json`

✅ Good: `artifacts/vision/fastvlm_benchmark.json`  
❌ Bad: `fastvlm_test_results_20250520_162249/benchmark_results.json`

## Retention Policy

The `artifacts/tmp` directory is cleared automatically on every run.
Other directories follow these retention policies:

- `analysis`: Keep until manually cleaned (permanent output)
- `vision`: Keep latest N test run results, prune monthly
- `test`: Keep only latest passing test results
- `benchmark`: Keep historical results for trending