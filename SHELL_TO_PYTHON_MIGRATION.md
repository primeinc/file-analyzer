# Shell Script to Python CLI Migration Plan

This document outlines the plan for migrating shell scripts to Python CLI commands.

## Progress Summary

| Script                  | Status      | Python Replacement                        |
|-------------------------|-------------|-------------------------------------------|
| tools/batch_json_test.sh | ✅ Removed   | src/cli/test/json_tests.py                |
| tools/direct_validation_test.sh | ✅ Removed | src/cli/validate/main.py            |
| tools/process_model_test.sh | ✅ Removed | src/model_config.py                     |
| tools/run_fastvlm_tests.sh | ✅ Removed | src/cli/test/fastvlm_tests.py            |
| tools/setup_fastvlm.sh  | ✅ Removed   | src/download_models.py                    |
| tools/vision_test.sh    | ✅ Removed   | src/cli/analyze/main.py (vision command)  |
| tools/direct_fastvlm_test.py | ✅ Removed | src/cli/analyze/main.py (vision command) |
| cleanup.sh              | ✅ Removed   | src/cli/artifact/main.py                |
| artifact_guard_py_adapter.sh | ⏳ Planned | src/artifact_guard.py                  |
| check_all_scripts.sh    | ⏳ Planned | TBD                                         |
| check_script_conformity.sh | ⏳ Planned | TBD                                      |
| preflight.sh            | ⏳ Planned | TBD                                         |
| test_hook.sh            | ⏳ Planned | TBD                                         |
| install.sh              | 🔄 In Progress | Hybrid approach                         |

## Migration Strategy

### Phase 1: Tool Scripts (Completed)
The scripts in the `tools/` directory that were direct wrappers around analyzer functionality have been migrated to corresponding Python CLI commands under the new `fa` command.

### Phase 2: Core Infrastructure Scripts (In Progress)

#### cleanup.sh (Completed)
- Implementation: `src/cli/artifact/main.py`
- CLI Commands:
  - `fa artifact setup` - Set up the artifact directory structure
  - `fa artifact clean` - Clean up old artifacts based on retention policy
  - `fa artifact clean-tmp` - Clean only temporary artifacts directory
  - `fa artifact report` - Generate a report of current artifacts and disk usage
  - `fa artifact check` - Check for artifact sprawl outside the canonical structure
  - `fa artifact env` - Print environment variables for artifact directories
  - `fa artifact env-file` - Generate artifacts.env file for sourcing in shell scripts
  - `fa artifact path TYPE NAME` - Get a canonical path in the artifact directory

#### Migration Status
✅ Full Python implementation
✅ Added to entry points in pyproject.toml
✅ Added to CLI loader in src/cli/main.py
✅ Removed original shell script

### Phase 3: Artifact Guard Migration (Planned)

#### artifact_guard_py_adapter.sh
This script provides bash function overrides for path operations. It's used by all other shell scripts to enforce artifact discipline.

Migration Plan:
1. Create a Python-to-Bash adapter that can be invoked from shell scripts
2. Update artifact_guard_py_adapter.sh to use the new adapter
3. Gradually refactor remaining shell scripts to use Python directly

### Phase 4: CI/CD and Test Fixtures (Planned)

Scripts in this category:
- check_all_scripts.sh
- check_script_conformity.sh
- preflight.sh
- test_hook.sh
- Tests in tests/*.sh

Migration Plan:
1. Create Python equivalents for CI/CD scripts
2. Update CI/CD pipelines to use new Python commands
3. Gradually refactor test fixtures to use Python

## Command Mappings

### cleanup.sh to fa artifact

| Shell Command              | Python CLI Command                        |
|----------------------------|-------------------------------------------|
| cleanup.sh --setup         | fa artifact setup                         |
| cleanup.sh --path TYPE NAME | fa artifact path TYPE NAME               |
| cleanup.sh --clean         | fa artifact clean                         |
| cleanup.sh --clean-tmp     | fa artifact clean-tmp                      |
| cleanup.sh --report        | fa artifact report                        |
| cleanup.sh --check         | fa artifact check                         |
| cleanup.sh --env           | fa artifact env                           |
| cleanup.sh --generate-env  | fa artifact env-file                      |

## Entry Point Registration

The Python CLI commands are registered as entry points in `pyproject.toml`:

```toml
[project.entry-points."fa.commands"]
analyze = "src.cli.analyze.main:app"
test = "src.cli.test.main:app"
validate = "src.cli.validate.main:app"
artifact = "src.cli.artifact.main:app"
```

After installing the package, these commands are available through the `fa` CLI command.

## Fixing the CLI Loader

To ensure proper loading of CLI commands, we've updated the command loader in `src/cli/main.py`:

1. The loader detects entry points from the `fa.commands` group
2. Commands are registered using explicit imports for clarity and error reporting
3. A fallback mechanism is provided for direct imports if entry point discovery fails
4. Better error handling and reporting for command loading issues

## Next Steps

1. Complete testing of the Python CLI artifact commands
2. Add a deprecation notice to cleanup.sh
3. Begin planning for the next round of script migrations
4. Add unit tests for the Python CLI implementation