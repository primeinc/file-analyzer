#!/bin/bash
# This is a wrapper for the Python-based preflight check
# All functionality has been migrated to src.cli.artifact.preflight

# Pass all arguments to the Python module
python -m src.cli.artifact.preflight run "$@"
exit $?