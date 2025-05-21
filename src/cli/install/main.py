#!/usr/bin/env python3
"""
Installation subcommand for the File Analyzer CLI

This module implements the 'install' subcommand, which provides a Typer-based
interface to the installation functionality previously in install.sh.
"""

import os
import sys
import shutil
import logging
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

# Import CLI common utilities
from src.cli.common.config import config
from src.cli.main import console

# Create Typer app for install subcommand
app = typer.Typer(help="Install the File Analyzer tools")

def get_logger(verbose: bool = False, quiet: bool = False):
    """
    Get the logger for install commands and update log level if needed.
    
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
    # Assuming this file is in src/cli/install/main.py
    return Path(__file__).parent.parent.parent.parent.absolute()

@app.callback()
def callback():
    """
    Install the File Analyzer tools.
    
    The install command provides utilities for installing the File Analyzer
    tools to a specified directory, creating symbolic links for easy access.
    """
    pass

@app.command()
def run(
    install_dir: Optional[str] = typer.Argument(
        None, help="Installation directory. If not provided, defaults to ~/bin"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Install the File Analyzer tools to the specified directory.
    
    Creates symbolic links for the analyzer tools in the target directory.
    If no directory is specified, it will install to $HOME/bin by default.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Default installation directory
    if not install_dir:
        install_dir = os.path.join(os.environ.get("HOME", "~"), "bin")
    
    # Create installation directory if it doesn't exist
    try:
        os.makedirs(install_dir, exist_ok=True)
    except OSError as e:
        console.print(f"[red]Error:[/red] Installation directory {install_dir} could not be created: {e}")
        return 1
    
    # Check if directory is writable
    if not os.access(install_dir, os.W_OK):
        console.print(f"[red]Error:[/red] Installation directory {install_dir} is not writable")
        return 1
    
    # Get absolute path to source directory
    project_root = get_project_root()
    
    # Create symbolic links for the analyzer tools
    try:
        # For tools/analyze.sh (now replaced by Python CLI)
        analyze_link_path = os.path.join(install_dir, "analyze-files")
        if os.path.exists(analyze_link_path) and os.path.islink(analyze_link_path):
            os.unlink(analyze_link_path)
        os.symlink(os.path.join(project_root, "src", "cli", "main.py"), analyze_link_path)
        
        # For the main CLI 'fa' command
        fa_link_path = os.path.join(install_dir, "fa")
        if os.path.exists(fa_link_path) and os.path.islink(fa_link_path):
            os.unlink(fa_link_path)
        os.symlink(os.path.join(project_root, "src", "cli", "main.py"), fa_link_path)
        
        # Make the Python scripts executable
        main_script = os.path.join(project_root, "src", "cli", "main.py")
        os.chmod(main_script, os.stat(main_script).st_mode | 0o755)
    except OSError as e:
        console.print(f"[red]Error creating symlinks:[/red] {e}")
        return 1
    
    # Check if installation was successful
    if (os.path.islink(os.path.join(install_dir, "analyze-files")) and 
        os.path.islink(os.path.join(install_dir, "fa"))):
        console.print("[green]Installation successful![/green]")
        console.print("The following commands are now available:")
        console.print("  - analyze-files: Legacy command for backwards compatibility")
        console.print("  - fa: Main CLI command")
        
        # Check if installation directory is in PATH
        paths = os.environ.get("PATH", "").split(os.pathsep)
        if install_dir not in paths:
            console.print("\n[yellow]WARNING:[/yellow] Installation directory is not in your PATH.")
            console.print("Add the following line to your ~/.bashrc or ~/.zshrc file:")
            console.print(f'  export PATH="{install_dir}:$PATH"')
        
        return 0
    else:
        console.print("[red]Installation failed.[/red]")
        return 1

if __name__ == "__main__":
    app()