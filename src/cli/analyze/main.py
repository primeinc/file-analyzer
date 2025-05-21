#!/usr/bin/env python3
"""
Analyze subcommand for the File Analyzer CLI

This module implements the 'analyze' subcommand, which provides a Typer-based
interface to the core file analysis functionality in src/analyzer.py.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Import CLI common utilities
from src.cli.common.config import config

# Import analyzer core
from src import analyzer

# Create Typer app for analyze subcommand
app = typer.Typer(help="Analyze files and directories")
console = Console()

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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    # Use the existing logger configured in main.py
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
    # Check if path exists
    if not os.path.exists(path):
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
    
    # Create options dictionary
    options = {
        'metadata': True,
        'duplicates': True,
        'ocr': True,
        'virus': True,
        'search': True,
        'search_text': '',  # Will be ignored since no specific search text
        'binary': True,
        'vision': True,
        'model': True,
        'model_type': "vision",
        'model_name': "fastvlm",
        'model_mode': "describe",
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
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
    
    # Print summary
    console.print("\n[bold]Analysis Complete[/bold]")
    console.print(f"Results path: {results.get('analyses', {}).get('metadata', {}).get('file', '')}")
    
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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
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
    options = {
        'metadata': True,
        'duplicates': False,
        'ocr': False,
        'virus': False,
        'search': False,
        'binary': False,
        'vision': False,
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
    # Check if path is a directory
    if not os.path.isdir(path):
        console.print(f"[red]Error:[/red] Path must be a directory: {path}")
        raise typer.Exit(code=1)
    
    # Create configuration for analyzer
    analysis_config = {}
    
    # Create options dictionary
    options = {
        'metadata': False,
        'duplicates': True,
        'ocr': False,
        'virus': False,
        'search': False,
        'binary': False,
        'vision': False,
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
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
    options = {
        'metadata': False,
        'duplicates': False,
        'ocr': True,
        'virus': False,
        'search': False,
        'binary': False,
        'vision': False,
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
    # Create configuration for analyzer
    analysis_config = {}
    
    # Create options dictionary
    options = {
        'metadata': False,
        'duplicates': False,
        'ocr': False,
        'virus': True,
        'search': False,
        'binary': False,
        'vision': False,
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
    # Create configuration for analyzer
    analysis_config = {
        "default_include_patterns": include_patterns,
        "default_exclude_patterns": exclude_patterns,
    }
    
    # Create options dictionary
    options = {
        'metadata': False,
        'duplicates': False,
        'ocr': False,
        'virus': False,
        'search': True,
        'search_text': text,
        'binary': False,
        'vision': False,
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
    # Check if path is a file
    if not os.path.isfile(path):
        console.print(f"[red]Error:[/red] Path must be a file: {path}")
        raise typer.Exit(code=1)
    
    # Create configuration for analyzer
    analysis_config = {}
    
    # Create options dictionary
    options = {
        'metadata': False,
        'duplicates': False,
        'ocr': False,
        'virus': False,
        'search': False,
        'binary': True,
        'vision': False,
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
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
        "0.5b", "--size", "-s", help="Model size (0.5b, 1.5b, 7b)"
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
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(log_level)
    
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
    options = {
        'metadata': False,
        'duplicates': False,
        'ocr': False,
        'virus': False,
        'search': False,
        'binary': False,
        'vision': True,
        'model': True,
        'model_type': "vision",
        'model_name': model,
        'model_size': size,
        'model_mode': mode,
        'results_dir': results_dir
    }
    
    # Initialize analyzer
    file_analyzer = analyzer.FileAnalyzer(analysis_config)
    
    # Run analysis
    results = file_analyzer.analyze(path, options)
    
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

if __name__ == "__main__":
    app()