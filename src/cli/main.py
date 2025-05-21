#!/usr/bin/env python3
"""
File Analyzer CLI: Main entry point

This module provides the main CLI interface for the File Analyzer tool,
implementing a plugin-based architecture for subcommands.
"""

import logging
import sys
import os
import platform
from importlib.metadata import entry_points
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

# Initialize the main Typer app
app = typer.Typer(
    help="File Analyzer CLI: Analyze, test, and validate file processing",
    add_completion=True,
)

# Initialize a default console for use outside of the main CLI flow
console = Console()

def setup_logging(verbose: bool = False, json_logs: bool = False, log_file: Optional[str] = None, no_color: bool = False) -> Console:
    """
    Configure logging based on CLI options.
    
    Args:
        verbose: Enable verbose logging
        json_logs: Output logs in JSON format
        log_file: Optional path to log file
        no_color: Disable colored output
        
    Returns:
        Console: The configured console instance
    """
    # Create console with appropriate color settings
    configured_console = Console(color_system=None if no_color else "auto")
    
    log_level = logging.DEBUG if verbose else logging.INFO
    
    if json_logs:
        # Configure JSON logging
        import json_log_formatter
        formatter = json_log_formatter.JSONFormatter()
        
        # Create a handler for JSON logs
        if log_file:
            handler = logging.FileHandler(log_file)
        else:
            handler = logging.StreamHandler()
            
        handler.setFormatter(formatter)
        logging.basicConfig(level=log_level, handlers=[handler])
    else:
        # Configure rich colored logging
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=configured_console, rich_tracebacks=True)] 
        )
    
    logger = logging.getLogger("file-analyzer")
    
    # Update the global console reference for modules that access it directly
    global console
    console = configured_console
    
    return configured_console, logger

def load_commands():
    """
    Discover and load commands registered under 'fa.commands' entry point.
    """
    logger = logging.getLogger("file-analyzer")
    
    try:
        # Discover entry points
        discovered_commands = entry_points(group='fa.commands')
        
        for entry in discovered_commands:
            try:
                command_app = entry.load()  # Loads the Typer app object
                app.add_typer(command_app, name=entry.name)
                logger.debug(f"Registered command group: {entry.name}")
            except Exception as e:
                logger.error(f"Failed to load command plugin '{entry.name}': {e}")
    except Exception as e:
        logger.warning(f"Error discovering plugins: {e}")
        # Fallback to direct imports if entry points discovery fails
        logger.debug("Using direct imports for commands")
        _import_builtin_commands()

def _import_builtin_commands():
    """
    Import built-in commands directly as a fallback if entry points discovery fails.
    """
    logger = logging.getLogger("file-analyzer")
    
    try:
        # Attempt to import the analyze command
        from src.cli.analyze.main import app as analyze_app
        app.add_typer(analyze_app, name="analyze")
        logger.debug("Registered analyze command")
    except ImportError:
        logger.warning("Could not import analyze command")
    
    try:
        # Attempt to import the test command
        from src.cli.test.main import app as test_app
        app.add_typer(test_app, name="test")
        logger.debug("Registered test command")
    except ImportError:
        logger.warning("Could not import test command")
        
    try:
        # Attempt to import the validate command
        from src.cli.validate.main import app as validate_app
        app.add_typer(validate_app, name="validate")
        logger.debug("Registered validate command")
    except ImportError:
        logger.warning("Could not import validate command")

def capture_environment():
    """Capture and return environment details."""
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "os_name": os.name,
        "user": os.getenv("USER", "unknown"),
        "pwd": os.getcwd(),
    }

@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all output except errors"),
    ci: bool = typer.Option(False, "--ci", help="Run in non-interactive CI mode"),
    log_json: bool = typer.Option(False, "--log-json", help="Output logs in JSON format"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Path to log file"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
):
    """
    File Analyzer: A unified tool for comprehensive file analysis.
    
    Combines multiple specialized tools:
    - ExifTool: Metadata extraction 
    - rdfind: Duplicate detection
    - Tesseract OCR: Text from images
    - ClamAV: Malware scanning  
    - ripgrep: Content searching
    - binwalk: Binary analysis
    - Vision Models: AI-powered image analysis
    """
    # Show version and exit if requested
    if version:
        from importlib.metadata import version as get_version
        try:
            v = get_version("file-analyzer")
            typer.echo(f"File Analyzer CLI v{v}")
        except:
            typer.echo("File Analyzer CLI (version unknown)")
        raise typer.Exit()
    
    # Set up logging based on verbosity
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
        
    # Configure logging and console with color settings
    configured_console, logger = setup_logging(
        verbose=verbose and not quiet,
        json_logs=log_json,
        log_file=log_file,
        no_color=no_color
    )
    
    # Capture environment for debugging/reproducibility
    env_info = capture_environment()
    logger.debug(f"Environment: {env_info}")
    
    # Load subcommands
    load_commands()

# Add version command as a simple alternative to --version
@app.command()
def version():
    """Show version information."""
    # Global console is already initialized at module level
    from importlib.metadata import version as get_version
    try:
        v = get_version("file-analyzer")
        console.print(f"File Analyzer CLI v{v}")
    except:
        console.print("File Analyzer CLI (version unknown)")
    
    # Show Python version
    console.print(f"Python {sys.version}")

if __name__ == "__main__":
    app()