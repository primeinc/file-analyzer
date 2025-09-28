# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

The File Analysis System is a unified AI-powered file analysis tool that combines multiple specialized tools for comprehensive file analysis. It features intelligent filename generation, vision model analysis, and artifact discipline enforcement.

**Primary Technologies:**
- **AI Vision Models**: FastVLM (Apple Silicon optimized), BakLLaVA, Qwen2-VL
- **CLI Framework**: Typer with plugin-based architecture
- **Output Formats**: Text, JSON, Markdown with intelligent rendering
- **Path Management**: Strict artifact discipline system for output organization

## Quick Development Commands

### Installation & Setup
```bash
# Install project in development mode
pip install -e ".[dev]"

# Install with vision dependencies  
pip install -e ".[dev,vision]"

# Set up FastVLM environment (Apple Silicon)
./tools/setup_fastvlm.sh
```

### Primary Usage Patterns
```bash
# Main use case - direct file analysis with AI vision
fa path/to/image.jpg                    # Smart analysis with filename suggestion
fa --json path/to/image.jpg             # JSON output format
fa --md path/to/image.jpg               # Markdown output format

# Model management
fa model list                           # List available models
fa model download --size 0.5b           # Download specific model size
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test categories
pytest tests/test_cli_essential.py -v           # CLI integration tests
pytest tests/test_fastvlm_json_parsing.py -v   # Model output validation
pytest tests/test_filename_generation.py -v    # Filename generation
pytest -k "regression" -v                      # Regression prevention

# Built-in test suite
fa test
```

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Check formatting (without changes)
black --check src/ tests/
isort --check-only src/ tests/
```

### Project-Specific Scripts
```bash
# Check artifact discipline (critical for this project)
./check_all_scripts.sh
./preflight.sh

# Path enforcement validation
./tests/test_path_enforcement.sh
```

## Architecture Overview

### Plugin-Based CLI System
The CLI uses a hierarchical command structure with dynamic plugin loading:

- **Main Entry**: `src/cli/main.py` - Typer app with plugin discovery
- **Core Commands**: `fa <filepath>` (direct analysis), `fa analyze`, `fa model`, `fa test`
- **Subcommands**: Dynamically loaded via entry points in `pyproject.toml`

**Command Flow**: `fa path.jpg` → analyze_single_file → FileAnalyzer → Vision Models → JSON validation → Intelligent rendering

### Core Components

**File Analysis Engine** (`src/core/analyzer.py`):
- Main `FileAnalyzer` class with parallel processing capabilities
- Integrates multiple analysis tools: ExifTool, rdfind, Tesseract OCR, ClamAV, ripgrep, binwalk
- Configurable analysis pipeline with selective tool execution

**AI Vision Integration** (`src/core/vision.py`):
- Multi-model support: FastVLM (Apple Silicon optimized), BakLLaVA, Qwen2-VL
- Robust JSON output validation with retry mechanisms
- Model-specific adapters in `src/models/` directory

**Intelligent Filename Generation** (`src/cli/utils/render.py`):
- AI-powered filename suggestions based on image content
- Content-specific patterns: `letter-t.jpg`, `number-5.jpg`, `icon-star.png`
- Tag cleaning and semantic analysis with fallback logic

**JSON Validation System** (`src/utils/json_utils.py`):
- Multi-stage JSON extraction from potentially malformed model outputs
- Balanced bracket parsing, pattern matching, embedded JSON detection  
- Centralized validation with standardized metadata injection

### Model Management System

**Centralized Storage** (precedence order):
1. `~/.local/share/fastvlm/` - User-level storage (preferred)
2. `libs/ml-fastvlm/checkpoints/` - Project-level (development)

**Model Sizes and Usage**:
- `0.5b` (1GB) - Development and testing
- `1.5b` (3GB) - Default production use  
- `7b` (14GB) - Highest quality analysis

**Setup Pattern**:
```bash
./tools/setup_fastvlm.sh              # Environment setup
fa model download --size 0.5b         # Download development model
```

### Artifact Discipline System

**Critical Requirement**: This project enforces strict artifact path discipline to prevent file sprawl.

**All scripts MUST**:
1. Source `artifact_guard_py_adapter.sh` immediately after shebang
2. Use only canonical paths from `get_canonical_artifact_path`  
3. Never create manual output directories

**Example Pattern**:
```bash
#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"

# Get canonical path - this is the ONLY way to create artifact directories
TEST_DIR=$(get_canonical_artifact_path test "my_test_context")
mkdir -p "$TEST_DIR/subdirs"  # OK - within canonical path
touch "$TEST_DIR/results.json"  # OK - within canonical path
```

**Directory Structure**:
```
artifacts/
├── analysis/  - File analysis results
├── vision/    - AI vision model outputs  
├── test/      - Test results and validation
├── benchmark/ - Performance benchmarks
├── tmp/       - Temporary files (auto-cleaned)
```

## Development Patterns

### Adding New Analysis Types
1. Add method to `FileAnalyzer` class in `src/core/analyzer.py`
2. Create CLI command in `src/cli/analyze/main.py`
3. Register options in `create_options_dict` function
4. Add tests in `tests/` with canonical artifact paths

### Adding New Vision Models
1. Create adapter in `src/models/` following existing pattern
2. Register in model manager and CLI options
3. Update `MODEL_INFO` dictionary for downloads
4. Add JSON validation patterns if needed

### Adding CLI Commands  
1. Create module in `src/cli/<command>/main.py` with Typer app
2. Register in `pyproject.toml` entry points
3. Add to command mapping in `src/cli/main.py`
4. Follow plugin architecture pattern

### JSON Output Standards
When adding new analysis types that produce JSON:
1. Include `status` field ("success", "error", "skipped")
2. Include `timestamp` and performance metrics
3. Use `json_utils.JSONValidator` for validation
4. Implement retry logic for model outputs
5. Follow consistent field naming

## Testing Strategy

### Comprehensive Test Coverage
**CLI Integration** (`test_cli_essential.py`):
- Tests all user-facing command patterns
- Path handling (relative, absolute, tilde expansion) 
- Output format validation (JSON, Markdown, text)
- **Regression Prevention**: Specific tests for known CLI issues

**Model Output Validation** (`test_fastvlm_json_parsing.py`):
- Real captured model outputs for validation
- Token limit optimization (prevents JSON repetition)
- JSON repair and extraction functionality
- Malformed JSON handling

**Filename Generation** (`test_filename_generation.py`):
- Content recognition patterns
- Tag cleaning and deduplication
- Semantic analysis validation
- Fallback behavior testing

**Artifact Discipline** (`test_artifact_discipline_pytest.py`):
- Path validation and enforcement
- Canonical path compliance
- Security boundary testing

### Running Regression Tests
```bash
# Test specific regression patterns
pytest tests/test_cli_essential.py::TestRegressionPrevention -v

# Test token optimization (prevents model output repetition)  
pytest tests/test_fastvlm_json_parsing.py::test_token_limit_optimization -v
```

## Important Rules from CLAUDE.md

### Critical Constraints
1. **Never modify files in `libs/` directory** - External libraries only, create wrappers if changes needed
2. **Artifact discipline is mandatory** - All outputs must use canonical paths
3. **JSON validation is required** - All model outputs must pass validation
4. **No manual artifact paths** - Use `get_canonical_artifact_path` exclusively

### PR Review Process
For GitHub PR reviews, use the established GraphQL workflow:
```bash
# Get PR info and unresolved threads
PR_NUMBER=$(gh pr list --head $(git branch --show-current) --json number --jq '.[0].number')

# Address all comments, then resolve threads programmatically
# See CLAUDE.md for complete GraphQL scripts
```

## Model File Management (MODELS.md Rules)

### Storage Discipline
- Models stored in `~/.local/share/fastvlm/` (user-level, preferred)
- Never commit model files to git repository
- Use smallest models (0.5b) for development
- Automatic download and validation system

### Development Workflow
1. `./tools/setup_fastvlm.sh` - Set up environment
2. `fa model download --size 0.5b` - Download development model
3. Use adapter API: `from src.models.fastvlm.adapter import create_adapter`
4. Store outputs in canonical artifact paths

The File Analyzer project emphasizes AI-powered analysis, intelligent output formatting, and strict artifact discipline. All development should follow the established patterns for CLI plugins, model integration, and path management.