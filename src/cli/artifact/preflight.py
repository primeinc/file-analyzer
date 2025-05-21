#!/usr/bin/env python3
"""
Preflight checks for the File Analyzer

This module implements the preflight check functionality, which was previously
in preflight.sh. It validates the repository state before test execution:
1. Enforces canonical artifact structure
2. Detects and reports rogue artifacts outside canonical paths
3. Enforces clean state requirements
4. Fails build if artifact discipline is violated
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import CLI common utilities
from src.cli.common.config import config
from src.cli.main import console

# Import artifact_guard utilities
from src.core.artifact_guard import (
    ARTIFACTS_ROOT, 
    ARTIFACT_TYPES,
    setup_artifact_structure,
    get_canonical_artifact_path
)

# Import script_checks functionality
from src.cli.artifact.script_checks import check_script, find_all_scripts

# Create Typer app for preflight subcommand
app = typer.Typer(
    help="Perform preflight checks for artifact discipline and repository state"
)

def get_logger(verbose: bool = False, quiet: bool = False):
    """
    Get the logger for preflight commands and update log level if needed.
    
    Args:
        verbose: Enable verbose output
        quiet: Suppress all output except errors
        
    Returns:
        Logger instance
    """
    # Import the setup_logging function from main module
    from src.cli.main import setup_logging
    
    # Update the logging configuration based on current verbose/quiet flags
    _, logger = setup_logging(verbose=verbose, quiet=quiet)
    return logger

def get_project_root() -> Path:
    """Get the project root directory."""
    # Assuming this file is in src/cli/artifact/preflight.py
    return Path(__file__).parent.parent.parent.parent.absolute()

# Import shared utility function
from src.cli.artifact.utils import check_artifact_sprawl

def check_scripts_conformity() -> Tuple[bool, List[str]]:
    """
    Check shell scripts for proper artifact discipline.
    
    Returns:
        Tuple[bool, List[str]]: (all_conforming, failures)
    """
    # List of scripts exempt from the sourcing requirement
    exempt_scripts = [
        "artifact_guard_py_adapter.sh",
        "preflight.sh",
        "install.sh",
        "check_script_conformity.sh",
        "check_all_scripts.sh"
    ]
    
    # Find all shell scripts
    all_scripts = find_all_scripts()
    
    # Check each script
    failures = []
    for script in all_scripts:
        # Skip third-party scripts in libs/ directory
        if "/libs/" in script:
            continue
            
        # Skip explicitly exempted scripts
        script_name = os.path.basename(script)
        if script_name in exempt_scripts:
            continue
        
        # Check if script sources artifact_guard_py_adapter.sh
        passed, message = check_script(script)
        if not passed:
            failures.append(script)
    
    return len(failures) == 0, failures

# Import functions from main module
from src.cli.artifact.main import clean_tmp_artifacts as main_clean_tmp_artifacts

def clean_tmp_artifacts():
    """
    Clean only the tmp directory.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        # Directly call the function from main module
        success, message = main_clean_tmp_artifacts()
        return success, message
    except Exception as e:
        return False, f"Failed to clean temporary artifacts: {str(e)}"

# Also import generate_env_file
from src.cli.artifact.main import generate_env_file as main_generate_env_file

def generate_env_file():
    """
    Generate an artifacts.env file for sourcing in shell scripts.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        # Directly call the function from main module
        success, file_path, message = main_generate_env_file()
        return success, message
    except Exception as e:
        return False, f"Failed to generate artifacts.env file: {str(e)}"

@app.callback()
def callback():
    """
    Perform preflight checks for artifact discipline and repository state.
    
    The preflight command validates the repository state before test execution,
    enforcing canonical artifact structure and clean state requirements.
    """
    pass

@app.command()
def run(
    no_enforce: bool = typer.Option(
        False, "--no-enforce", help="Don't fail on artifact sprawl (DISCOURAGED)"
    ),
    no_tmp_clean: bool = typer.Option(
        False, "--no-tmp-clean", help="Don't clean the tmp directory"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Run all preflight checks to ensure repository is in a valid state.
    
    Validates the repository state before test execution:
    1. Enforces canonical artifact structure
    2. Detects and reports rogue artifacts outside canonical paths
    3. Enforces clean state requirements
    4. Fails build if artifact discipline is violated
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    enforce = not no_enforce
    clean_tmp = not no_tmp_clean
    
    # Print header
    console.print(Panel.fit(
        "[bold]File Analyzer Preflight Checks[/bold]",
        border_style="blue"
    ))
    
    # Ensure artifact directory structure exists
    if not os.path.isdir(ARTIFACTS_ROOT):
        console.print("[yellow]Creating artifact directory structure...[/yellow]")
        setup_artifact_structure()
    
    # Always clean the tmp directory for a fresh start
    if clean_tmp:
        console.print("[yellow]Cleaning temporary artifact directory...[/yellow]")
        success, message = clean_tmp_artifacts()
        if not success:
            console.print(f"[red]Error:[/red] {message}")
    
    # Check for scripts without artifact_guard_py_adapter.sh sourcing
    console.print("\n[bold]Checking scripts for artifact_guard_py_adapter.sh sourcing:[/bold]")
    all_scripts_conforming, failing_scripts = check_scripts_conformity()
    
    if all_scripts_conforming:
        console.print("[green][bold]SUCCESS:[/bold][/green] All scripts conform to artifact discipline requirements.")
    else:
        console.print(f"[red][bold]ERROR:[/bold][/red] Found {len(failing_scripts)} scripts without artifact_guard_py_adapter.sh sourcing!")
        
        # Print the failing scripts
        for script in failing_scripts:
            console.print(f"[red]✗[/red] {script}")
        
        if enforce:
            console.print("[red][bold]ERROR: Scripts must be updated to use artifact_guard_py_adapter.sh[/bold][/red]")
            return 1
    
    # Check for artifact sprawl
    console.print("\n[bold]Checking for artifact sprawl...[/bold]")
    
    # Direct call to check_artifact_sprawl function (already imported above)
    no_sprawl, sprawl_paths = check_artifact_sprawl(check_dir=".")
    
    # Display the results
    if no_sprawl:
        console.print("\n[green][bold]No Artifact Sprawl Detected[/bold][/green]")
        console.print("All artifacts appear to be in the canonical structure.")
    else:
        console.print("\n[red][bold]Artifact Sprawl Detected[/bold][/red]")
        console.print("=======================")
        console.print("[yellow]The following directories outside the canonical artifact structure were found:[/yellow]")
        for sprawl_path in sprawl_paths:
            console.print(sprawl_path)
        
        if enforce:
            console.print("[red][bold]Error: Artifact sprawl detected.[/bold][/red]")
            return 1
    
    # Check presence of artifact.env and make sure all required scripts update it
    if not os.path.isfile(os.path.join(get_project_root(), "artifacts.env")):
        console.print("[yellow]Generating artifacts.env file...[/yellow]")
        success, message = generate_env_file()
        if not success:
            console.print(f"[red]Error:[/red] {message}")
    else:
        console.print("[green]✓ artifacts.env file exists[/green]")
    
    # Success message
    console.print("\n[green][bold]Preflight check completed successfully.[/bold][/green]")
    console.print("[bold]IMPORTANT:[/bold] All scripts must:")
    console.print("1. Source [yellow]artifact_guard_py_adapter.sh[/yellow] or import [yellow]src.core.artifact_guard[/yellow]")
    console.print("2. Use [yellow]get_canonical_artifact_path <type> \"context\"[/yellow] for generating paths")
    console.print("3. Write all files in canonical locations with manifests")
    console.print("4. NOT bypass the artifact guard with manual paths")
    console.print("")
    console.print("Run [bold]python -m src.cli.artifact.main --help[/bold] for more options.")
    
    return 0

if __name__ == "__main__":
    app()