#!/usr/bin/env python3
"""
Script conformity checks for shell scripts in the project.

This module implements functionality to check shell scripts for proper
artifact discipline, replacing the check_script_conformity.sh script.
"""

import os
import re
import glob
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import typer
from rich.console import Console
from rich.table import Table

# Create Typer app for script checks subcommand
app = typer.Typer(help="Check shell scripts for artifact discipline")

# Constants
GUARD_SCRIPT = "artifact_guard_py_adapter.sh"
ALLOWED_UNSOURCED = [
    GUARD_SCRIPT,
    "preflight.sh", 
    "cleanup.sh", 
    "check_script_conformity.sh", 
    "artifacts.env", 
    "check_all_scripts.sh", 
    "install.sh"
]

# Initialize console
console = Console()
logger = logging.getLogger("file-analyzer")

def get_project_root() -> Path:
    """Get the project root directory."""
    # Assuming this file is in src/cli/artifact/script_checks.py
    return Path(__file__).parent.parent.parent.parent.absolute()

def check_script(script_path: str) -> Tuple[bool, str]:
    """
    Check if a shell script properly sources artifact_guard_py_adapter.sh.
    
    Args:
        script_path: Path to the shell script to check
        
    Returns:
        Tuple[bool, str]: (pass_status, message)
    """
    script_name = os.path.basename(script_path)
    
    # Skip scripts that are allowed to not source the guard
    if script_name in ALLOWED_UNSOURCED:
        return True, f"EXEMPT: {script_path} (exempt from sourcing requirement)"
    
    # Skip scripts in the libs/ directory
    if "/libs/" in script_path:
        return True, f"EXEMPT: {script_path} (in libs/ directory - external library)"
    
    # Look for any sourcing of artifact_guard.sh or artifact_guard_py_adapter.sh in the script
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Regular expression to match source or . command for artifact_guard(_py_adapter)?.sh
    if re.search(r'^(source|\.) +.*artifact_guard(_py_adapter)?\.sh', content, re.MULTILINE):
        return True, f"PASS: {script_path}"
    else:
        return False, f"FAIL: {script_path} (does not source artifact_guard.sh or artifact_guard_py_adapter.sh)"

def find_all_scripts() -> List[str]:
    """
    Find all shell scripts in the project.
    
    Returns:
        List[str]: List of shell script paths
    """
    project_root = get_project_root()
    all_scripts = []
    
    # Use glob to find all .sh files
    for script_path in sorted(glob.glob(str(project_root) + "/**/*.sh", recursive=True)):
        all_scripts.append(script_path)
    
    return all_scripts

def check_multiple_scripts(scripts: List[str]) -> Tuple[int, int, List[str]]:
    """
    Check multiple scripts for artifact discipline.
    
    Args:
        scripts: List of script paths to check
        
    Returns:
        Tuple[int, int, List[str]]: (total, failures, failure_messages)
    """
    total = 0
    failures = 0
    failure_messages = []
    
    # Create a table for results
    table = Table(title="Script Conformity Check Results")
    table.add_column("Status", style="bold")
    table.add_column("Script", style="cyan")
    table.add_column("Message", style="yellow")
    
    for script in scripts:
        passed, message = check_script(script)
        
        # Extract script path relative to project root for cleaner display
        project_root = str(get_project_root())
        rel_path = script
        if script.startswith(project_root):
            rel_path = script[len(project_root):].lstrip('/')
            
        if passed:
            if "EXEMPT" in message:
                status_style = "[yellow]EXEMPT[/yellow]"
            else:
                status_style = "[green]PASS[/green]"
        else:
            status_style = "[red]FAIL[/red]"
            failures += 1
            failure_messages.append(message)
        
        table.add_row(status_style, rel_path, message.split(": ", 1)[1] if ": " in message else "")
        total += 1
    
    # Print the table
    console.print(table)
    
    # Print summary
    console.print(f"\n[bold]Total scripts checked:[/bold] {total}")
    console.print(f"[bold]Conforming scripts:[/bold] {total - failures}")
    console.print(f"[bold]Non-conforming scripts:[/bold] {failures}")
    
    return total, failures, failure_messages

@app.callback()
def callback():
    """
    Check shell scripts for proper artifact discipline.
    
    Enforces the requirement that all shell scripts must source
    artifact_guard_py_adapter.sh for proper artifact path discipline.
    """
    pass

@app.command("check")
def check_scripts(
    scripts: List[str] = typer.Argument(
        None, help="List of shell scripts to check. If not provided, all scripts will be checked."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Check shell scripts for proper artifact discipline.
    
    Validates that all shell scripts source artifact_guard_py_adapter.sh
    to ensure proper artifact path discipline is enforced.
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else (logging.ERROR if quiet else logging.INFO)
    logging.basicConfig(level=log_level)
    
    try:
        scripts_to_check = []
        
        # If specific scripts were provided, check them
        if scripts:
            for script in scripts:
                # Resolve to absolute path if needed
                if not os.path.isabs(script):
                    script = os.path.join(os.getcwd(), script)
                
                # Verify it's a shell script
                if not os.path.isfile(script) or not script.endswith('.sh'):
                    console.print(f"[red]Error:[/red] {script} is not a shell script or does not exist.")
                    continue
                
                scripts_to_check.append(script)
        else:
            # Otherwise check all scripts
            console.print("[bold]Checking all shell scripts for artifact_guard_py_adapter.sh sourcing:[/bold]")
            scripts_to_check = find_all_scripts()
        
        # Perform the checks
        total, failures, failure_messages = check_multiple_scripts(scripts_to_check)
        
        if failures > 0:
            console.print("\n[red][bold]ERROR:[/bold][/red] Some scripts do not conform to artifact discipline requirements.")
            console.print("Each script must source artifact_guard_py_adapter.sh immediately after the shebang line.")
            console.print("Example:")
            console.print("#!/bin/bash")
            console.print('source "$(dirname "${BASH_SOURCE[0]}")/artifact_guard_py_adapter.sh"')
            return 1
        else:
            console.print("\n[green][bold]SUCCESS:[/bold][/green] All scripts conform to artifact discipline requirements.")
            return 0
    
    except Exception as e:
        console.print(f"[red]Error during script check:[/red] {str(e)}")
        return 1

@app.command("all")
def check_all_scripts(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Check all scripts in src, tools, and tests directories.
    
    Equivalent to the check_all_scripts.sh functionality.
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else (logging.ERROR if quiet else logging.INFO)
    logging.basicConfig(level=log_level)
    
    try:
        console.print("[bold]Checking all scripts in src, tools, and tests directories...[/bold]")
        
        # Get paths to check
        project_root = get_project_root()
        scripts_to_check = []
        
        # Add tools scripts
        tools_scripts = glob.glob(str(project_root / "tools" / "*.sh"))
        scripts_to_check.extend(tools_scripts)
        
        # Add tests scripts
        tests_scripts = glob.glob(str(project_root / "tests" / "*.sh"))
        scripts_to_check.extend(tests_scripts)
        
        # Add root scripts
        root_scripts = glob.glob(str(project_root / "*.sh"))
        scripts_to_check.extend(root_scripts)
        
        # Perform the checks
        total, failures, failure_messages = check_multiple_scripts(scripts_to_check)
        
        if failures > 0:
            console.print("\n[red][bold]ERROR:[/bold][/red] Some scripts do not conform to artifact discipline requirements.")
            return 1
        else:
            console.print("\n[green][bold]SUCCESS:[/bold][/green] All critical scripts conform to artifact discipline requirements!")
            return 0
    
    except Exception as e:
        console.print(f"[red]Error during script check:[/red] {str(e)}")
        return 1

if __name__ == "__main__":
    app()