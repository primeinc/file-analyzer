#!/usr/bin/env python3
"""
Python CLI for Artifact Path Discipline

This is a standalone command-line tool that provides the same functionality
as artifact_guard.sh but with more robust error handling and full Python
implementation.

Usage:
    # Create canonical artifact path
    path=$(python src/artifact_guard_cli.py create test "my test context")
    
    # Validate a path
    python src/artifact_guard_cli.py validate $path
    
    # Setup artifact directory structure
    python src/artifact_guard_cli.py setup
    
    # Clean up old artifacts
    python src/artifact_guard_cli.py cleanup --days 7 --type test
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to the Python path
project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import artifact discipline components
from src.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    cleanup_artifacts,
    setup_artifact_structure,
    ARTIFACT_TYPES,
    ARTIFACTS_ROOT
)

# Terminal colors for enhanced output
RED = '\033[0;31m' if sys.stdout.isatty() else ''
GREEN = '\033[0;32m' if sys.stdout.isatty() else ''
YELLOW = '\033[0;33m' if sys.stdout.isatty() else ''
BOLD = '\033[1m' if sys.stdout.isatty() else ''
RESET = '\033[0m' if sys.stdout.isatty() else ''

def show_project_structure():
    """Display information about the project structure."""
    print(f"""
{GREEN}{BOLD}Project Structure:{RESET}
  ├── {GREEN}src/{RESET}      - Core Python modules and libraries
  ├── {GREEN}tools/{RESET}    - Command-line tools and utilities
  ├── {GREEN}tests/{RESET}    - Test scripts and validation
  └── {GREEN}artifacts/{RESET} - Canonical output storage
      ├── analysis/   - Analysis results
      ├── vision/     - Vision model outputs
      ├── test/       - Test outputs
      ├── benchmark/  - Performance benchmarks
      └── tmp/        - Temporary files (auto-cleaned)
""")

def warn_artifact_discipline():
    """Warn about usage of unprotected operations."""
    print(f"""{YELLOW}{BOLD}WARNING: Artifact Discipline{RESET}
Remember that while artifact_guard.py provides protection via PathGuard and decorators,
direct file operations may bypass this protection.

For full artifact discipline, ensure all files are created within canonical directories
obtained via {BOLD}get_canonical_artifact_path(){RESET}.

Example:
  # Get a canonical artifact path
  from src.artifact_guard import get_canonical_artifact_path, PathGuard
  
  # Create canonical path
  artifact_dir = get_canonical_artifact_path("test", "my_test_context")
  
  # Use PathGuard to enforce discipline
  with PathGuard(artifact_dir):
      with open(os.path.join(artifact_dir, "output.txt"), "w") as f:
          f.write("Test output")
""")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Python CLI for Artifact Path Discipline")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser(
        "create", help="Create a canonical artifact path")
    create_parser.add_argument(
        "type", choices=ARTIFACT_TYPES, help="Artifact type")
    create_parser.add_argument(
        "context", help="Artifact context description")
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a path against artifact discipline")
    validate_parser.add_argument(
        "path", help="Path to validate")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Clean up old artifacts")
    cleanup_parser.add_argument(
        "--days", type=int, default=7, help="Retention days (default: 7)")
    cleanup_parser.add_argument(
        "--type", choices=ARTIFACT_TYPES, help="Artifact type to clean up")
    
    # Setup command
    setup_parser = subparsers.add_parser(
        "setup", help="Set up artifact directory structure")
    
    # Info command - shows project structure and warnings
    info_parser = subparsers.add_parser(
        "info", help="Show information about artifact discipline")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "create":
        # Create canonical artifact path
        try:
            path = get_canonical_artifact_path(args.type, args.context)
            print(path)  # Output just the path for shell script capture
            sys.exit(0)
        except ValueError as e:
            print(f"{RED}{BOLD}ERROR:{RESET} {str(e)}", file=sys.stderr)
            sys.exit(1)
            
    elif args.command == "validate":
        # Validate path against artifact discipline with detailed feedback
        path = args.path
        valid = validate_artifact_path(path)
        
        if valid:
            print(f"{GREEN}Path IS valid according to artifact discipline.{RESET}")
            sys.exit(0)
        else:
            # Provide more specific reasons why the path is invalid
            print(f"{RED}Path is NOT valid according to artifact discipline:{RESET}")
            
            # Check if it's a system directory
            if path.startswith('/tmp') or path.startswith('/var/tmp'):
                print(f"{RED}ERROR:{RESET} Path is a system temporary directory. Use canonical artifact paths instead.")
                print(f"  Use: get_canonical_artifact_path(\"tmp\", \"your_context\") for temporary files.")
            
            # Check if it's attempting path traversal
            elif '..' in path:
                print(f"{RED}ERROR:{RESET} Path contains parent directory references (..) which is not allowed.")
                print(f"  Use absolute paths within the canonical artifact structure.")
            
            # Check if it's outside project directory
            elif not path.startswith('/') and not os.path.abspath(path).startswith(project_root):
                print(f"{RED}ERROR:{RESET} Path is outside the project directory structure.")
                
            # Check if it's using a legacy pattern
            elif any(pattern in path for pattern in ['analysis_results', 'vision_results']):
                print(f"{RED}ERROR:{RESET} Path uses a legacy pattern that is not compatible with artifact discipline.")
                print(f"  Replace legacy paths with canonical artifact paths.")
            
            # Check if it's in artifacts directory but not following canonical structure
            elif path.startswith(ARTIFACTS_ROOT) and not any(f"/{t}/" in path for t in ARTIFACT_TYPES):
                print(f"{RED}ERROR:{RESET} Path is in artifacts directory but doesn't follow canonical type structure.")
                print(f"  Canonical paths must include a valid type: {', '.join(ARTIFACT_TYPES)}")
            
            # General guidance
            print(f"\n{YELLOW}Valid paths must be within:{RESET}")
            print(f"1. {ARTIFACTS_ROOT} and follow canonical naming")
            print(f"2. {project_root}/src, {project_root}/tools, {project_root}/tests")
            print(f"3. Standard files in project root directory")
            
            print(f"\n{YELLOW}Example of valid canonical path:{RESET}")
            print(f"  {get_canonical_artifact_path('test', 'example_context')}")
            
            sys.exit(1)
            
    elif args.command == "cleanup":
        # Clean up old artifacts
        try:
            count = cleanup_artifacts(args.days, args.type)
            print(f"{GREEN}Cleaned up {count} artifact{'s' if count != 1 else ''}.{RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"{RED}{BOLD}ERROR:{RESET} {str(e)}", file=sys.stderr)
            sys.exit(1)
            
    elif args.command == "setup":
        # Set up artifact directory structure
        try:
            setup_artifact_structure()
            print(f"{GREEN}Artifact directory structure set up at {ARTIFACTS_ROOT}{RESET}")
            print(f"Created directories for: {', '.join(ARTIFACT_TYPES)}")
            sys.exit(0)
        except Exception as e:
            print(f"{RED}{BOLD}ERROR:{RESET} {str(e)}", file=sys.stderr)
            sys.exit(1)
            
    elif args.command == "info":
        # Show information about artifact discipline
        show_project_structure()
        warn_artifact_discipline()
        print(f"\n{BOLD}Artifact types:{RESET} {', '.join(ARTIFACT_TYPES)}")
        print(f"{BOLD}Artifacts root:{RESET} {ARTIFACTS_ROOT}")
        sys.exit(0)
        
    else:
        # Show help if no command specified
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
