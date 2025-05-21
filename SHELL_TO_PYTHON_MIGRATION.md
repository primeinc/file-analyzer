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
| tests/env_example_test.sh | ✅ Removed | tests/test_artifact_discipline.py         |
| tests/example_test.sh   | ✅ Removed   | tests/test_artifact_discipline.py         |
| tests/strict_example.sh | ✅ Removed   | tests/test_python_artifact_discipline.py  |
| tests/test_basic.sh     | ✅ Removed   | tests/test_analyzer.py                    |
| tests/test_exit_codes.sh | ✅ Removed  | tests/test_vision_integrations.py         |
| tests/test_exit_codes_forced.sh | ✅ Removed | tests/test_vision_integrations.py   |
| tests/test_fastvlm.sh   | ✅ Removed   | tests/test_fastvlm_json.py               |
| tests/test_path_enforcement.sh | ✅ Removed | tests/test_artifact_discipline.py    |
| check_script_conformity.sh | ✅ Completed | src/cli/artifact/script_checks.py      |
| check_all_scripts.sh    | ✅ Completed | src/cli/artifact/script_checks.py (all command) |
| preflight.sh            | ✅ Completed | src/cli/artifact/preflight.py            |
| install.sh              | ✅ Completed | src/cli/install/main.py                 |
| test_hook.sh            | ✅ Completed | src/cli/test/hook.py                    |
| artifact_guard_py_adapter.sh | ✅ Completed | src/cli/artifact/adapter.py         |

## Python Module Migration

| Python Module           | Status      | CLI Integration                           |
|-------------------------|-------------|-------------------------------------------|
| src/artifact_guard_cli.py | ✅ Completed | src/cli/artifact/main.py                |
| src/analyzer.py         | ⏳ In Progress | src/cli/analyze/main.py                 |
| src/download_models.py  | ✅ Completed | src/cli/model/main.py                     |
| src/benchmark_fastvlm.py | ✅ Completed  | src/cli/benchmark/main.py               |
| src/generate_benchmark_samples.py | ✅ Completed | src/cli/benchmark/samples.py      |

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

#### check_script_conformity.sh (Completed)
- Implementation: `src/cli/artifact/script_checks.py`
- CLI Commands:
  - `fa artifact script-checks check` - Check shell scripts for proper artifact discipline
  - `fa artifact script-checks all` - Check all scripts in src, tools, and tests directories

#### check_all_scripts.sh (Completed)
- Implementation: `src/cli/artifact/script_checks.py` (all command)
- CLI Command:
  - `fa artifact script-checks all` - Check all scripts in src, tools, and tests directories

#### preflight.sh (Completed)
- Implementation: `src/cli/artifact/preflight.py`
- CLI Command:
  - `fa preflight run` - Run all preflight checks to ensure repository is in a valid state

#### install.sh (Completed)
- Implementation: `src/cli/install/main.py`
- CLI Command:
  - `fa install run [INSTALL_DIR]` - Install the File Analyzer tools to the specified directory

#### test_hook.sh (Completed)
- Implementation: `src/cli/test/hook.py`
- CLI Command:
  - `fa test hook run` - Run a simple test hook for CI/pre-commit integration

#### Migration Status
✅ Full Python implementation for cleanup.sh, check_script_conformity.sh, check_all_scripts.sh, preflight.sh, install.sh, and test_hook.sh
✅ Added to entry points in pyproject.toml
✅ Added to CLI loader in src/cli/main.py
✅ CLI commands registered and accessible

### Phase 3: Artifact Guard Migration (Completed)

#### artifact_guard_py_adapter.sh
This script provides bash function overrides for path operations. It's used by all other shell scripts to enforce artifact discipline.

Migration:
1. Created a Python-to-Bash adapter in src/cli/artifact/adapter.py
2. Implemented shell function generation for bash (mkdir_guard, touch_guard, cp_guard, mv_guard)
3. Added CLI interface for use by shell scripts with the following commands:
   - `python -m src.cli.artifact.adapter create TYPE CONTEXT` - Create a canonical artifact path
   - `python -m src.cli.artifact.adapter validate PATH` - Validate a path against artifact discipline
   - `python -m src.cli.artifact.adapter setup` - Set up artifact directory structure
   - `python -m src.cli.artifact.adapter env` - Generate environment script
   - `python -m src.cli.artifact.adapter shell FUNC` - Generate shell commands for bash
   - `python -m src.cli.artifact.adapter batch` - Run commands from stdin in batch mode

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

### check_script_conformity.sh to fa artifact script-checks

| Shell Command                            | Python CLI Command                      |
|-----------------------------------------|---------------------------------------|
| check_script_conformity.sh file1.sh file2.sh | fa artifact script-checks check file1.sh file2.sh |
| check_script_conformity.sh              | fa artifact script-checks check        |

### check_all_scripts.sh to fa artifact script-checks all

| Shell Command              | Python CLI Command                    |
|----------------------------|------------------------------------|
| check_all_scripts.sh       | fa artifact script-checks all       |

### preflight.sh to fa preflight

| Shell Command              | Python CLI Command                    |
|----------------------------|------------------------------------|
| preflight.sh               | fa preflight run                    |
| preflight.sh --no-enforce  | fa preflight run --no-enforce       |
| preflight.sh --no-tmp-clean | fa preflight run --no-tmp-clean     |

### install.sh to fa install

| Shell Command              | Python CLI Command                    |
|----------------------------|------------------------------------|
| install.sh                 | fa install run                      |
| install.sh ~/bin           | fa install run ~/bin                |

### test_hook.sh to fa test hook

| Shell Command              | Python CLI Command                    |
|----------------------------|------------------------------------|
| test_hook.sh               | fa test hook run                    |

## Entry Point Registration

The Python CLI commands are registered as entry points in `pyproject.toml`:

```toml
[project.entry-points."fa.commands"]
analyze = "src.cli.analyze.main:app"
test = "src.cli.test.main:app"
validate = "src.cli.validate.main:app"
artifact = "src.cli.artifact.main:app"
install = "src.cli.install.main:app"
```

After installing the package, these commands are available through the `fa` CLI command.

## Extending the CLI Loader

We've updated the command loader in `src/cli/main.py` to support the new commands:

1. Added direct registration for the preflight and install commands
2. Improved the fallback mechanism for direct imports
3. Enhanced error handling and reporting for command loading issues

The main CLI now supports the following commands:
- `fa analyze` - Analyze files and directories
- `fa test` - Run tests for file analysis functionality
- `fa validate` - Validate JSON files against schemas
- `fa artifact` - Manage artifact directories and outputs
- `fa preflight` - Perform preflight checks for repository state
- `fa install` - Install the File Analyzer tools

Additionally, subcommands have been implemented:
- `fa test hook` - Run test hook for CI/pre-commit integration
- `fa artifact script-checks` - Check shell scripts for artifact discipline

### artifact_guard_py_adapter.sh to Python Module

| Shell Command                       | Python CLI Command                       |
|------------------------------------|----------------------------------------|
| artifact_guard_py_adapter.sh create TYPE NAME | python -m src.cli.artifact.adapter create TYPE NAME |
| artifact_guard_py_adapter.sh validate PATH | python -m src.cli.artifact.adapter validate PATH |
| artifact_guard_py_adapter.sh setup | python -m src.cli.artifact.adapter setup |
| artifact_guard_py_adapter.sh env   | python -m src.cli.artifact.adapter env   |
| artifact_guard_py_adapter.sh       | python -m src.cli.artifact.adapter       |

### artifact_guard_cli.py to fa artifact

| Python CLI Command                    | fa CLI Command                          |
|--------------------------------------|----------------------------------------|
| python src/artifact_guard_cli.py create TYPE NAME | fa artifact path TYPE NAME              |
| python src/artifact_guard_cli.py validate PATH | fa artifact validate PATH               |
| python src/artifact_guard_cli.py setup | fa artifact setup                       |
| python src/artifact_guard_cli.py cleanup --days 7 | fa artifact clean --days 7              |
| python src/artifact_guard_cli.py info | fa artifact info                        |

### analyzer.py to fa analyze

| Python CLI Command                    | fa CLI Command                          |
|--------------------------------------|----------------------------------------|
| python src/analyzer.py --all PATH    | fa analyze all PATH                     |
| python src/analyzer.py --metadata PATH | fa analyze metadata PATH                |
| python src/analyzer.py --duplicates PATH | fa analyze duplicates PATH            |
| python src/analyzer.py --ocr PATH    | fa analyze ocr PATH                     |
| python src/analyzer.py --virus PATH  | fa analyze virus PATH                   |
| python src/analyzer.py --search "text" PATH | fa analyze search "text" PATH         |
| python src/analyzer.py --binary PATH | fa analyze binary PATH                  |
| python src/analyzer.py --vision PATH | fa analyze vision PATH                  |
| python src/analyzer.py --verify      | fa analyze verify                       |

### download_models.py to fa model

| Python CLI Command                      | fa CLI Command                        |
|---------------------------------------|--------------------------------------|
| python src/download_models.py list    | fa model list                        |
| python src/download_models.py download --size 0.5b | fa model download 0.5b   |
| python src/download_models.py download --size 1.5b | fa model download 1.5b   |
| python src/download_models.py download --size 7b | fa model download 7b       |

### benchmark_fastvlm.py to fa benchmark

| Python CLI Command                      | fa CLI Command                        |
|---------------------------------------|--------------------------------------|
| python src/benchmark_fastvlm.py       | fa benchmark run                     |
| python src/benchmark_fastvlm.py --images DIR | fa benchmark run --images DIR  |
| python src/benchmark_fastvlm.py --model PATH | fa benchmark run --model PATH  |
| N/A                                   | fa benchmark images                  |
| N/A                                   | fa benchmark images --download       |

### generate_benchmark_samples.py to fa benchmark samples

| Python CLI Command                      | fa CLI Command                        |
|---------------------------------------|--------------------------------------|
| python src/generate_benchmark_samples.py | fa benchmark samples generate       |
| python src/generate_benchmark_samples.py --no-cache | fa benchmark samples generate --no-cache |
| python src/generate_benchmark_samples.py --force | fa benchmark samples generate --force |
| N/A                                   | fa benchmark samples cache --info    |
| N/A                                   | fa benchmark samples cache --clear   |

## Next Steps

1. Add unit tests for all the new Python implementations
2. Delete all shell scripts after Python implementations are complete
3. Update any documentation or references to shell scripts
4. Create new artifact_guard_py_adapter.sh that sources Python-generated functions