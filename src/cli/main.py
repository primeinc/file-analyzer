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
from typing import Optional, Tuple

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
    
    try:
        # Discover entry points
        discovered_commands = entry_points(group='fa.commands')
        
        # First, correctly print what we found to debug
        logger.debug(f"Found entry points: {list(discovered_commands)}")
        
        # This section will EXPLICITLY register the commands we know about
        # This provides better error reporting than the dynamic loading
        entry_map = {entry.name: entry for entry in discovered_commands}
        
        # Register analyze if available
        if 'analyze' in entry_map:
            try:
                from src.cli.analyze.main import app as analyze_app
                app.add_typer(analyze_app, name='analyze')
                logger.debug("Registered analyze command")
            except Exception as e:
                logger.error(f"Failed to load analyze command: {e}")
        
        # Register test if available
        if 'test' in entry_map:
            try:
                from src.cli.test.hook import app as test_app
                app.add_typer(test_app, name='test')
                logger.debug("Registered test command")
            except Exception as e:
                logger.error(f"Failed to load test command: {e}")
        
        # Register validate if available
        if 'validate' in entry_map:
            try:
                from src.cli.validate.main import app as validate_app
                app.add_typer(validate_app, name='validate')
                logger.debug("Registered validate command")
            except Exception as e:
                logger.error(f"Failed to load validate command: {e}")
        
        # Register artifact if available
        if 'artifact' in entry_map:
            try:
                from src.cli.artifact.main import app as artifact_app
                app.add_typer(artifact_app, name='artifact')
                logger.debug("Registered artifact command")
            except Exception as e:
                logger.error(f"Failed to load artifact command: {e}")
        
        # Register preflight directly - it's part of the artifact module
        try:
            from src.cli.artifact.preflight import app as preflight_app
            app.add_typer(preflight_app, name='preflight')
            logger.debug("Registered preflight command")
        except Exception as e:
            logger.error(f"Failed to load preflight command: {e}")
        
        # Register adapter command - it's part of the artifact module
        try:
            import src.cli.artifact.adapter
            logger.debug("Registered adapter module for bash integration")
        except Exception as e:
            logger.error(f"Failed to load adapter command: {e}")
        
        # Register install command
        try:
            from src.cli.install.main import app as install_app
            app.add_typer(install_app, name='install')
            logger.debug("Registered install command")
        except Exception as e:
            logger.error(f"Failed to load install command: {e}")
            
        # Register model command
        try:
            from src.cli.model.main import app as model_app
            app.add_typer(model_app, name='model')
            logger.debug("Registered model command")
        except Exception as e:
            logger.error(f"Failed to load model command: {e}")
            
        # Register benchmark command
        try:
            from src.cli.benchmark.main import app as benchmark_app
            app.add_typer(benchmark_app, name='benchmark')
            logger.debug("Registered benchmark command")
        except Exception as e:
            logger.error(f"Failed to load benchmark command: {e}")
                
    except Exception as e:
        logger.warning(f"Error discovering plugins: {e}")
        # Fallback to direct imports if entry points discovery fails
        logger.debug("Using direct imports for commands")
        _import_builtin_commands()

def _import_builtin_commands():
    """
    Import built-in commands directly as a fallback if entry points discovery fails.
    
    This is a fallback loader that doesn't depend on entry points.
    """
    logger = logging.getLogger("file-analyzer")
    logger.warning("Using fallback command loader - entry points discovery failed")
    
    # Try to import all known commands directly
    try:
        from src.cli.analyze.main import app as analyze_app
        app.add_typer(analyze_app, name="analyze")
        logger.debug("Registered analyze command")
    except ImportError:
        logger.warning("Could not import analyze command")
    
    try:
        from src.cli.test.main import app as test_app
        app.add_typer(test_app, name="test")
        logger.debug("Registered test command")
    except ImportError:
        logger.warning("Could not import test command")
        
    try:
        from src.cli.validate.main import app as validate_app
        app.add_typer(validate_app, name="validate")
        logger.debug("Registered validate command")
    except ImportError:
        logger.warning("Could not import validate command")
        
    try:
        from src.cli.artifact.main import app as artifact_app
        app.add_typer(artifact_app, name="artifact")
        logger.debug("Registered artifact command")
    except ImportError:
        logger.warning("Could not import artifact command")
    
    try:
        from src.cli.artifact.preflight import app as preflight_app
        app.add_typer(preflight_app, name="preflight")
        logger.debug("Registered preflight command")
    except ImportError:
        logger.warning("Could not import preflight command")
    
    try:
        import src.cli.artifact.adapter
        logger.debug("Registered adapter module for bash integration")
    except ImportError:
        logger.warning("Could not import adapter module")
    
    try:
        from src.cli.install.main import app as install_app
        app.add_typer(install_app, name="install")
        logger.debug("Registered install command")
    except ImportError:
        logger.warning("Could not import install command")
        
    try:
        from src.cli.model.main import app as model_app
        app.add_typer(model_app, name="model")
        logger.debug("Registered model command")
    except ImportError:
        logger.warning("Could not import model command")
        
    try:
        from src.cli.benchmark.main import app as benchmark_app
        app.add_typer(benchmark_app, name="benchmark")
        logger.debug("Registered benchmark command")
    except ImportError:
        logger.warning("Could not import benchmark command")

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