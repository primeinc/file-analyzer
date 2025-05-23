#!/usr/bin/env python3
"""
File Analyzer CLI: Main entry point

This module provides the main CLI interface for the File Analyzer tool,
implementing a clean command structure with proper help system.
"""

import logging
import sys
import os
import platform
import importlib
from importlib.metadata import entry_points, version as get_version
from typing import Optional, Tuple, List, Dict

import typer
from rich.console import Console
from rich.logging import RichHandler

# Initialize the main Typer app
app = typer.Typer(
    help="File Analyzer CLI: Analyze, test, and validate file processing",
    add_completion=True,
    no_args_is_help=True,
)

# Initialize a default console for use outside of the main CLI flow
console = Console()

def setup_logging(verbose: bool = False, quiet: bool = False, json_logs: bool = False, log_file: Optional[str] = None, 
               no_color: bool = False, ci: bool = False) -> Tuple[Console, logging.Logger]:
    """
    Configure logging based on CLI options.
    
    Args:
        verbose: Enable verbose logging
        quiet: Suppress all output except errors
        json_logs: Output logs in JSON format
        log_file: Optional path to log file
        no_color: Disable colored output
        ci: Run in CI mode (disables animations and colors)
        
    Returns:
        tuple[Console, Logger]: The configured console and logger instances
    """
    # Create console with appropriate color settings
    # CI mode disables animations and potentially colors
    console_options = {
        "color_system": None if no_color or ci else "auto",
        "highlight": not ci,
    }
    
    # Create a console instance for this specific logging setup
    log_console = Console(**console_options)
    
    # Determine log level
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    # Setup logging configuration
    handlers = []
    
    # Console handler with Rich formatting
    if not quiet:
        console_handler = RichHandler(
            console=log_console,
            show_path=verbose,
            show_time=verbose,
            rich_tracebacks=True,
            markup=True
        )
        console_handler.setLevel(log_level)
        handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always debug level for file
        
        if json_logs:
            try:
                from pythonjsonlogger import jsonlogger
                formatter = jsonlogger.JsonFormatter(
                    '%(asctime)s %(name)s %(levelname)s %(message)s'
                )
            except ImportError:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Create and return a logger for the CLI
    logger = logging.getLogger("file-analyzer")
    logger.debug(f"Logging configured: level={log_level}, quiet={quiet}, verbose={verbose}")
    
    return log_console, logger

@app.command()
def quick(
    file_path: str = typer.Argument(..., help="Path to file to analyze"),
    output_format: str = typer.Option("pretty", "--format", "-f", help="Output format: pretty, json, md"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    markdown_output: bool = typer.Option(False, "--md", help="Output in Markdown format"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed logging"),
):
    """
    Quick analysis of a single file with vision AI.
    
    This command provides fast AI-powered analysis of a single file,
    optimized for speed and convenience.
    """
    # Setup logging first
    setup_console, logger = setup_logging(verbose=verbose)
    
    # Handle format flags
    if json_output:
        output_format = "json"
    elif markdown_output:
        output_format = "md"
    
    # BANNED: Manual imports from other CLI modules
    # Quick command must be self-contained
    typer.echo("Error: Quick analysis not available - use 'fa analyze vision' instead", err=True)
    raise typer.Exit(1)

@app.command()
def direct(
    file_path: str = typer.Argument(..., help="Path to file to analyze"),
    output_format: str = typer.Option("pretty", "--format", "-f", help="Output format: pretty, json, md"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    markdown_output: bool = typer.Option(False, "--md", help="Output in Markdown format"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Direct file analysis (equivalent to 'fa <filepath>').
    
    This is the same functionality as the quick command, provided
    for compatibility with the 'fa <filepath>' syntax.
    """
    # BANNED: Manual imports from other CLI modules
    typer.echo("Error: Direct analysis not available - use 'fa analyze vision' instead", err=True)
    raise typer.Exit(1)

def version_callback(version: bool):
    """Handle version flag."""
    if version:
        try:
            version_str = get_version("file-analyzer")
        except Exception:
            version_str = "unknown"
        
        python_version = platform.python_version()
        platform_info = platform.platform()
        
        typer.echo(f"File Analyzer CLI v{version_str}")
        typer.echo(f"Python {python_version}")
        typer.echo(f"Platform: {platform_info}")
        raise typer.Exit()

@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress all output except errors"),
    ci: bool = typer.Option(False, "--ci", help="Run in non-interactive CI mode"),
    json_logs: bool = typer.Option(False, "--log-json", help="Output logs in JSON format"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Path to log file"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    version: bool = typer.Option(False, "--version", help="Show version and exit", callback=version_callback),
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
    
    Use 'fa COMMAND --help' to get help for specific commands.
    """
    # Setup logging for the session
    setup_console, logger = setup_logging(
        verbose=verbose, 
        quiet=quiet, 
        json_logs=json_logs, 
        log_file=log_file,
        no_color=no_color,
        ci=ci
    )
    
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['console'] = setup_console
    ctx.obj['logger'] = logger
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['ci'] = ci

# Load subcommands via entry points (the proper way)
try:
    command_eps = entry_points(group="fa.commands")
    for ep in command_eps:
        try:
            command_app = ep.load()
            app.add_typer(command_app, name=ep.name)
        except Exception as e:
            # Silently skip broken commands in production
            pass
except Exception:
    # Entry points system failed, skip
    pass

if __name__ == "__main__":
    app()