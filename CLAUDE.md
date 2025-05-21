# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## PR Review Workflow with GraphQL

### Reviewing PR Comments and Resolving Them

```bash
# 1. Get PR ID
gh api repos/OWNER/REPO/pulls/PR_NUMBER --jq .node_id

# 2. Get all review threads from a PR
gh api graphql -f query='
query {
  repository(owner: "primeinc", name: "file-analyzer") {
    pullRequest(number: PR_NUMBER) {
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
}'

# 3. Add a general comment to the PR
gh pr comment PR_NUMBER -b "Your comment here"

# 4. Create a new review
gh api graphql -f query='
mutation {
  addPullRequestReview(input: {
    pullRequestId: "PR_ID_HERE",
    event: COMMENT,
    body: "Addressing review comments"
  }) {
    pullRequestReview {
      id
    }
  }
}'

# 5. Submit a review
gh api graphql -f query='
mutation {
  submitPullRequestReview(input: {
    pullRequestReviewId: "REVIEW_ID_HERE",
    event: COMMENT
  }) {
    pullRequestReview {
      id
    }
  }
}'

# 6. Resolve a specific review thread
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {
    threadId: "THREAD_ID_HERE"
  }) {
    thread {
      id
      isResolved
    }
  }
}'
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

The system consists of several main components:

1. **analyzer.py**: The core Python implementation that:
   - Defines a `FileAnalyzer` class to manage different analysis operations
   - Uses ThreadPoolExecutor for parallel processing
   - Executes external tools via subprocess
   - Generates JSON and text report files
   - Handles error cases and provides appropriate status messages

2. **model_manager.py**: Centralized model management system:
   - Manages model discovery and initialization
   - Provides unified adapter interface
   - Handles model downloads and validation
   - Supports both single file and batch processing

3. **model_analyzer.py**: Unified model analysis interface:
   - Integrates with the core analyzer
   - Provides standardized parameters and output
   - Implements parallel processing for batch operations

The system follows a modular design where each analysis type is encapsulated in its own method within the `FileAnalyzer` class, making it easy to add new analysis capabilities.

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

## Common Development Tasks

### Adding a New Analysis Type

To add a new analysis type:

1. Add a new method to the `FileAnalyzer` class that:
   - Takes necessary parameters
   - Executes the required tool via `run_command`
   - Saves results to a file
   - Updates the `self.results` dictionary
   - Returns the output or None on error

2. Add a new command-line argument in `main()`

3. Update the analyze.sh wrapper script to pass the new argument

### Adding a New Model Adapter

To add a new model adapter:

1. Create a new adapter file (e.g., `my_model_adapter.py`) that implements:
   - `MyModelAdapter` class with `__init__`, `predict`, and `get_info` methods
   - `create_adapter` function that returns an adapter instance

2. Register the adapter with the model manager:
   ```python
   from src.my_model_adapter import create_adapter
   manager = create_manager()
   manager.adapters["my_model"] = create_adapter
   ```

3. Update the model analyzer configuration if needed

### Error Handling

The system uses a consistent error handling pattern:
- Commands are executed with `check=True` in subprocess
- Exceptions are caught and reported
- Analysis methods return None on error
- The results dictionary tracks status as "success", "error", or "skipped"

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

## Model Management System

The file analyzer includes a centralized model management system:

1. **Model Storage**:
   - User-level storage: `~/.local/share/fastvlm/`
   - Project-level storage: `libs/ml-fastvlm/checkpoints/`

2. **Model Discovery**:
   - Automatic path resolution across locations
   - Model version and size management
   - Download capability for missing models

3. **Unified Adapter Interface**:
   - Common API for all model types
   - Standard prediction interface
   - Consistent output format

4. **Model Analyzer**:
   - High-level analysis capabilities
   - Batch processing with parallelism
   - Result tracking and summarization

For more details, see the MODEL_ANALYSIS.md and MODELS.md documentation files.

## GitHub PR Review Thread Workflow

When working with GitHub Pull Request review threads, follow this precise workflow:

### 1. Creating review comments

To comment on specific lines in files and create review threads:

```bash
# Create a new review and get its ID
gh api graphql -f query='
mutation {
  addPullRequestReview(input: {
    pullRequestId: "PR_ID_HERE",  # Get using: gh api repos/{owner}/{repo}/pulls/1 --jq .node_id
    event: COMMENT,
    body: "Starting review with comments"
  }) {
    pullRequestReview {
      id  # Save this ID for subsequent steps
    }
  }
}'
```

### 2. Add threaded review comments on specific files/lines

```bash
# Add review thread on specific line in file
gh api graphql -f query='
mutation {
  addPullRequestReviewThread(input: {
    pullRequestReviewId: "PRR_ID_FROM_STEP_1",
    path: "path/to/file.py",
    line: 42,  # Line number in the file
    body: "Comment about this specific line of code"
  }) {
    thread {
      id  # This is your thread ID for later resolution
    }
  }
}'
```

### 3. Submit the review with all comments

```bash
# Submit the review to make all comments visible
gh api graphql -f query='
mutation {
  submitPullRequestReview(input: {
    pullRequestReviewId: "PRR_ID_FROM_STEP_1",
    event: COMMENT  # Or APPROVE, REQUEST_CHANGES
  }) {
    pullRequestReview {
      id
    }
  }
}'
```

### 4. Listing review threads to resolve

```bash
# Get all review threads with their IDs
gh api graphql -f query='
query {
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 5) {
            nodes {
              id
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
}'
```

### 5. Responding to review threads

IMPORTANT: Always add your own comment to a thread before resolving it! You cannot use addPullRequestReviewComment directly - you must:

1. Create a new review
2. Add thread comments through that review 
3. Submit the review
4. Only then resolve the thread

```bash
# Create a new review for your responses
gh api graphql -f query='
mutation {
  addPullRequestReview(input: {
    pullRequestId: "PR_ID_HERE",
    event: COMMENT,
    body: "Addressing review feedback"
  }) {
    pullRequestReview {
      id  # Use this ID for your responses
    }
  }
}'

# Add threads to specific files/lines to respond to previous comments
gh api graphql -f query='
mutation {
  addPullRequestReviewThread(input: {
    pullRequestReviewId: "YOUR_NEW_REVIEW_ID",
    path: "path/to/file.py",
    line: 42,
    body: "I fixed this issue by implementing X and Y solution"
  }) {
    thread {
      id
    }
  }
}'

# Submit your response review 
gh api graphql -f query='
mutation {
  submitPullRequestReview(input: {
    pullRequestReviewId: "YOUR_NEW_REVIEW_ID",
    event: COMMENT
  }) {
    pullRequestReview {
      id
    }
  }
}'
```

### 6. Resolving review threads

After responding, resolve the threads:

```bash
# Resolve a review thread
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {
    threadId: "THREAD_ID_TO_RESOLVE"
  }) {
    thread {
      id
      isResolved
    }
  }
}'
```