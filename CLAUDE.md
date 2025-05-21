# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
./analyze.sh -a <path_to_analyze>

# Run the Python script directly
./file_analyzer.py --all <path_to_analyze>

# Extract metadata and find duplicates
./analyze.sh -m -d <path_to_analyze>

# Search for specific content
./analyze.sh -s "password" <path_to_analyze>

# OCR images in a directory
./analyze.sh -o <path_to_analyze>

# Custom output directory
./analyze.sh -a <path_to_analyze> -r /path/to/output

# Analyze images with AI vision models
./analyze.sh -V <path_to_analyze>

# Use a specific vision model
./analyze.sh -V --vision-model fastvlm <path_to_analyze>

# Document analysis mode
./analyze.sh -V --vision-mode document <path_to_analyze>
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

The system consists of two main components:

1. **analyze.sh**: A Bash wrapper script that provides a command-line interface and passes arguments to the Python script.

2. **file_analyzer.py**: The core Python implementation that:
   - Defines a `FileAnalyzer` class to manage different analysis operations
   - Uses ThreadPoolExecutor for parallel processing of OCR tasks
   - Executes external tools via subprocess
   - Generates JSON and text report files
   - Handles error cases and provides appropriate status messages

The system follows a modular design where each analysis type is encapsulated in its own method within the `FileAnalyzer` class, making it easy to add new analysis capabilities.

### Output Files

The analyzer produces several output files with results:

- `analysis_summary_[timestamp].json`: Overall summary
- `metadata_[timestamp].json`: File metadata
- `duplicates_[timestamp].txt`: Duplicate files
- `ocr_results_[timestamp].json`: Text from images
- `malware_scan_[timestamp].txt`: Malware scan results
- `search_[text]_[timestamp].txt`: Content search results
- `binary_analysis_[timestamp].txt`: Binary analysis
- `vision_analysis_[timestamp].(txt|json)`: AI vision model analysis

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

3. Update the `analyze.sh` wrapper script to pass the new argument

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

### Retry Logic

For vision model outputs that fail JSON validation:

1. Initial attempt uses a standard JSON-formatted prompt
2. If validation fails, a stronger prompt specifically emphasizing JSON format is used
3. Multiple retry attempts with progressively stricter prompts
4. Graceful fallback to structured text output with appropriate metadata

### Test Infrastructure

The JSON validation system includes comprehensive testing:

- Unit tests for JSON extraction from various text formats
- Tests for progressively corrupted JSON inputs
- Tests for complete JSON parsing failure scenarios
- Integration tests for the full validation pipeline

### Error Reporting

Test scripts include enhanced error reporting:

- Detailed error logs for debugging failed validations
- Non-zero exit codes for CI/CD integration
- Visual indicators (✓/✗) for test status feedback

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

## GitHub CLI Integration

### Authentication and Token Management

The GitHub CLI (gh) provides several methods to authenticate with GitHub's API:

- **Authentication token retrieval**: Use `gh auth token` to display your current authentication token
- **Environment variables**: Set `GH_TOKEN` for automation scenarios
- **Automatic token refresh**: GitHub CLI manages token lifecycle automatically

```bash
# Get current authentication token
TOKEN=$(gh auth token)

# Print token status
gh auth status
```

### Working with Pull Requests

You can interact with pull requests directly using built-in commands or the API:

#### Using Built-in Commands

```bash
# Comment on a pull request
gh pr comment 1 --body "Great improvements!"

# View PR details
gh pr view 1 --json number,title,body,comments

# Checkout a PR
gh pr checkout 1
```

#### Using the GitHub API

The `gh api` command allows direct access to GitHub's REST API:

```bash
# Get PR comments
gh api repos/{owner}/{repo}/issues/1/comments

# Post a comment on a PR
gh api -X POST repos/{owner}/{repo}/issues/1/comments -f body="Nice work!"

# Get detailed PR information
gh api repos/{owner}/{repo}/pulls/1 --jq '.title, .body'
```

### Comment Types and Placement

GitHub supports different types of comments on pull requests:

1. **Regular PR comments**: Comments on the main PR conversation thread
   ```bash
   gh api -X POST repos/{owner}/{repo}/issues/{pr_number}/comments \
     -f body="General comment on the PR"
   ```

2. **Line-specific review comments**: Comments on specific code in the diff
   ```bash
   gh api -X POST repos/{owner}/{repo}/pulls/{pr_number}/comments \
     -f body="Comment on specific code" \
     -f commit_id="{commit_sha}" \
     -f path="path/to/file.py" \
     -f line=42 \
     -f side="RIGHT"
   ```

3. **Reply to an existing comment**: Thread comments
   ```bash
   gh api -X POST repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
     -f body="Reply to previous comment"
   ```

### Automated PR Reviews

You can use the GitHub CLI to automate PR review workflows:

```bash
# Approve a PR
gh pr review 1 --approve

# Request changes on a PR
gh pr review 1 --request-changes --body "Please fix the tests"

# Comment on a PR without approval/rejection
gh pr review 1 --comment --body "Some suggestions to consider"
```

### Authentication Best Practices

- Create separate tokens for different use cases to limit access scope
- Store tokens securely using environment variables or GitHub Secrets
- For GitHub Actions, use the built-in `GITHUB_TOKEN` when possible
- Regularly rotate tokens used in automation workflows
- Use fine-grained tokens with minimal permissions required