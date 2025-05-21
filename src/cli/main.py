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
import importlib
from importlib.metadata import entry_points
from typing import Optional, Tuple, List, Dict

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
        "markup": not ci,
        "emoji": not ci,
    }
    configured_console = Console(**console_options)
    
    # Set log level based on verbose/quiet flags
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    # Clear existing handlers to prevent duplicates if setup_logging is called multiple times
    logging.root.handlers.clear()
    
    if json_logs:
        # Configure JSON logging
        from pythonjsonlogger import json as jsonlog
        formatter = jsonlog.JsonFormatter()
        
        # Create a handler for JSON logs
        if log_file:
            handler = logging.FileHandler(log_file)
        else:
            handler = logging.StreamHandler()
            
        handler.setFormatter(formatter)
        logging.basicConfig(level=log_level, handlers=[handler])
    else:
        # Configure rich colored logging
        rich_handler_options = {
            "console": configured_console,
            "rich_tracebacks": True,
            "show_time": not ci,
            "show_path": not ci
        }
        logging.basicConfig(
            level=log_level,
            format="%(message)s" if not ci else "%(levelname)s: %(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(**rich_handler_options)] 
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
    
    # Define command mapping: name -> (module_path, object_name, is_module)
    command_mapping = {
        'analyze': ('src.cli.analyze.main', 'app', False),
        'test': ('src.cli.test.hook', 'app', False),
        'validate': ('src.cli.validate.main', 'app', False),
        'artifact': ('src.cli.artifact.main', 'app', False),
        'preflight': ('src.cli.artifact.preflight', 'app', False),
        'adapter': ('src.cli.artifact.adapter', None, True),
        'install': ('src.cli.install.main', 'app', False),
        'model': ('src.cli.model.main', 'app', False),
        'benchmark': ('src.cli.benchmark.main', 'app', False),
    }
    
    try:
        # Discover entry points
        discovered_commands = entry_points(group='fa.commands')
        
        # Log discovered commands
        logger.debug(f"Found entry points: {list(discovered_commands)}")
        
        # Create a map of entry names
        entry_map = {entry.name: entry for entry in discovered_commands}
        
        # Register commands that are in the entry points
        for cmd_name, config in command_mapping.items():
            if cmd_name in entry_map:
                if len(config) == 2:
                    register_command(cmd_name, config[0], config[1])
                else:
                    register_command(cmd_name, config[0], config[1], config[2])
        
        # Register additional commands that aren't in entry points
        if 'preflight' not in entry_map:
            register_command('preflight', 'src.cli.artifact.preflight', 'app')
        
        if 'adapter' not in entry_map:
            register_command('adapter', 'src.cli.artifact.adapter', None, True)
                
    except Exception as e:
        logger.warning(f"Error discovering plugins: {e}")
        # Fallback to direct imports if entry points discovery fails
        logger.debug("Using direct imports for commands")
        _import_builtin_commands()

def register_command(name, module_path, object_name="app", is_module=False):
    """
    Register a single command with error handling.
    
    Args:
        name: Command name to register
        module_path: Import path of the module containing the app
        object_name: Name of the object to import (default: 'app')
        is_module: Whether to import as a module rather than get an attribute
        
    Returns:
        bool: True if registered successfully, False otherwise
    """
    logger = logging.getLogger("file-analyzer")
    
    try:
        if is_module:
            # Import the module without accessing an attribute
            importlib.import_module(module_path)
            logger.debug(f"Registered {name} module")
        else:
            # Import the Typer app and add it to the main app
            module = importlib.import_module(module_path)
            command_app = getattr(module, object_name)
            app.add_typer(command_app, name=name)
            logger.debug(f"Registered {name} command")
        return True
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not import {name} command: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to load {name} command: {str(e)}")
        return False

def _import_builtin_commands():
    """
    Import built-in commands directly as a fallback if entry points discovery fails.
    
    This is a fallback loader that doesn't depend on entry points.
    """
    logger = logging.getLogger("file-analyzer")
    logger.warning("Using fallback command loader - entry points discovery failed")
    
    # Define all commands to load
    commands = [
        ("analyze", "src.cli.analyze.main", "app"),
        ("test", "src.cli.test.hook", "app"),
        ("validate", "src.cli.validate.main", "app"),
        ("artifact", "src.cli.artifact.main", "app"),
        ("preflight", "src.cli.artifact.preflight", "app"),
        ("adapter", "src.cli.artifact.adapter", None, True),  # Import as module
        ("install", "src.cli.install.main", "app"),
        ("model", "src.cli.model.main", "app"),
        ("benchmark", "src.cli.benchmark.main", "app"),
    ]
    
    # Register each command
    for cmd in commands:
        if len(cmd) == 3:
            register_command(cmd[0], cmd[1], cmd[2])
        else:
            register_command(cmd[0], cmd[1], cmd[2], cmd[3])

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
    json_logs: bool = typer.Option(False, "--log-json", help="Output logs in JSON format"),
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
        from importlib.metadata import PackageNotFoundError
        try:
            v = get_version("file-analyzer")
            typer.echo(f"File Analyzer CLI v{v}")
        except PackageNotFoundError:
            typer.echo("File Analyzer CLI (version unknown)")
        
        # Also show Python version for diagnostic purposes
        typer.echo(f"Python {sys.version.split()[0]}")
        typer.echo(f"Platform: {platform.platform()}")
        raise typer.Exit()
    
    # Configure logging and console with color settings
    configured_console, logger = setup_logging(
        verbose=verbose, 
        quiet=quiet,
        json_logs=json_logs,
        log_file=log_file,
        no_color=no_color,
        ci=ci
    )
    
    # Capture environment for debugging/reproducibility
    env_info = capture_environment()
    logger.debug(f"Environment: {env_info}")
    
    # Load subcommands
    load_commands()
    
    # Show available commands (only in debug mode)
    if verbose:
        logger.debug(f"Registered subcommands: {[typer_instance.name for typer_instance in app.registered_typer_instances]}")
    # The prior debug log statement is sufficient, we don't need to print to stdout

# We're removing the version command and only using the --version flag option
# to avoid confusing users with two different ways to get version information.

if __name__ == "__main__":
    app()