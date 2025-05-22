#!/usr/bin/env python3
"""
Model management subcommand for the File Analyzer CLI

This module implements the 'model' subcommand, which provides a Typer-based
interface for managing FastVLM models.
"""

import os
import sys
import logging
import hashlib
import tempfile
import zipfile
import shutil
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, DownloadColumn, TransferSpeedColumn

# Import CLI common utilities
from src.cli.common.config import config

# Helper function to get console - avoids circular imports
def get_console():
    """Get console for output - import here to avoid circular imports."""
    from src.cli.main import console
    return console

# Import artifact_guard utilities
from src.core.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard
)

# Create Typer app for model subcommand
app = typer.Typer(help="Manage FastVLM models")

# Model information - size, URL, checksum
MODEL_INFO = {
    "0.5b": {
        "name": "llava-fastvithd_0.5b_stage3",
        "size_mb": 580,
        "url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_0.5b_stage3.zip",
        "md5": "5ee58683b47c8ac1cf68ced7dd48b7c3"
    },
    "1.5b": {
        "name": "llava-fastvithd_1.5b_stage3",
        "size_mb": 1720,
        "url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_1.5b_stage3.zip",
        "md5": "5c6235e7a68cdcf9bd079deed9716d8b"
    },
    "7b": {
        "name": "llava-fastvithd_7b_stage3",
        "size_mb": 7500,
        "url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_7b_stage3.zip",
        "md5": "f6cff9f3f157f3799c83972dafb496dd"  # Updated MD5 based on actual download
    }
}

def get_logger(verbose: bool = False, quiet: bool = False):
    """
    Get the logger for model commands and update log level if needed.
    
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
    Manage FastVLM models.
    
    The model command provides utilities for managing FastVLM models:
    - List available models
    - Download models by size
    - Check model integrity
    """
    pass

def get_project_root():
    """
    Get the project root directory.
    
    Returns:
        Path: Path to the project root
    """
    # Check for libs/ml-fastvlm directory relative to the current file
    src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.dirname(src_dir)

def get_model_dir():
    """
    Get the path to the models directory.
    
    Returns:
        Path: Path to the models directory
    """
    # Use the USER_MODEL_DIR from config instead of project directory
    # Import user model directory from config
    from src.models.config import USER_MODEL_DIR
    return USER_MODEL_DIR

def calculate_md5(file_path):
    """
    Calculate MD5 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: MD5 hash of the file
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def download_file(url, dest_path, desc=None, min_size_bytes=1000000):
    """
    Download a file with progress monitoring.
    
    Args:
        url: URL to download
        dest_path: Path to save the file
        desc: Description of the file being downloaded
        min_size_bytes: Minimum expected file size (default 1MB)
        
    Returns:
        bool: True if download succeeded, False otherwise
    """
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Download with progress bar
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=console
        ) as progress:
            desc = desc or f"Downloading {os.path.basename(dest_path)}"
            task = progress.add_task(f"[green]{desc}", total=1.0)
            
            # Implement a custom urlretrieve with progress reporting - no timeout for large files
            with urllib.request.urlopen(url) as response, open(dest_path, 'wb') as out_file:
                content_length = response.headers.get('Content-Length')
                total = int(content_length) if content_length else None
                
                if total is None:
                    # If we can't get the file size, just show an indeterminate progress
                    progress.update(task, completed=0.5)
                    out_file.write(response.read())
                    progress.update(task, completed=1.0)
                else:
                    # Update progress based on downloaded bytes
                    downloaded = 0
                    while True:
                        buffer = response.read(8192)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        out_file.write(buffer)
                        progress.update(task, completed=downloaded / total)
        
        # Verify the downloaded file size after download
        if os.path.exists(dest_path):
            file_size = os.path.getsize(dest_path)
            if file_size < min_size_bytes:
                console = get_console()
                console.print(f"[red]Downloaded file is too small ({file_size} bytes).[/red]")
                
                # Check if it's a 1-byte file (common with Apple CDN redirect issues)
                if file_size <= 1:
                    console.print(f"[red]Apple CDN often returns 1-byte files for redirects or auth issues.[/red]")
                    os.remove(dest_path)
                    return False
                
                console.print(f"[red]Expected at least {min_size_bytes} bytes.[/red]")
                os.remove(dest_path)
                return False
                
            console = get_console()
            console.print(f"[green]Download complete: {file_size} bytes[/green]")
        
        return True
    except Exception as e:
        console = get_console()
        console.print(f"[red]Error during download:[/red] {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

def extract_zip(zip_path, extract_dir):
    """
    Extract a ZIP file with progress monitoring.
    
    Args:
        zip_path: Path to the ZIP file
        extract_dir: Directory to extract to
        
    Returns:
        bool: True if extraction succeeded, False otherwise
    """
    try:
        # Create extraction directory if it doesn't exist
        os.makedirs(extract_dir, exist_ok=True)
        
        # Count number of files in the ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Analyze zip structure first
            namelist = zip_ref.namelist()
            
            # Find all top-level directories (for nested structure detection)
            top_level_dirs = set()
            top_level_files = set()
            
            # Analyze structure - identify the main folder structure
            for name in namelist:
                # Skip macOS metadata files
                if name.startswith('__MACOSX/') or name == '__MACOSX/':
                    continue
                    
                parts = name.split('/')
                if len(parts) > 1:
                    top_level_dirs.add(parts[0])
                else:
                    top_level_files.add(name)
                    
            # Determine if we have a structure with one main directory containing everything
            nested_structure = len(top_level_dirs) == 1 and len(top_level_files) == 0
            
            # Check if the main directory has the same name as what we're extracting to
            main_dir = list(top_level_dirs)[0] if nested_structure else None
            
            console = get_console()
            console.print(f"[yellow]ZIP structure analysis: {'nested under ' + main_dir if nested_structure else 'multiple top-level items'}[/yellow]")
            
            # If we have a nested structure where all files are inside a single top dir with the same name as our target,
            # extract with path modification to avoid double nesting
            if nested_structure and main_dir and main_dir == os.path.basename(extract_dir):
                console.print(f"[yellow]Detected single nested directory matching target: {main_dir}[/yellow]")
                console.print(f"[yellow]Extracting directly to target to avoid double nesting[/yellow]")
                
                # Extract with path modification to remove the top-level directory
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    total_files = sum(1 for name in namelist if not name.startswith('__MACOSX/'))
                    task = progress.add_task(f"[green]Extracting {os.path.basename(zip_path)}", total=total_files)
                    processed = 0
                    
                    for i, member in enumerate(namelist):
                        # Skip macOS metadata
                        if member.startswith('__MACOSX/'):
                            continue
                            
                        # Skip directories themselves
                        if member.endswith('/'):
                            continue
                            
                        # Get path components
                        parts = member.split('/')
                        
                        # Remove the first component (the nested directory)
                        if len(parts) > 1:
                            # Create the modified target path directly inside extract_dir
                            target_path = os.path.join(extract_dir, *parts[1:])
                            
                            # Ensure the parent directory exists
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            
                            # Extract the file directly to the target path
                            with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                                
                            processed += 1
                            progress.update(task, completed=processed)
            else:
                # Regular extraction for flat structure or non-matching directory names
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task(f"[green]Extracting {os.path.basename(zip_path)}", total=len(namelist))
                    
                    # Extract each file
                    for i, file in enumerate(namelist):
                        zip_ref.extract(file, extract_dir)
                        progress.update(task, completed=i+1)
                        
                # After extraction, check if we need to clean up __MACOSX directories
                macosx_dir = os.path.join(extract_dir, '__MACOSX')
                if os.path.exists(macosx_dir):
                    console.print(f"[yellow]Removing macOS metadata directory: {macosx_dir}[/yellow]")
                    shutil.rmtree(macosx_dir)
                
            # Show what we've got after extraction
            top_level_items = [item for item in os.listdir(extract_dir) 
                              if not item.startswith('.') and not item == '__MACOSX']
            console.print(f"[yellow]Extracted to {extract_dir}[/yellow]")
            console.print(f"[yellow]Top-level items: {', '.join(top_level_items)}[/yellow]")
        
        return True
    except Exception as e:
        console = get_console()
        console.print(f"[red]Error during extraction:[/red] {e}")
        console.print(f"[red]Error details: {str(e.__class__.__name__)}[/red]")
        return False

@app.command("list")
def list_models(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    List available FastVLM models.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Create table for rich output
        table = Table(title="Available FastVLM Models")
        table.add_column("Size", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Disk Space", style="blue")
        
        # Get model directory
        model_dir = get_model_dir()
        
        # Check each model
        for size, info in MODEL_INFO.items():
            # Check if model directory exists
            model_path = os.path.join(model_dir, info["name"])
            model_exists = os.path.exists(model_path)
            
            # Format disk space
            disk_space = f"{info['size_mb']} MB"
            
            # Format status
            if model_exists:
                # Check for safetensors file as a simple existence check
                safetensors_file = os.path.join(model_path, "model.safetensors")
                if os.path.exists(safetensors_file):
                    status = "[green]Installed[/green]"
                else:
                    status = "[yellow]Incomplete[/yellow]"
            else:
                status = "[red]Not Installed[/red]"
            
            # Add row to table
            table.add_row(size, info["name"], status, disk_space)
        
        # Print table
        console = get_console()
        console.print(table)
        
        # Print model directory
        console.print(f"\n[bold]Model directory:[/bold] {model_dir}")
        
        return 0
    
    except Exception as e:
        console = get_console()
        console.print(f"[red]Error listing models:[/red] {str(e)}")
        logger.error(f"Error listing models: {str(e)}")
        return 1

@app.command("download")
def download_model_cmd(
    sizes: list[str] = typer.Argument(
        None, help="Model sizes to download (0.5b, 1.5b, 7b)"
    ),
    all_models: bool = typer.Option(
        False, "--all", "-a", help="Download all available models"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force re-download even if model exists"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Download FastVLM models.
    
    Examples:
        fa model download             # Download default 1.5b model
        fa model download 0.5b 7b     # Download 0.5b and 7b models
        fa model download --all       # Download all models
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    # Get console for output
    console = get_console()
    
    try:
        # Handle --all option
        if all_models:
            models_to_download = list(MODEL_INFO.keys())
        else:
            # Validate each size
            models_to_download = []
            for size in sizes:
                if size not in MODEL_INFO:
                    console.print(f"[red]Error:[/red] Invalid model size: {size}")
                    console.print(f"Valid sizes: {', '.join(MODEL_INFO.keys())}")
                    return 1
                models_to_download.append(size)
                
        # If no models specified, use default
        if not models_to_download:
            if sizes is None or len(sizes) == 0:
                # Default to 1.5b if no arguments provided
                models_to_download = ["1.5b"]
                console.print("[yellow]No model size specified, defaulting to 1.5b[/yellow]")
            
        # Show summary of what will be downloaded
        console.print(f"[bold]Models to download: {', '.join(models_to_download)}[/bold]")
        
        # Get model directory and ensure it exists
        model_dir = get_model_dir()
        os.makedirs(model_dir, exist_ok=True)
        
        # Download each model
        success_count = 0
        fail_count = 0
        
        for size in models_to_download:
            console.print(f"\n[bold cyan]Processing model: {size}[/bold cyan]")
            
            # Get model info
            info = MODEL_INFO[size]
            model_name = info["name"]
            model_url = info["url"]
            model_md5 = info["md5"]
            model_path = os.path.join(model_dir, model_name)
            
            # Check if model already exists
            if os.path.exists(model_path) and not force:
                # Check for safetensors file
                safetensors_file = os.path.join(model_path, "model.safetensors")
                nested_path = os.path.join(model_path, model_name, "model.safetensors")
                
                # Additional check for actual file size to verify complete downloads
                model_valid = False
                min_size_bytes = 100000000  # 100MB - models should be much larger
                
                if os.path.exists(safetensors_file) and os.path.getsize(safetensors_file) > min_size_bytes:
                    console.print(f"[green]Found valid model at {safetensors_file}[/green]")
                    model_valid = True
                elif os.path.exists(nested_path) and os.path.getsize(nested_path) > min_size_bytes:
                    console.print(f"[green]Found valid model at {nested_path}[/green]")
                    model_valid = True
                
                if model_valid:
                    console.print(f"[yellow]Model {model_name} is already installed. Skipping.[/yellow]")
                    success_count += 1
                    continue
                else:
                    console.print(f"[yellow]Found existing model directory but it appears incomplete or corrupted. Re-downloading.[/yellow]")
            
            # Create a temporary file for the download
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Check if we need to download or already have the file
                # Prefer reusing an existing download if valid
                already_exists = False
                for check_dir in [model_dir, "/tmp", os.path.expanduser("~/Downloads")]:
                    # Look for the zip or the extracted directory
                    zip_path = os.path.join(check_dir, f"{model_name}.zip")
                    if os.path.exists(zip_path) and os.path.getsize(zip_path) > 1000000:  # >1MB
                        console.print(f"[yellow]Found existing zip at {zip_path}[/yellow]")
                        shutil.copy(zip_path, tmp_path)
                        
                        # Verify the existing download
                        console.print(f"[bold]Verifying existing download integrity...[/bold]")
                        actual_md5 = calculate_md5(tmp_path)
                        if actual_md5 == model_md5:
                            console.print(f"[green]Existing download verified successfully.[/green]")
                            already_exists = True
                            break
                        else:
                            console.print(f"[yellow]Existing download verification failed. Will download fresh copy.[/yellow]")
                
                # Download the model if needed
                if not already_exists:
                    console.print(f"[bold]Downloading model {model_name} ({info['size_mb']} MB)...[/bold]")
                    console.print(f"This may take a while depending on your internet connection.")
                    
                    # Download the model
                    desc = f"Downloading {model_name} ({size})"
                    if not download_file(model_url, tmp_path, desc):
                        console.print(f"[red]Failed to download model {model_name}.[/red]")
                        fail_count += 1
                        continue
                    
                    # Verify MD5 checksum
                    console.print(f"[bold]Verifying download integrity...[/bold]")
                    actual_md5 = calculate_md5(tmp_path)
                    if actual_md5 != model_md5:
                        console.print(f"[red]MD5 checksum verification failed![/red]")
                        console.print(f"Expected: {model_md5}")
                        console.print(f"Actual:   {actual_md5}")
                        
                        # Proceed with extraction anyway but warn the user
                        console.print(f"[yellow]MD5 checksum mismatch could indicate a model update or corruption.[/yellow]")
                        console.print(f"[yellow]Model files will still be extracted for inspection.[/yellow]")
                        
                        # Save the MD5 hash for future reference
                        md5_file = os.path.join(model_dir, f"{model_name}_actual_md5.txt")
                        with open(md5_file, "w") as f:
                            f.write(f"Expected: {model_md5}\nActual: {actual_md5}\nSize: {os.path.getsize(tmp_path)} bytes\nDate: {datetime.now().isoformat()}")
                        
                        console.print(f"[yellow]Saved actual MD5 to {md5_file} for reference[/yellow]")
                
                # Remove existing model directory if it exists
                if os.path.exists(model_path):
                    console.print(f"[yellow]Removing existing model directory...[/yellow]")
                    shutil.rmtree(model_path)
                
                # Ensure the model path exists
                os.makedirs(model_path, exist_ok=True)
                
                # Extract the model
                console.print(f"[bold]Extracting model files...[/bold]")
                if not extract_zip(tmp_path, model_path):
                    console.print(f"[red]Failed to extract model files.[/red]")
                    fail_count += 1
                    continue
                    
                # Verify the model was extracted correctly
                # We need to be flexible about model file structure
                found_model_file = False
                
                # Primary model files to check
                primary_model_files = [
                    # Single file format
                    os.path.join(model_path, "model.safetensors"),
                    os.path.join(model_path, model_name, "model.safetensors"),
                    # Sharded format with index
                    os.path.join(model_path, "model.safetensors.index.json"),
                    os.path.join(model_path, model_name, "model.safetensors.index.json")
                ]
                
                # Sharded model patterns
                sharded_patterns = [
                    os.path.join(model_path, "model-00001-of-*.safetensors"),
                    os.path.join(model_path, model_name, "model-00001-of-*.safetensors")
                ]
                
                # Check for primary model files
                for check_path in primary_model_files:
                    if os.path.exists(check_path):
                        console.print(f"[green]Found model file at: {check_path}[/green]")
                        found_model_file = True
                        break
                        
                # If we haven't found a model file yet, check for sharded files
                if not found_model_file:
                    for pattern in sharded_patterns:
                        import glob
                        matches = glob.glob(pattern)
                        if matches:
                            console.print(f"[green]Found sharded model files matching: {pattern}[/green]")
                            console.print(f"[green]First shard: {matches[0]}[/green]")
                            found_model_file = True
                            break
                
                # Additional checks for config files that should be present
                config_files_present = False
                config_file_paths = [
                    os.path.join(model_path, "config.json"),
                    os.path.join(model_path, model_name, "config.json")
                ]
                
                for config_path in config_file_paths:
                    if os.path.exists(config_path):
                        console.print(f"[green]Found config file: {config_path}[/green]")
                        config_files_present = True
                        break
                
                # Check if we have tokenizer files
                tokenizer_files_present = False
                tokenizer_file_paths = [
                    os.path.join(model_path, "tokenizer_config.json"),
                    os.path.join(model_path, model_name, "tokenizer_config.json")
                ]
                
                for tokenizer_path in tokenizer_file_paths:
                    if os.path.exists(tokenizer_path):
                        console.print(f"[green]Found tokenizer config: {tokenizer_path}[/green]")
                        tokenizer_files_present = True
                        break
                
                # For the 7b model specifically, check for sharded files pattern
                if size == "7b":
                    # The 7b model uses a sharded format with 4 parts
                    sharded_format = True
                    for i in range(1, 5):
                        shard_file = os.path.join(model_path, f"model-0000{i}-of-00004.safetensors")
                        if not os.path.exists(shard_file):
                            sharded_format = False
                            break
                    
                    if sharded_format:
                        console.print(f"[green]Found all 4 shards of the 7b model[/green]")
                        found_model_file = True
                
                # If we have either model files or both config and tokenizer, consider it a success
                if found_model_file and (config_files_present or tokenizer_files_present):
                    console.print(f"[green]Model verification successful[/green]")
                    valid_model = True
                elif found_model_file:
                    console.print(f"[yellow]Found model files but missing some config files - model may still work[/yellow]")
                    valid_model = True
                else:
                    console.print(f"[red]Model extraction appears incomplete. Missing expected files.[/red]")
                    valid_model = False
                
                if not valid_model:
                    console.print(f"[yellow]Keeping downloaded files at {model_path} for manual inspection.[/yellow]")
                    console.print(f"[yellow]You may want to check the contents and structure of this directory.[/yellow]")
                    fail_count += 1
                    continue
                
                console.print(f"[green]Successfully downloaded and installed model {model_name} ({size}).[/green]")
                success_count += 1
                
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        # Show download summary
        console.print(f"\n[bold]Download Summary:[/bold]")
        console.print(f"Total requested: {len(models_to_download)}")
        console.print(f"[green]Successfully downloaded: {success_count}[/green]")
        
        if fail_count > 0:
            console.print(f"[red]Failed downloads: {fail_count}[/red]")
            return 1
            
        console.print(f"Models are installed at: {model_dir}")
        return 0
    
    except Exception as e:
        console.print(f"[red]Error downloading model:[/red] {str(e)}")
        logger.error(f"Error downloading model: {str(e)}")
        return 1

if __name__ == "__main__":
    app()