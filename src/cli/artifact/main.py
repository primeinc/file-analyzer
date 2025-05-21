#!/usr/bin/env python3
"""
Artifact management subcommand for the File Analyzer CLI

This module implements the 'artifact' subcommand, which provides a Typer-based
interface to the artifact management functionality previously in cleanup.sh.
"""

import os
import sys
import json
import shutil
import logging
import platform
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Import CLI common utilities
from src.cli.common.config import config
from src.cli.main import console

# Import artifact_guard utilities
from src.core.artifact_guard import (
    ARTIFACTS_ROOT, 
    ARTIFACT_TYPES,
    get_canonical_artifact_path, 
    validate_artifact_path,
    setup_artifact_structure as setup_artifact_dir,
    cleanup_artifacts as cleanup_artifact_dirs
)

# Import script_checks subcommand
from src.cli.artifact.script_checks import app as script_checks_app

# Create Typer app for artifact subcommand
app = typer.Typer(help="Manage artifact directories and outputs")

# Add script_checks subcommand
app.add_typer(script_checks_app, name="script-checks")

def get_logger(verbose: bool = False, quiet: bool = False):
    """
    Get the logger for artifact commands and update log level if needed.
    
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

@app.callback()
def callback():
    """
    Manage artifact directories and outputs.

    The artifact command provides utilities for managing the canonical
    artifact directory structure, creating paths, cleaning up old artifacts,
    and generating reports.
    """
    pass

# Constants from cleanup.sh
CONFIG_FILE = ".artifact-config.json"
LOG_FILE = os.path.join(os.path.dirname(ARTIFACTS_ROOT), "cleanup.log")
DEFAULT_RETENTION_DAYS = 7

def log_message(level: str, message: str):
    """
    Log a message to the log file and console.
    
    Args:
        level: Log level
        message: Message to log
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    # Append to log file
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + "\n")
    
    # Print to console using rich
    if level == "ERROR":
        console.print(f"[red]Error:[/red] {message}")
    elif level == "WARN":
        console.print(f"[yellow]Warning:[/yellow] {message}")
    else:
        console.print(message)

def _get_config_value(config_path: str, key: str, default: Any) -> Any:
    """
    Get a value from a JSON config file.
    
    Args:
        config_path: Path to config file
        key: Key to get
        default: Default value if key not found
        
    Returns:
        Value from config or default
    """
    if not os.path.exists(config_path):
        return default
        
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get(key, default)
    except (json.JSONDecodeError, IOError):
        return default

def _setup_artifact_lock():
    """
    Create a lock file to prevent concurrent cleanup operations.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    # Create the lock file directory
    lock_dir = os.path.join(ARTIFACTS_ROOT, "tmp")
    os.makedirs(lock_dir, exist_ok=True)
    
    # Set lock file path
    lock_file = os.path.join(lock_dir, "file-analyzer-cleanup.lock")
    
    # Check if lock file exists
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
                
            # Check if process is still running
            try:
                if platform.system() == "Windows":
                    # Windows - use tasklist with safer list arguments
                    output = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}"])
                    if str(pid) in output.decode():
                        return False, f"Another cleanup process is already running (PID: {pid})"
                else:
                    # Unix-like - use ps
                    os.kill(pid, 0)  # This will raise OSError if process is not running
                    return False, f"Another cleanup process is already running (PID: {pid})"
            except (OSError, subprocess.SubprocessError):
                # Process not running, remove stale lock
                log_message("WARN", "Removing stale lock file")
                os.unlink(lock_file)
        except (IOError, ValueError):
            # Invalid lock file, remove it
            log_message("WARN", "Removing invalid lock file")
            os.unlink(lock_file)
    
    # Create the lock file with current PID
    with open(lock_file, 'w') as f:
        f.write(str(os.getpid()))
        
    # Register cleanup handler to remove lock file on exit
    import atexit
    atexit.register(lambda: os.unlink(lock_file) if os.path.exists(lock_file) else None)
    
    return True, "Lock acquired"

def clean_tmp_artifacts():
    """
    Clean only the tmp directory.
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    tmp_dir = os.path.join(ARTIFACTS_ROOT, "tmp")
    
    try:
        # Remove all files in tmp directory
        if os.path.exists(tmp_dir):
            for item in os.listdir(tmp_dir):
                item_path = os.path.join(tmp_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.unlink(item_path)
        
        # Recreate empty directory
        os.makedirs(tmp_dir, exist_ok=True)
        return True, "Temporary artifacts cleaned"
    except Exception as e:
        return False, f"Failed to clean temporary artifacts: {str(e)}"

# Import shared utility function
from src.cli.artifact.utils import check_artifact_sprawl

def generate_env_file() -> Tuple[bool, str, str]:
    """
    Generate an artifacts.env file for sourcing in shell scripts.
    
    Returns:
        Tuple[bool, str, str]: (success, file_path, message)
    """
    env_file = os.path.join(os.path.dirname(ARTIFACTS_ROOT), "artifacts.env")
    
    try:
        # Create the file header
        with open(env_file, 'w') as f:
            f.write(f"# Artifact environment variables\n")
            f.write(f"# Source this file to get standard artifact paths\n")
            f.write(f"# Generated by 'fa artifact env-file' on {datetime.datetime.now()}\n\n")
            f.write(f"export ARTIFACTS_ROOT=\"{ARTIFACTS_ROOT}\"\n")
            
            # Add exports for each artifact type
            config_file = os.path.join(ARTIFACTS_ROOT, CONFIG_FILE)
            if os.path.exists(config_file):
                with open(config_file, 'r') as cf:
                    try:
                        config = json.load(cf)
                        structure = config.get("structure", {})
                        
                        for dir_name, description in structure.items():
                            var_name = f"ARTIFACTS_{dir_name.upper()}"
                            dir_path = os.path.join(ARTIFACTS_ROOT, dir_name)
                            f.write(f"export {var_name}=\"{dir_path}\" # {description}\n")
                    except json.JSONDecodeError:
                        # If config file is invalid, just add default directories
                        for dir_name in ARTIFACT_TYPES:
                            var_name = f"ARTIFACTS_{dir_name.upper()}"
                            dir_path = os.path.join(ARTIFACTS_ROOT, dir_name)
                            f.write(f"export {var_name}=\"{dir_path}\"\n")
            else:
                # No config file, just add default directories
                for dir_name in ARTIFACT_TYPES:
                    var_name = f"ARTIFACTS_{dir_name.upper()}"
                    dir_path = os.path.join(ARTIFACTS_ROOT, dir_name)
                    f.write(f"export {var_name}=\"{dir_path}\"\n")
            
            # Add helper functions
            f.write("""
# Helper function to get specific artifact directories
get_artifact_path() {
  local type="$1"
  local name="$2"
  
  case "$type" in
    analysis|vision|test|benchmark|json|tmp)
      dir_var="ARTIFACTS_${type^^}"
      dir_path="${!dir_var}/$name"
      mkdir -p "$dir_path"
      echo "$dir_path"
      ;;
    *)
      echo "Unknown artifact type: $type" >&2
      echo "Valid types: analysis, vision, test, benchmark, json, tmp" >&2
      return 1
      ;;
  esac
}

# Clean temporary artifacts
clean_tmp_artifacts() {
  rm -rf "$ARTIFACTS_TMP"/*
  mkdir -p "$ARTIFACTS_TMP"
}
""")
        
        return True, env_file, f"Generated environment file: {env_file}"
    except Exception as e:
        return False, "", f"Failed to generate environment file: {str(e)}"

@app.command()
def setup(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Set up the artifact directory structure.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Use the setup function from artifact_guard
        setup_artifact_dir()
        
        # Set up config file if it doesn't exist
        config_file = os.path.join(ARTIFACTS_ROOT, CONFIG_FILE)
        if not os.path.exists(config_file):
            config = {
                "retention_days": DEFAULT_RETENTION_DAYS,
                "structure": {
                    "test": "Test outputs and results",
                    "analysis": "File analysis results",
                    "vision": "Vision model analysis outputs",
                    "benchmark": "Performance benchmark results",
                    "json": "JSON validation results",
                    "tmp": "Temporary files (cleared on every run)"
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
        
        # Create .gitignore in each directory
        for artifact_type in ARTIFACT_TYPES:
            type_dir = os.path.join(ARTIFACTS_ROOT, artifact_type)
            gitignore_file = os.path.join(type_dir, ".gitignore")
            if not os.path.exists(gitignore_file):
                with open(gitignore_file, 'w') as f:
                    f.write("*\n")
        
        console.print(f"[green]Artifact directory structure created at:[/green] {ARTIFACTS_ROOT}")
        return 0
    except Exception as e:
        console.print(f"[red]Failed to set up artifact structure:[/red] {str(e)}")
        return 1

@app.command()
def path(
    type_name: str = typer.Argument(
        ..., help="Artifact type (analysis, vision, test, benchmark, json, tmp)"
    ),
    name: str = typer.Argument(
        ..., help="Artifact context name/description"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Get a canonical path in the artifact directory (creates if needed).
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Use the function from artifact_guard
        artifact_path = get_canonical_artifact_path(type_name, name)
        print(artifact_path)  # Print without rich formatting for shell scripts
        return 0
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        return 1
    except Exception as e:
        console.print(f"[red]Failed to create artifact path:[/red] {str(e)}")
        return 1

@app.command("clean")
def clean_artifacts(
    retention_days: int = typer.Option(
        7, "--days", "-d", help="Number of days to keep artifacts"
    ),
    artifact_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Specific artifact type to clean"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Clean up old artifacts based on retention policy.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Acquire lock to prevent concurrent cleanup
        lock_success, lock_message = _setup_artifact_lock()
        if not lock_success:
            console.print(f"[yellow]Warning:[/yellow] {lock_message}")
            return 1
        
        # Get default retention policy
        config_file = os.path.join(ARTIFACTS_ROOT, CONFIG_FILE)
        config_retention = _get_config_value(config_file, "retention_days", DEFAULT_RETENTION_DAYS)
        
        # Use specified retention days or config value
        retention = retention_days or config_retention
        
        log_message("INFO", f"Cleaning artifacts based on retention policies (default: {retention} days)...")
        log_message("INFO", "Using per-manifest retention days when available")
        
        # Use the cleanup function from artifact_guard
        count = cleanup_artifact_dirs(retention, artifact_type)
        
        console.print(f"[green]Cleaned up {count} artifact{'s' if count != 1 else ''}[/green]")
        log_message("INFO", f"Cleaned up {count} artifact{'s' if count != 1 else ''}")
        
        # Always clean tmp directory
        clean_tmp_artifacts()
        
        return 0
    except Exception as e:
        console.print(f"[red]Failed to clean artifacts:[/red] {str(e)}")
        return 1

@app.command("clean-tmp")
def clean_tmp(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Clean only temporary artifacts directory.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        success, message = clean_tmp_artifacts()
        if success:
            console.print(f"[green]{message}[/green]")
            log_message("INFO", message)
        else:
            console.print(f"[red]Error:[/red] {message}")
            log_message("ERROR", message)
            return 1
        
        return 0
    except Exception as e:
        console.print(f"[red]Failed to clean temporary artifacts:[/red] {str(e)}")
        return 1

@app.command()
def report(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Generate a report of current artifacts and disk usage.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        log_message("INFO", "Generating artifact report...")
        
        # Create table for rich output
        table = Table(title="Artifact Report")
        table.add_column("Type", style="blue")
        table.add_column("Size", style="green")
        table.add_column("Artifacts", style="yellow")
        
        # Track total size
        total_size_kb = 0
        
        # Get sizes of each category
        for artifact_type in ARTIFACT_TYPES:
            dir_path = os.path.join(ARTIFACTS_ROOT, artifact_type)
            if not os.path.exists(dir_path):
                continue
                
            # Calculate size more efficiently
            dir_size_kb = 0
            try:
                if platform.system() != "Windows":
                    # Use 'du' on Unix-like systems for better performance
                    result = subprocess.run(
                        ["du", "-sk", dir_path], 
                        capture_output=True, 
                        text=True, 
                        check=True
                    )
                    # Parse the output - first field is size in KB
                    dir_size_kb = int(result.stdout.strip().split()[0])
                else:
                    # Fallback to Python implementation on Windows
                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path) and not os.path.islink(file_path):
                                dir_size_kb += os.path.getsize(file_path) // 1024
            except (subprocess.SubprocessError, ValueError, IndexError):
                # Fallback to Python implementation if du fails
                dir_size_kb = 0
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path) and not os.path.islink(file_path):
                            dir_size_kb += os.path.getsize(file_path) // 1024
            
            # Calculate human-readable size
            if dir_size_kb > 1048576:  # 1 GB in KB
                size_str = f"{dir_size_kb / 1048576:.2f} GB"
            elif dir_size_kb > 1024:  # 1 MB in KB
                size_str = f"{dir_size_kb / 1024:.2f} MB"
            else:
                size_str = f"{dir_size_kb} KB"
            
            # Count artifacts
            artifact_count = len([d for d in os.listdir(dir_path) 
                               if os.path.isdir(os.path.join(dir_path, d)) and not d.startswith('.')])
            
            # Add to table
            table.add_row(artifact_type, size_str, f"{artifact_count} items")
            
            # Add to total
            total_size_kb += dir_size_kb
        
        # Convert total to human readable
        if total_size_kb > 1048576:  # 1 GB in KB
            total_size_str = f"{total_size_kb / 1048576:.2f} GB"
        elif total_size_kb > 1024:  # 1 MB in KB
            total_size_str = f"{total_size_kb / 1024:.2f} MB"
        else:
            total_size_str = f"{total_size_kb} KB"
        
        # Print table
        console.print(table)
        console.print(f"Total size: [bold]{total_size_str}[/bold]")
        
        # Find largest directories
        console.print("\n[bold]Largest artifact directories:[/bold]")
        
        largest_dirs = []
        for artifact_type in ARTIFACT_TYPES:
            type_dir = os.path.join(ARTIFACTS_ROOT, artifact_type)
            if not os.path.exists(type_dir):
                continue
                
            for item in os.listdir(type_dir):
                item_path = os.path.join(type_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    # Calculate size efficiently
                    size_kb = 0
                    try:
                        if platform.system() != "Windows":
                            # Use 'du' on Unix-like systems for better performance
                            result = subprocess.run(
                                ["du", "-sk", item_path], 
                                capture_output=True, 
                                text=True, 
                                check=True
                            )
                            # Parse the output - first field is size in KB
                            size_kb = int(result.stdout.strip().split()[0])
                        else:
                            # Fallback to Python implementation on Windows
                            for root, dirs, files in os.walk(item_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    if os.path.exists(file_path) and not os.path.islink(file_path):
                                        size_kb += os.path.getsize(file_path) // 1024
                    except (subprocess.SubprocessError, ValueError, IndexError):
                        # Fallback to Python implementation if du fails
                        size_kb = 0
                        for root, dirs, files in os.walk(item_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path) and not os.path.islink(file_path):
                                    size_kb += os.path.getsize(file_path) // 1024
                    
                    largest_dirs.append((item_path, size_kb))
        
        # Sort by size (largest first) and take top 5
        largest_dirs.sort(key=lambda x: x[1], reverse=True)
        for dir_path, size_kb in largest_dirs[:5]:
            # Calculate human-readable size
            if size_kb > 1048576:  # 1 GB in KB
                size_str = f"{size_kb / 1048576:.2f} GB"
            elif size_kb > 1024:  # 1 MB in KB
                size_str = f"{size_kb / 1024:.2f} MB"
            else:
                size_str = f"{size_kb} KB"
                
            console.print(f"{size_str.ljust(10)} {dir_path}")
        
        return 0
    except Exception as e:
        console.print(f"[red]Failed to generate artifact report:[/red] {str(e)}")
        return 1

@app.command()
def check(
    path: str = typer.Argument(
        ".", help="Directory to check for artifact sprawl"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Check for artifact sprawl outside the canonical structure.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        log_message("INFO", f"Checking for artifact sprawl in {path}...")
        
        no_sprawl, sprawl_paths = check_artifact_sprawl(path)
        
        if no_sprawl:
            console.print("\n[green][bold]No Artifact Sprawl Detected[/bold][/green]")
            console.print("All artifacts appear to be in the canonical structure.")
            log_message("INFO", "No artifact sprawl detected")
        else:
            console.print("\n[red][bold]Artifact Sprawl Detected[/bold][/red]")
            console.print("=======================")
            console.print("[yellow]The following directories outside the canonical artifact structure were found:[/yellow]")
            for sprawl_path in sprawl_paths:
                console.print(sprawl_path)
            
            log_message("WARN", f"Artifact sprawl detected: {len(sprawl_paths)} directories")
            return 1
        
        return 0
    except Exception as e:
        console.print(f"[red]Failed to check for artifact sprawl:[/red] {str(e)}")
        return 1

@app.command()
def env(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Print environment variables for artifact directories.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        console.print("[bold]Artifact Environment[/bold]")
        console.print("====================")
        console.print(f"[blue]ARTIFACTS_ROOT[/blue]={ARTIFACTS_ROOT}")
        
        # Print each artifact type directory
        config_file = os.path.join(ARTIFACTS_ROOT, CONFIG_FILE)
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    structure = config.get("structure", {})
                    
                    for dir_name, description in structure.items():
                        var_name = f"ARTIFACTS_{dir_name.upper()}"
                        dir_path = os.path.join(ARTIFACTS_ROOT, dir_name)
                        console.print(f"[blue]{var_name}[/blue]={dir_path} [yellow]# {description}[/yellow]")
            except json.JSONDecodeError:
                # If config file is invalid, just print the directories
                for artifact_type in ARTIFACT_TYPES:
                    var_name = f"ARTIFACTS_{artifact_type.upper()}"
                    dir_path = os.path.join(ARTIFACTS_ROOT, artifact_type)
                    console.print(f"[blue]{var_name}[/blue]={dir_path}")
        else:
            # No config file, just print the directories
            for artifact_type in ARTIFACT_TYPES:
                var_name = f"ARTIFACTS_{artifact_type.upper()}"
                dir_path = os.path.join(ARTIFACTS_ROOT, artifact_type)
                console.print(f"[blue]{var_name}[/blue]={dir_path}")
        
        console.print("\n[bold]Source the artifacts.env file in your scripts:[/bold]")
        console.print("source ./artifacts.env")
        
        return 0
    except Exception as e:
        console.print(f"[red]Failed to print environment variables:[/red] {str(e)}")
        return 1

@app.command("env-file")
def env_file(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Generate an artifacts.env file for sourcing in shell scripts.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        success, file_path, message = generate_env_file()
        
        if success:
            console.print(f"[green]{message}[/green]")
        else:
            console.print(f"[red]Error:[/red] {message}")
            return 1
        
        return 0
    except Exception as e:
        console.print(f"[red]Failed to generate environment file:[/red] {str(e)}")
        return 1

@app.command("validate")
def validate(
    path: str = typer.Argument(..., help="Path to validate"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Validate a path against artifact discipline with detailed feedback.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Validate path against artifact discipline
        is_valid = validate_artifact_path(path)
        
        if is_valid:
            console.print(f"[green]Path IS valid according to artifact discipline.[/green]")
            return 0
        else:
            # Get absolute path for better checking
            project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            abs_path = os.path.abspath(path)
            
            # Provide more specific reasons why the path is invalid
            console.print(f"[red]Path is NOT valid according to artifact discipline:[/red]")
            
            # Check if it's a system directory
            if path.startswith('/tmp') or path.startswith('/var/tmp'):
                console.print(f"[red]ERROR:[/red] Path is a system temporary directory. Use canonical artifact paths instead.")
                console.print(f"  Use: get_canonical_artifact_path(\"tmp\", \"your_context\") for temporary files.")
            
            # Check if it's attempting path traversal
            elif '..' in path:
                console.print(f"[red]ERROR:[/red] Path contains parent directory references (..) which is not allowed.")
                console.print(f"  Use absolute paths within the canonical artifact structure.")
            
            # Check if it's outside project directory
            elif not path.startswith('/') and not abs_path.startswith(project_root):
                console.print(f"[red]ERROR:[/red] Path is outside the project directory structure.")
                
            # Check if it's using a legacy pattern
            elif any(pattern in path for pattern in ['analysis_results', 'vision_results']):
                console.print(f"[red]ERROR:[/red] Path uses a legacy pattern that is not compatible with artifact discipline.")
                console.print(f"  Replace legacy paths with canonical artifact paths.")
            
            # Check if it's in artifacts directory but not following canonical structure
            elif path.startswith(ARTIFACTS_ROOT) and not any(f"/{t}/" in path for t in ARTIFACT_TYPES):
                console.print(f"[red]ERROR:[/red] Path is in artifacts directory but doesn't follow canonical type structure.")
                console.print(f"  Canonical paths must include a valid type: {', '.join(ARTIFACT_TYPES)}")
            
            # General guidance
            console.print(f"\n[yellow]Valid paths must be within:[/yellow]")
            console.print(f"1. {ARTIFACTS_ROOT} and follow canonical naming")
            console.print(f"2. {project_root}/src, {project_root}/tools, {project_root}/tests")
            console.print(f"3. Standard files in project root directory")
            
            console.print(f"\n[yellow]Example of valid canonical path:[/yellow]")
            console.print(f"  {get_canonical_artifact_path('test', 'example_context')}")
            
            return 1
    
    except Exception as e:
        console.print(f"[red]Failed to validate path:[/red] {str(e)}")
        return 1

@app.command("info")
def info(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Show information about artifact discipline and project structure.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Get project root directory
        project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
        # Display project structure
        console.print(f"\n[bold green]Project Structure:[/bold green]")
        console.print(f"  ├── [green]src/[/green]      - Core Python modules and libraries")
        console.print(f"  ├── [green]tools/[/green]    - Command-line tools and utilities")
        console.print(f"  ├── [green]tests/[/green]    - Test scripts and validation")
        console.print(f"  └── [green]artifacts/[/green] - Canonical output storage")
        console.print(f"      ├── analysis/   - Analysis results")
        console.print(f"      ├── vision/     - Vision model outputs")
        console.print(f"      ├── test/       - Test outputs")
        console.print(f"      ├── benchmark/  - Performance benchmarks")
        console.print(f"      └── tmp/        - Temporary files (auto-cleaned)")
        
        # Warn about artifact discipline
        console.print(f"\n[bold yellow]Artifact Discipline Warning:[/bold yellow]")
        console.print("Remember that while artifact_guard.py provides protection via PathGuard and decorators,")
        console.print("direct file operations may bypass this protection.")
        console.print("")
        console.print("For full artifact discipline, ensure all files are created within canonical directories")
        console.print("obtained via [bold]get_canonical_artifact_path()[/bold].")
        
        console.print(f"\n[bold]Example:[/bold]")
        console.print("  # Get a canonical artifact path")
        console.print("  from src.artifact_guard import get_canonical_artifact_path, PathGuard")
        console.print("  ")
        console.print("  # Create canonical path")
        console.print("  artifact_dir = get_canonical_artifact_path(\"test\", \"my_test_context\")")
        console.print("  ")
        console.print("  # Use PathGuard to enforce discipline")
        console.print("  with PathGuard(artifact_dir):")
        console.print("      with open(os.path.join(artifact_dir, \"output.txt\"), \"w\") as f:")
        console.print("          f.write(\"Test output\")")
        
        # Print artifact types and root
        console.print(f"\n[bold]Artifact types:[/bold] {', '.join(ARTIFACT_TYPES)}")
        console.print(f"[bold]Artifacts root:[/bold] {ARTIFACTS_ROOT}")
        
        return 0
    except Exception as e:
        console.print(f"[red]Failed to display information:[/red] {str(e)}")
        return 1

if __name__ == "__main__":
    app()