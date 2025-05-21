#!/bin/bash
# analyze.sh - Command-line wrapper for the file analysis system
# This is a transitional wrapper for backward compatibility
# Long-term, we should use the Python CLI directly

# Get the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source the artifact guard adapter
source "$PROJECT_ROOT/artifact_guard_py_adapter.sh"

# Forward all arguments to the Python analyzer
python3 "$PROJECT_ROOT/src/analyzer.py" "$@"
