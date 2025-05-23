# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
# Install project in development mode
pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_analyzer.py

# Run tests matching pattern
pytest -k test_fastvlm

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check formatting (without changes)
black --check src/ tests/
isort --check-only src/ tests/
```

### CLI Testing
```bash
# Main CLI entry point
fa --help

# Direct file analysis (primary use case)
fa path/to/image.jpg

# Output formats
fa --json path/to/image.jpg          # JSON output
fa --md path/to/image.jpg            # Markdown output
fa --format json path/to/image.jpg   # Alternative JSON syntax

# Verbose output for debugging
fa --verbose path/to/image.jpg

# Run built-in test suite
fa test

# Legacy subcommands (still supported)
fa quick path/to/file.jpg
fa analyze vision path/to/file.jpg

# Other CLI commands
fa validate        # Validate configurations
fa benchmark       # Run benchmarks
fa model list      # List available models
fa model download  # Download models
```

### Project-Specific Scripts
```bash
# Check artifact discipline in all scripts
./check_all_scripts.sh

# Run preflight checks
./preflight.sh

# Check script conformity
./check_script_conformity.sh

# Test path enforcement
./tests/test_path_enforcement.sh
```

## PR Review Workflow with GraphQL

### Reviewing PR Comments and Resolving Them

Follow this step-by-step workflow for working with PR comments:

```bash
# 1. Get the PR number for the current branch
gh pr list --head $(git branch --show-current) --json number --jq '.[0].number'

# 2. Get PR ID (node_id) - replace PR_NUMBER with the actual number
export PR_NUMBER=5
gh api repos/primeinc/file-analyzer/pulls/$PR_NUMBER --jq .node_id
# Example output: PR_kwDOOtfNVs6XDJNj - save this as PR_ID

# 3. Get all review threads from a PR with filtering
# This command shows all unresolved threads and their details
export PR_NUMBER=5
gh api graphql -f query='
query {
  repository(owner: "primeinc", name: "file-analyzer") {
    pullRequest(number: '"$PR_NUMBER"') {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 5) {
            nodes {
              body
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}' | jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
# Example output with thread IDs: PRRT_kwDOOtfNVs5QXxLc, etc.

# 4. Add a general comment to the PR (simpler approach)
export PR_NUMBER=5
gh pr comment $PR_NUMBER -b "Your comment here"

# 5. Create a new review (needed for thread operations)
export PR_ID="PR_kwDOOtfNVs6XDJNj"  # Use the value from step 2
gh api graphql -f query='
mutation {
  addPullRequestReview(input: {
    pullRequestId: "'"$PR_ID"'",
    event: COMMENT,
    body: "Addressing review comments"
  }) {
    pullRequestReview {
      id
    }
  }
}'
# Save the returned review ID, example: PRR_kwDOOtfNVs6qU3aH

# 6. To resolve threads directly (without adding new comments)
# First make sure you have the thread IDs from step 3
export THREAD_ID="PRRT_kwDOOtfNVs5QXxLc"  # Replace with actual thread ID
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {
    threadId: "'"$THREAD_ID"'"
  }) {
    thread {
      id
      isResolved
    }
  }
}'
```

For multiple threads, you can create a script to iterate through them:

```bash
#!/bin/bash
# Example script to resolve multiple threads

# Thread IDs from the query in step 3
THREAD_IDS=(
  "PRRT_kwDOOtfNVs5QXxLc"
  "PRRT_kwDOOtfNVs5QXxLu"
  "PRRT_kwDOOtfNVs5QXxq0"
  "PRRT_kwDOOtfNVs5QXxq2"
)

# Resolve each thread
for thread_id in "${THREAD_IDS[@]}"; do
  echo "Resolving thread: $thread_id"
  gh api graphql -f query='
  mutation {
    resolveReviewThread(input: {
      threadId: "'"$thread_id"'"
    }) {
      thread {
        id
        isResolved
      }
    }
  }'
done
```

## CRITICAL RULES

1. **DO NOT MODIFY ANY FILES IN THE `libs/` DIRECTORY**: The `libs/` directory contains external libraries and dependencies that should NEVER be modified directly. If changes are needed to library functionality, create wrapper functions instead.

2. **When responding to GitHub PR review threads**:
   - DO NOT create multiple new reviews
   - Reply to existing threads using the existing review
   - For each thread: (1) add your own comment, (2) submit the review, (3) resolve the thread
   - Use `addPullRequestReviewComment` with `inReplyTo` parameter, NOT `addPullRequestReviewThread`

3. **Todo List Management**:
   - Organize todos by priority and group related tasks together
   - Mark tasks as in_progress while working on them and completed immediately when finished
   - Only have ONE task in_progress at a time
   - Create specific, actionable items with clear success criteria

## Project Overview

The File Analysis System is a unified tool for comprehensive file analysis that combines multiple specialized tools:

- ExifTool: Metadata extraction
- rdfind: Duplicate detection
- Tesseract OCR: Text from images
- ClamAV: Malware scanning
- ripgrep: Content searching
- binwalk: Binary analysis
- Vision Models: AI-powered image analysis (FastVLM, BakLLaVA, Qwen2-VL)

## Commands

### Running the File Analyzer

```bash
# Run all analyses on a directory
./tools/analyze.sh -a <path_to_analyze>

# Run the Python script directly
python src/analyzer.py --all <path_to_analyze>

# Extract metadata and find duplicates
./tools/analyze.sh -m -d <path_to_analyze>

# Search for specific content
./tools/analyze.sh -s "password" <path_to_analyze>

# OCR images in a directory
./tools/analyze.sh -o <path_to_analyze>

# Custom output directory
./tools/analyze.sh -a <path_to_analyze> -r /path/to/output

# Analyze images with AI vision models
./tools/analyze.sh -V <path_to_analyze>

# Use a specific vision model
./tools/analyze.sh -V --vision-model fastvlm <path_to_analyze>

# Document analysis mode
./tools/analyze.sh -V --vision-mode document <path_to_analyze>
```

### Analysis Options

- `-a, --all`: Run all analyses
- `-m, --metadata`: Extract metadata
- `-d, --duplicates`: Find duplicates
- `-o, --ocr`: Perform OCR on images
- `-v, --virus`: Scan for malware
- `-s, --search TEXT`: Search content
- `-b, --binary`: Analyze binary files
- `-V, --vision`: Analyze images with AI vision models
- `--vision-model MODEL`: Select vision model (fastvlm, bakllava, qwen2vl)
- `--vision-mode MODE`: Vision analysis mode (describe, detect, document)
- `-r, --results DIR`: Output directory

## Architecture

**Plugin-based CLI**: Main entry point at `src/cli/main.py` using Typer with subcommands registered via entry points:
- `fa <filepath>` - Direct file analysis with AI vision models (primary use case)
- `fa analyze` - Comprehensive file analysis with multiple tools (ExifTool, OCR, duplicates, etc.)  
- `fa test` - Built-in test suite
- `fa validate` - Configuration validation
- `fa model` - AI model management
- `fa benchmark` - Performance testing
- `fa quick` - Legacy alias for direct file analysis

**Core Components**:
- `src/core/analyzer.py` - Main `FileAnalyzer` class with parallel processing
- `src/core/vision.py` - AI vision model integration (FastVLM, BakLLaVA, Qwen2-VL)
- `src/models/` - Model adapters and management system
- `src/utils/json_utils.py` - Robust JSON extraction and validation for AI outputs

**Artifact System**: Strict path discipline with canonical artifact paths in `artifacts/` directory to prevent file sprawl. All scripts must source `artifact_guard_py_adapter.sh`.

### Output Files

The analyzer produces several output files with results in canonical artifact paths:

- `artifacts/analysis/<context>/analysis_summary.json`: Overall summary
- `artifacts/analysis/<context>/metadata.json`: File metadata
- `artifacts/analysis/<context>/duplicates.txt`: Duplicate files
- `artifacts/analysis/<context>/ocr_results.json`: Text from images
- `artifacts/analysis/<context>/malware_scan.txt`: Malware scan results
- `artifacts/analysis/<context>/search_results.txt`: Content search results
- `artifacts/analysis/<context>/binary_analysis.txt`: Binary analysis
- `artifacts/vision/<context>/vision_analysis.json`: AI vision model analysis

## Dependencies

The system requires the following external tools to be installed and available in the PATH:

- ExifTool
- rdfind
- Tesseract OCR
- ClamAV
- ripgrep (rg)
- binwalk

For vision analysis, the following dependencies might be required based on selected model:

- Python 3.8+
- For FastVLM: `pip install mlx mlx-fastvlm`
- For BakLLaVA: llama.cpp or Fuzzy-Search/realtime-bakllava
- For Qwen2-VL: `pip install mlx-vlm`

If any of these tools are missing, the corresponding analysis will fail with an error status.

## Extension Points

**Adding Analysis Types**: Add methods to `FileAnalyzer` class in `src/core/analyzer.py` and register CLI options.

**Adding Model Adapters**: Implement adapter interface in `src/models/` and register with model manager.

**Adding CLI Commands**: Create new modules in `src/cli/` and register via entry points in `pyproject.toml`.

## JSON Validation System

The File Analysis System includes a robust JSON validation system for handling vision model outputs:

### JSON Utilities Module

The `json_utils.py` module centralizes JSON handling operations:

- **JSONValidator** class with methods for:
  - Extracting valid JSON from text responses using multiple strategies
  - Validating JSON structure against expected fields
  - Adding standardized metadata to JSON results
  - Formatting fallback responses when JSON parsing fails

- **Common prompt templates** for different analysis modes:
  - `describe`: General image description with tags
  - `detect`: Object detection with locations
  - `document`: Text extraction and document type identification
  - `retry`: Stronger prompts for retry attempts

### JSON Extraction Features

The system employs a multi-stage approach to extract JSON from potentially malformed text:

1. **Direct parsing** - Simple `json.loads()` attempt
2. **Pattern matching** - Regex search for field-specific patterns
3. **Balanced bracket search** - Character-by-character parsing with stack-based tracking
4. **Embedded JSON detection** - Finds JSON objects embedded within larger text

The extraction can handle nested objects, arrays, and quoted strings properly.

## Intelligent Filename Generation

The system includes smart filename generation that suggests meaningful names based on image content:

### Features
- **Content-specific patterns**: Recognizes letters (letter-t.jpg), numbers (number-5.jpg), icons (icon-star.png)
- **Semantic analysis**: Uses AI models to generate descriptive filenames from image content
- **Tag cleaning**: Removes generic terms like "image", "photo", "shooting" while preserving meaningful tags
- **Fallback logic**: Graceful degradation when AI analysis fails or produces unclear results

### Implementation
- `src/cli/utils/render.py` - Main filename generation logic
- Model-based filename suggestions using targeted prompts
- Tag deduplication and frequency-based sorting
- Length limits and filesystem-safe character handling

### Usage
```python
from src.cli.utils.render import generate_intelligent_filename, clean_and_dedupe_tags

# Generate filename from description
filename = generate_intelligent_filename(description, original_path, file_extension)

# Clean and deduplicate tags
clean_tags = clean_and_dedupe_tags(raw_tags)
```

## Model Management

**Storage Locations** (in precedence order):
- `~/.local/share/fastvlm/` - User-level storage (preferred)
- `libs/ml-fastvlm/checkpoints/` - Project-level (development)

**Setup and Usage**:
```bash
# Setup environment and download 0.5B model
./tools/setup_fastvlm.sh

# List/download models via CLI
fa model list
fa model download --size 0.5b

# Use in Python
from src.models.fastvlm.adapter import create_adapter
adapter = create_adapter(model_size="0.5b")
result = adapter.predict(image_path, prompt, mode="describe")
```

See MODELS.md for complete details.

## Comprehensive Testing Strategy

The project includes multiple layers of testing to prevent regressions and ensure reliability:

### Test Categories

**Unit Tests**: Individual component testing
```bash
pytest tests/test_analyzer.py              # Core analyzer functionality
pytest tests/test_vision_core.py           # Vision model integration
pytest tests/test_fastvlm_json.py         # JSON parsing and model outputs
pytest tests/test_json_utils.py           # JSON extraction utilities
```

**Integration Tests**: End-to-end workflow testing
```bash
pytest tests/test_cli_integration.py       # Complete CLI user experience
pytest tests/test_end_to_end.py           # Full analysis workflows
pytest tests/test_vision_integrations.py  # Model adapter integration
```

**Regression Prevention**: Specific tests for known issues
```bash
# CLI argument parsing regression (fa filepath not working)
pytest tests/test_cli_integration.py::TestRegressionPrevention::test_cli_argument_parsing_regression

# Model token limit optimization (prevents JSON repetition)
pytest tests/test_fastvlm_json_parsing.py::test_token_limit_optimization
```

### Key Test Features

**CLI Integration Tests** (`tests/test_cli_integration.py`):
- Tests all user-facing command patterns (`fa filepath`, `fa --json filepath`, etc.)
- Path handling (relative, absolute, tilde expansion)
- Output format validation (JSON, Markdown, text)
- Error scenarios and edge cases
- Filename generation and tag cleaning
- Regression prevention for CLI argument parsing

**Model Output Tests** (`tests/test_fastvlm_json_parsing.py`):
- Real captured model outputs for validation
- Token limit optimization testing (256 vs 512 tokens)
- JSON repair functionality validation
- Malformed JSON handling

**Artifact Discipline Tests**:
- Path validation and artifact sprawl prevention
- Precommit hook validation
- Safe function testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage reporting
pytest --cov=src

# Run specific test categories
pytest tests/test_cli_integration.py -v     # CLI integration
pytest tests/test_*regression* -v           # Regression tests
pytest -k "fastvlm" -v                     # FastVLM-related tests

# Run tests that would catch specific regressions
pytest tests/test_cli_integration.py::TestRegressionPrevention -v
```

### Test Strategy Notes

1. **Mock Strategy**: Tests use `unittest.mock.patch` to mock model calls for fast, reliable testing
2. **Real Data**: Some tests use actual captured model outputs to validate JSON parsing
3. **Subprocess Testing**: CLI integration tests use `subprocess.run` to test actual user experience
4. **Regression Focus**: Specific tests designed to catch known regression patterns
5. **Performance**: Fast unit tests (< 1s) with longer integration tests (< 30s) for comprehensive coverage

## Complete GitHub PR Review Workflow

Working with GitHub PR comments can be complex due to GraphQL API requirements. Below is a comprehensive guide covering all common PR review workflows:

### 1. Finding and Analyzing PR Comments

First, identify your PR and get a list of all unresolved comments:

```bash
# Create a script called pr-comments.sh
#!/bin/bash

# Get the PR number for current branch
PR_NUMBER=$(gh pr list --head $(git branch --show-current) --json number --jq '.[0].number')
echo "Current PR: #$PR_NUMBER"

# Get PR node ID (needed for GraphQL operations)
PR_ID=$(gh api repos/primeinc/file-analyzer/pulls/$PR_NUMBER --jq .node_id)
echo "PR ID: $PR_ID"

# Get all unresolved review threads - saving full output
gh api graphql -f query='
query {
  repository(owner: "primeinc", name: "file-analyzer") {
    pullRequest(number: '"$PR_NUMBER"') {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 5) {
            nodes {
              body
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}' > pr_threads.json

# Extract and display just the unresolved threads
echo "Unresolved review threads:"
cat pr_threads.json | jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | {id: .id, path: .path, line: .line, comment: .comments.nodes[0].body, author: .comments.nodes[0].author.login}'

# Save thread IDs to a file for later use
cat pr_threads.json | jq -r '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false) | .id' > unresolved_thread_ids.txt

echo "Thread IDs saved to unresolved_thread_ids.txt"
```

### 2. Addressing Multiple Comments Efficiently

After fixing the issues described in the comments, use this script to add a response to the PR and resolve all threads:

```bash
# Create a script called resolve-pr-comments.sh
#!/bin/bash

PR_NUMBER=$(gh pr list --head $(git branch --show-current) --json number --jq '.[0].number')
PR_ID=$(gh api repos/primeinc/file-analyzer/pulls/$PR_NUMBER --jq .node_id)

# Add a single general PR comment explaining all the fixes
gh pr comment $PR_NUMBER -b "I've addressed all the unresolved PR review comments:

$(cat unresolved_thread_ids.txt | wc -l) issues have been fixed and committed to the branch.

$(git log -1 --pretty=%B)"

# Resolve all threads in the file
echo "Resolving all threads..."
while read thread_id; do
  echo "Resolving thread: $thread_id"
  gh api graphql -f query='
  mutation {
    resolveReviewThread(input: {
      threadId: "'"$thread_id"'"
    }) {
      thread {
        id
        isResolved
      }
    }
  }'
done < unresolved_thread_ids.txt

echo "All PR threads resolved!"
```

### 3. For Individual Comment Responses (When Needed)

In some cases, you may want to respond to individual comments with specific replies. Here's how to do that:

```bash
# Create a new review for your responses
PR_ID="PR_kwDOOtfNVs6XDJNj"  # Use the value from previous step
REVIEW_RESPONSE=$(gh api graphql -f query='
mutation {
  addPullRequestReview(input: {
    pullRequestId: "'"$PR_ID"'",
    event: COMMENT,
    body: "Addressing specific review comments"
  }) {
    pullRequestReview {
      id
    }
  }
}')
REVIEW_ID=$(echo $REVIEW_RESPONSE | jq -r '.data.addPullRequestReview.pullRequestReview.id')
echo "Created review: $REVIEW_ID"

# Now add a thread response to a specific file/line
# You need both the path and line number from the original comment
gh api graphql -f query='
mutation {
  addPullRequestReviewThread(input: {
    pullRequestReviewId: "'"$REVIEW_ID"'",
    path: "src/cli/common/config.py",
    line: 46,  # Must match the line from the original comment
    body: "Fixed by implementing a robust find_project_root() function that looks for marker files."
  }) {
    thread {
      id
    }
  }
}'

# Submit your review with all the thread responses
gh api graphql -f query='
mutation {
  submitPullRequestReview(input: {
    pullRequestReviewId: "'"$REVIEW_ID"'",
    event: COMMENT
  }) {
    pullRequestReview {
      id
    }
  }
}'

# After submission, you can resolve individual threads
THREAD_ID="PRRT_kwDOOtfNVs5QXxLc"  # Get this from previous step
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {
    threadId: "'"$THREAD_ID"'"
  }) {
    thread {
      id
      isResolved
    }
  }
}'
```

### Important Tips for PR Comment Management

1. Always check if your PR is up-to-date with the latest changes before responding to comments
2. Group related fixes in a single commit with a clear message
3. When you have fixed all comments, it's generally better to:
   - Add one comprehensive PR comment explaining all the fixes
   - Resolve all threads directly without individual responses
   - Push your changes in a single commit
4. For complex PRs with many comments, maintain a checklist of issues to track progress
5. Use the GitHub web UI for simple responses when the GraphQL API seems too complex