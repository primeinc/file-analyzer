#!/usr/bin/env python3
"""
Test hook for pre-commit and CI integration

This module implements the functionality previously in test_hook.sh,
providing a simple hook for testing and CI integration.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console

# Create Typer app for test hook
app = typer.Typer(help="Test hook for pre-commit and CI integration")

# Initialize console for rich output
console = Console()

def get_logger(verbose: bool = False, quiet: bool = False):
    """
    Get the logger for test hook and update log level if needed.
    
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
    Test hook for pre-commit and CI integration.
    
    This command provides a simple hook for testing and CI integration,
    implementing the functionality previously in test_hook.sh.
    """
    pass

@app.command()
def run(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Run the test hook.
    
    Executes a simple test to verify the hook system is working properly.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    console.print("[bold]Running test hook for CI/pre-commit integration[/bold]")
    console.print("This is a test script that can be used as a pre-commit hook.")
    console.print("Hello World")
    
    return 0

if __name__ == "__main__":
    app()