#!/usr/bin/env python3
"""
Analyze subcommand for the File Analyzer CLI

This module implements the 'analyze' subcommand, which provides a Typer-based
interface to the core file analysis functionality in src/analyzer.py.
"""

import os
import logging
from typing import Optional, List

import typer
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Import CLI common utilities
from src.cli.common.config import config

# We'll import console from main when needed to avoid circular imports

# Import analyzer core
from src.core.analyzer import FileAnalyzer, verify_installation

# Create Typer app for analyze subcommand
app = typer.Typer(help="Analyze files and directories")

# Create a class to store state across command invocations
class AnalyzeState:
    """Class to store state for the analyze command."""
    def __init__(self):
        self.verification_results = {}

# Initialize state
state = AnalyzeState()

# Helper function to get console - avoids circular imports
def get_console():
    """Get console for output - import here to avoid circular imports."""
    from src.cli.main import console
    return console

def get_logger(verbose: bool = False, quiet: bool = False):
    """
    Get the logger for analyze commands and update log level if needed.
    
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
    Perform file analysis operations.

    The analyze command provides access to all analysis capabilities:
    - Metadata extraction
    - Duplicate detection
    - OCR text extraction
    - Malware scanning
    - Content searching
    - Binary analysis
    - AI-powered model analysis
    """
    pass
    
# Context object to store shared state
context = {
    "ci_mode": False  # Whether we're running in CI mode (disables progress bars)
}

# Common options dictionary template
def create_options_dict(analysis_type, **kwargs):
    """
    Create a standard options dictionary for analyzer with the specified analysis type enabled.
    
    Args:
        analysis_type: The type of analysis to enable
        **kwargs: Additional options to include
        
    Returns:
        Dictionary with standard options structure and specified analysis enabled
    """
    # Create base options with all analyses disabled
    options = {
        'metadata': False,
        'duplicates': False,
        'ocr': False,
        'virus': False,
        'search': False,
        'binary': False,
        'vision': False,
        'results_dir': kwargs.get('results_dir')
    }
    
    # Enable specified analysis type
    if analysis_type in options:
        options[analysis_type] = True
    
    # Add optional search text if provided
    if 'search_text' in kwargs:
        options['search_text'] = kwargs['search_text']
    
    # Add vision model options if provided
    if analysis_type == 'vision' or kwargs.get('enable_vision', False):
        options['vision'] = True
        options['model'] = True
        options['model_type'] = "vision"
        options['model_name'] = kwargs.get('model_name', 'fastvlm')
        options['model_size'] = kwargs.get('model_size', '1.5b')
        options['model_mode'] = kwargs.get('model_mode', 'describe')
    
    return options

@app.command()
def all(
    path: str = typer.Argument(
        ".", help="Path to analyze (file or directory)"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    include_patterns: List[str] = typer.Option(
        [], "--include", "-i", help="Patterns to include (e.g. *.jpg)"
    ),
    exclude_patterns: List[str] = typer.Option(
        [], "--exclude", "-e", help="Patterns to exclude (e.g. *.tmp)"
    ),
    max_files: int = typer.Option(
        50, "--max-files", "-m", help="Maximum number of files to process"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Run all analysis types on the specified path.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Check if path exists
    if not os.path.exists(path):
        console = get_console()
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(code=1)
    
    # Create configuration for analyzer
    analysis_config = {
        "max_metadata_files": max_files,
        "file_extensions": {
            "images": [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"],
        },
        "default_include_patterns": include_patterns,
        "default_exclude_patterns": exclude_patterns,
    }
    
    # Create options dictionary for all analysis types
    options = create_options_dict('all', results_dir=results_dir)
    
    # Enable all analysis types
    for key in ['metadata', 'duplicates', 'ocr', 'virus', 'search', 'binary']:
        options[key] = True
    
    # Set model options
    options['vision'] = True
    options['model'] = True
    options['model_type'] = "vision"
    options['model_name'] = "fastvlm"
    options['model_size'] = "1.5b"
    options['model_mode'] = "describe"
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis with progress indicator
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Running all analyses...", total=7)
        
        # Run analysis
        results = file_analyzer.analyze(path, options)
        progress.update(task, completed=7)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    console.print("\n[bold]Analysis Complete[/bold]")
    
    # Find a results path from the available analyses in a more robust way
    results_path = ""
    analyses = results.get('analyses', {})
    
    # Try to find any output file from the analyses, prioritizing in this order
    for analysis_type in ['metadata', 'vision', 'ocr', 'duplicates', 'virus', 'search', 'binary']:
        if analysis_type in analyses:
            analysis_result = analyses[analysis_type]
            if 'file' in analysis_result:
                results_path = analysis_result['file']
                break
            elif 'output_path' in analysis_result:
                results_path = analysis_result['output_path']
                break
            elif 'output_dir' in analysis_result:
                results_path = analysis_result['output_dir']
                break
    
    if results_path:
        console.print(f"Results path: {results_path}")
    else:
        console.print("Results saved to output directory")
    
    # Return success
    return 0

@app.command()
def metadata(
    path: str = typer.Argument(
        ".", help="Path to analyze (file or directory)"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    include_patterns: List[str] = typer.Option(
        [], "--include", "-i", help="Patterns to include (e.g. *.jpg)"
    ),
    exclude_patterns: List[str] = typer.Option(
        [], "--exclude", "-e", help="Patterns to exclude (e.g. *.tmp)"
    ),
    max_files: int = typer.Option(
        50, "--max-files", "-m", help="Maximum number of files to process"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Extract metadata from files.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Create configuration for analyzer
    analysis_config = {
        "max_metadata_files": max_files,
        "file_extensions": {
            "images": [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"],
        },
        "default_include_patterns": include_patterns,
        "default_exclude_patterns": exclude_patterns,
    }
    
    # Create options dictionary
    options = create_options_dict('metadata', results_dir=results_dir)
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    if results.get('metadata', {}).get('status') == 'success':
        console.print(f"[green]Metadata extraction complete[/green]")
        console.print(f"Found {results['metadata'].get('count', 0)} items")
        console.print(f"Results saved to: {results['metadata'].get('file', '')}")
    else:
        console.print(f"[red]Metadata extraction failed:[/red] {results.get('metadata', {}).get('message', 'Unknown error')}")
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def duplicates(
    path: str = typer.Argument(
        ".", help="Path to analyze (file or directory)"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Find duplicate files.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Check if path is a directory
    if not os.path.isdir(path):
        console = get_console()
        console.print(f"[red]Error:[/red] Path must be a directory: {path}")
        raise typer.Exit(code=1)
    
    # Create configuration for analyzer
    analysis_config = {}
    
    # Create options dictionary
    options = create_options_dict('duplicates', results_dir=results_dir)
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    if results.get('duplicates', {}).get('status') == 'success':
        console.print(f"[green]Duplicate analysis complete[/green]")
        console.print(f"Results saved to: {results['duplicates'].get('file', '')}")
    else:
        console.print(f"[red]Duplicate analysis failed:[/red] {results.get('duplicates', {}).get('message', 'Unknown error')}")
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def ocr(
    path: str = typer.Argument(
        ".", help="Path to analyze (file or directory)"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    include_patterns: List[str] = typer.Option(
        [], "--include", "-i", help="Patterns to include (e.g. *.jpg)"
    ),
    exclude_patterns: List[str] = typer.Option(
        [], "--exclude", "-e", help="Patterns to exclude (e.g. *.tmp)"
    ),
    max_files: int = typer.Option(
        50, "--max-files", "-m", help="Maximum number of files to process"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Perform OCR on images.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Create configuration for analyzer
    analysis_config = {
        "max_ocr_images": max_files,
        "file_extensions": {
            "images": [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"],
        },
        "default_include_patterns": include_patterns,
        "default_exclude_patterns": exclude_patterns,
    }
    
    # Create options dictionary
    options = create_options_dict('ocr', results_dir=results_dir)
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    if results.get('ocr', {}).get('status') == 'success':
        console.print(f"[green]OCR processing complete[/green]")
        console.print(f"Processed {results['ocr'].get('total', 0)} images")
        console.print(f"Successful: {results['ocr'].get('successful', 0)}, Failed: {results['ocr'].get('failed', 0)}")
        console.print(f"Results saved to: {results['ocr'].get('file', '')}")
    else:
        console.print(f"[red]OCR processing failed:[/red] {results.get('ocr', {}).get('message', 'Unknown error')}")
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def virus(
    path: str = typer.Argument(
        ".", help="Path to analyze (file or directory)"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Scan for malware.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Create configuration for analyzer
    analysis_config = {}
    
    # Create options dictionary
    options = create_options_dict('virus', results_dir=results_dir)
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    status = results.get('virus', {}).get('status')
    if status in ['clean', 'threat_detected']:
        if status == 'clean':
            console.print(f"[green]Malware scan complete: No threats found[/green]")
        else:
            console.print(f"[red]Malware scan complete: Threats detected![/red]")
        
        console.print(f"Results saved to: {results['virus'].get('file', '')}")
        
        # Print summary information if available
        if 'summary' in results.get('virus', {}):
            console.print("\nScan Summary:")
            for key, value in results['virus']['summary'].items():
                console.print(f"  {key}: {value}")
    else:
        console.print(f"[red]Malware scan failed:[/red] {results.get('virus', {}).get('message', 'Unknown error')}")
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def search(
    text: str = typer.Argument(
        ..., help="Text to search for"
    ),
    path: str = typer.Argument(
        ".", help="Path to analyze (file or directory)"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    include_patterns: List[str] = typer.Option(
        [], "--include", "-i", help="Patterns to include (e.g. *.txt)"
    ),
    exclude_patterns: List[str] = typer.Option(
        [], "--exclude", "-e", help="Patterns to exclude (e.g. *.tmp)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Search file contents for specific text.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Create configuration for analyzer
    analysis_config = {
        "default_include_patterns": include_patterns,
        "default_exclude_patterns": exclude_patterns,
    }
    
    # Create options dictionary
    options = create_options_dict('search', results_dir=results_dir, search_text=text)
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    if results.get('search', {}).get('status') == 'success':
        matches = results['search'].get('matches', 0)
        if matches > 0:
            console.print(f"[green]Search complete: Found {matches} matches[/green]")
        else:
            console.print(f"[yellow]Search complete: No matches found[/yellow]")
        
        console.print(f"Results saved to: {results['search'].get('file', '')}")
    else:
        console.print(f"[red]Search failed:[/red] {results.get('search', {}).get('message', 'Unknown error')}")
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def binary(
    path: str = typer.Argument(
        ..., help="Path to file to analyze"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Analyze binary files.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Check if path is a file
    if not os.path.isfile(path):
        console = get_console()
        console.print(f"[red]Error:[/red] Path must be a file: {path}")
        raise typer.Exit(code=1)
    
    # Create configuration for analyzer
    analysis_config = {}
    
    # Create options dictionary
    options = create_options_dict('binary', results_dir=results_dir)
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    if results.get('binary', {}).get('status') == 'success':
        interesting = results['binary'].get('interesting_data', False)
        if interesting:
            console.print(f"[green]Binary analysis complete: Found interesting data[/green]")
        else:
            console.print(f"[yellow]Binary analysis complete: No interesting data found[/yellow]")
        
        console.print(f"Results saved to: {results['binary'].get('file', '')}")
    else:
        console.print(f"[red]Binary analysis failed:[/red] {results.get('binary', {}).get('message', 'Unknown error')}")
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def vision(
    path: str = typer.Argument(
        ..., help="Path to image or directory of images to analyze"
    ),
    model: str = typer.Option(
        "fastvlm", "--model", "-m", help="Vision model to use (fastvlm, bakllava, qwen2vl)"
    ),
    size: str = typer.Option(
        "1.5b", "--size", "-s", help="Model size (0.5b, 1.5b, 7b)"
    ),
    mode: str = typer.Option(
        "describe", "--mode", "-M", help="Analysis mode (describe, detect, document)"
    ),
    results_dir: Optional[str] = typer.Option(
        None, "--results", "-r", help="Output directory for results"
    ),
    include_patterns: List[str] = typer.Option(
        [], "--include", "-i", help="Patterns to include (e.g. *.jpg)"
    ),
    exclude_patterns: List[str] = typer.Option(
        [], "--exclude", "-e", help="Patterns to exclude (e.g. *.tmp)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Analyze images with AI vision models.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Create configuration for analyzer
    analysis_config = {
        "default_include_patterns": include_patterns,
        "default_exclude_patterns": exclude_patterns,
        "file_extensions": {
            "images": [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"],
        },
        "vision": {
            "model": model,
            "model_size": size,
            "mode": mode
        }
    }
    
    # Create options dictionary
    options = create_options_dict('vision', results_dir=results_dir, 
                                model_name=model, model_size=size, model_mode=mode)
    
    # Initialize analyzer
    file_analyzer = FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
    # Get console for output
    console = get_console()
    
    # Print summary
    if results.get('vision', {}).get('status') == 'success':
        console.print(f"[green]Vision analysis complete[/green]")
        
        if 'files_processed' in results.get('vision', {}):
            console.print(f"Processed {results['vision'].get('files_processed', 0)} files")
            console.print(f"Successful: {results['vision'].get('successful', 0)}, Failed: {results['vision'].get('failed', 0)}")
            console.print(f"Results saved to: {results['vision'].get('output_dir', '')}")
        else:
            console.print(f"Results saved to: {results['vision'].get('output_path', '')}")
    else:
        console.print(f"[red]Vision analysis failed:[/red] {results.get('vision', {}).get('error', 'Unknown error')}")
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def verify(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Verify the installation and dependencies.
    
    Checks for required tools, libraries, and models needed by the file analyzer.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Get console for output
    console = get_console()
    
    console.print("[bold]Verifying file-analyzer installation...[/bold]")
    
    # Get verification results
    verification = verify_installation()
    
    # Store verification results in the state object
    state.verification_results = verification
    
    # Print verification results in a more beautiful way
    console.print("\n[bold green]System Information:[/bold green]")
    for key, value in verification["system"].items():
        console.print(f"  [blue]{key}:[/blue] {value}")
    
    console.print("\n[bold green]Core Dependencies:[/bold green]")
    for key, value in verification["core_dependencies"].items():
        if "Not installed" in value:
            console.print(f"  [blue]{key}:[/blue] [yellow]{value}[/yellow]")
        else:
            console.print(f"  [blue]{key}:[/blue] {value}")
    
    console.print("\n[bold green]External Tools:[/bold green]")
    for key, value in verification["external_tools"].items():
        if "Not found" in value or "Error" in value:
            console.print(f"  [blue]{key}:[/blue] [yellow]{value}[/yellow]")
        else:
            console.print(f"  [blue]{key}:[/blue] [green]{value}[/green]")
    
    console.print("\n[bold green]Vision Models:[/bold green]")
    if "error" in verification["vision_models"]:
        console.print(f"  [red]Error checking models:[/red] {verification['vision_models']['error']}")
    else:
        for key, value in verification["vision_models"].items():
            console.print(f"  [blue]{key}:[/blue] [green]{value}[/green]")
    
    console.print("\n[bold]Verification complete.[/bold]")
    
    # Check if all required tools are present
    missing_tools = [key for key, value in verification["external_tools"].items() 
                  if "Not found" in value or "Error" in value]
    
    if missing_tools:
        console.print("\n[yellow]Warning: The following external tools are missing:[/yellow]")
        for tool in missing_tools:
            console.print(f"  - {tool}")
        console.print("\nSome analyzer functionality may be limited.")
    
    return 0

def _setup_logging(verbose: bool):
    """Setup logging configuration for analysis."""
    import logging
    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=log_level)
    return logging.getLogger("file-analyzer")


def _validate_file_path(file_path: str) -> str:
    """Validate and expand file path. Returns error message if invalid, empty string if valid."""
    import os
    file_path = os.path.expanduser(file_path)
    if not os.path.exists(file_path):
        return f"Error: File does not exist: {file_path}"
    return ""


def _create_analyzer_config():
    """Create analyzer configuration and options."""
    options = create_options_dict('vision',
                                  model_name='fastvlm',
                                  model_size='1.5b',
                                  model_mode='describe')
    config = {
        'vision': {
            'model_size': '1.5b'
        }
    }
    return options, config


def _run_analysis_with_timeout(analyzer, file_path: str, options: dict, logger):
    """Run analysis with cross-platform timeout handling."""
    import threading
    
    class AnalysisTimeoutError(Exception):
        pass

    result = {"success": False, "data": None, "error": None}
    
    def analysis_worker():
        try:
            result["data"] = analyzer.analyze(file_path, options)
            result["success"] = True
        except Exception as e:
            result["error"] = e
            
    # Start analysis in a separate thread
    analysis_thread = threading.Thread(target=analysis_worker)
    analysis_thread.daemon = True
    analysis_thread.start()
    
    # Wait for completion with timeout
    analysis_thread.join(timeout=45)  # 45 second timeout
    
    if analysis_thread.is_alive():
        # Thread is still running, analysis timed out
        logger.warning("Analysis timed out after 45 seconds")
        raise AnalysisTimeoutError("Analysis timed out after 45 seconds")
        
    if not result["success"]:
        # Analysis completed but with error
        if result["error"]:
            raise result["error"]
        else:
            raise Exception("Analysis failed for unknown reason")
            
    return result["data"]


def _validate_analysis_results(results: dict, verbose: bool, logger) -> tuple:
    """Validate analysis results and extract vision data. Returns (success, error_message, output_path)."""
    vision_result = results.get("vision")
    if not vision_result:
        return False, "Analysis failed - no vision results", None
        
    # Extract actual error message if analysis failed
    if vision_result.get("status") != "success":
        # Get the actual error message from the result
        actual_error = vision_result.get('error', 'unknown failure')
        error_type = vision_result.get('error_type', 'Unknown')
        
        # If we have traceback information, include it in verbose mode
        if verbose and 'traceback' in vision_result:
            logger.error(f"Full traceback: {vision_result['traceback']}")
            
        return False, f"Model analysis failed ({error_type}): {actual_error}", None

    output_path = vision_result.get("output_path")
    if not output_path:
        return False, "Analysis failed - output path missing from result", None
        
    return True, "", output_path


def _wait_for_mtime_stabilization(path: str, stable_duration=0.3, timeout=5.0):
    """Wait until the file at 'path' has a stable mtime for at least `stable_duration` seconds."""
    import time
    import os
    
    start = time.time()
    last_mtime = None
    stable_since = None

    while True:
        if not os.path.exists(path):
            time.sleep(0.05)
            continue

        current_mtime = os.stat(path).st_mtime
        now = time.time()

        if last_mtime != current_mtime:
            last_mtime = current_mtime
            stable_since = now
        elif now - stable_since >= stable_duration:
            return  # mtime has stabilized

        if now - start > timeout:
            raise TimeoutError(f"File mtime did not stabilize for: {path}")

        time.sleep(0.05)


def _read_and_parse_analysis_output(output_path: str) -> tuple:
    """Read and parse analysis output JSON. Returns (success, error_message, data)."""
    import json
    
    try:
        # Wait for file to be completely written
        _wait_for_mtime_stabilization(output_path)
        
        # Read and validate JSON
        with open(output_path, "r") as f:
            content = f.read()
            if not content.strip():
                raise ValueError("Empty JSON output file")
            try:
                analysis_data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in output: {e}")
                
        return True, "", analysis_data
                
    except Exception as e:
        return False, f"Analysis failed - could not parse model output: {e}", None


def _validate_analysis_schema(analysis_data) -> str:
    """Validate analysis data schema. Returns error message if invalid, empty string if valid."""
    if not isinstance(analysis_data, dict):
        return "Analysis failed - output is not a valid object"
    if "description" not in analysis_data or "tags" not in analysis_data:
        return "Analysis failed - output missing required fields"
    return ""


def analyze_single_file(file_path: str, output_format: str = "pretty", verbose: bool = False) -> str:
    """
    Hardened single-file analysis function.
    Performs robust analysis with timeout, logging, subprocess validation,
    file I/O safety, and schema checking.
    """
    import os
    import time
    from src.core.analyzer import FileAnalyzer
    from src.cli.utils.render import render_output

    # Setup logging
    logger = _setup_logging(verbose)

    # Validate file path
    file_path = os.path.expanduser(file_path)
    if error := _validate_file_path(file_path):
        return error

    # Create analyzer configuration
    options, config = _create_analyzer_config()
    analyzer = FileAnalyzer(config)

    # Run analysis with timeout
    try:
        results = _run_analysis_with_timeout(analyzer, file_path, options, logger)
    except Exception as e:
        if "timed out" in str(e):
            return "Analysis failed - operation timed out after 45 seconds"
        logger.error(f"Analysis failed with exception: {e}")
        if verbose:
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        return f"Analysis failed - unexpected error: {e}"

    # Validate analysis results
    success, error_msg, output_path = _validate_analysis_results(results, verbose, logger)
    if not success:
        return error_msg

    # Read and parse analysis output
    success, error_msg, analysis_data = _read_and_parse_analysis_output(output_path)
    if not success:
        return error_msg

    # Validate schema
    if error := _validate_analysis_schema(analysis_data):
        return error

    # Format and return output
    return render_output(analysis_data, output_format, file_path)

if __name__ == "__main__":
    app()