# Artifact Discipline Migration Strategy

This document outlines the strategy for transitioning the codebase to use the new enforced artifact management system.

## Current Implementation Status

- ✅ Artifact guard system for runtime path enforcement
- ✅ Preflight check script with strict validation
- ✅ Canonical path structure with unique IDs
- ✅ Machine-readable manifest for each artifact
- ✅ Git pre-commit hook enforcement
- ✅ CI workflow validation

## Required Migration Steps

### 1. Update All Test Scripts (CRITICAL)

Every test script must be updated to:

- Source `artifact_guard.sh` for path discipline
- Use `get_canonical_artifact_path` for all artifact paths
- Replace hardcoded timestamp directories with canonical paths
- Add manifest file for traceability

### 2. Migration Timeline

1. **Phase 1: Enforcement with Temporary Bypasses (Current)**
   - Pre-commit and CI checks are active but allow legacy directories
   - New scripts must follow discipline, existing scripts are flagged
   - `--allow-legacy-dirs` and `--allow-legacy-scripts` flags used

2. **Phase 2: Script Migration (Next Week)**
   - Migrate all test scripts to use artifact guard
   - Update analyze.sh to use canonical paths
   - Remove `--allow-legacy-scripts` flag in CI

3. **Phase 3: Legacy Directory Cleanup (Following Week)**
   - Run one-time migration to move legacy artifacts to canonical structure
   - Remove all legacy artifacts in CI environment
   - Remove `--allow-legacy-dirs` flag
   - Full enforcement active

### 3. Script Migration Process

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

### 4. CI/CD Integration

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