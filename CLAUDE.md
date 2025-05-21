# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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