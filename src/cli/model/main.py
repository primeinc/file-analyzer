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
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, DownloadColumn, TransferSpeedColumn

# Import CLI common utilities
from src.cli.common.config import config
from src.cli.main import console

# Import artifact_guard utilities
from src.artifact_guard import (
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
        "url": "https://huggingface.co/apple/ml-fastvlm/resolve/main/checkpoints/llava-fastvithd_0.5b_stage3.zip",
        "md5": "5ee58683b47c8ac1cf68ced7dd48b7c3"
    },
    "1.5b": {
        "name": "llava-fastvithd_1.5b_stage3",
        "size_mb": 1720,
        "url": "https://huggingface.co/apple/ml-fastvlm/resolve/main/checkpoints/llava-fastvithd_1.5b_stage3.zip",
        "md5": "9cd651417e5c0b764df33c3b552eedf9"
    },
    "7b": {
        "name": "llava-fastvithd_7b_stage3",
        "size_mb": 7500,
        "url": "https://huggingface.co/apple/ml-fastvlm/resolve/main/checkpoints/llava-fastvithd_7b_stage3.zip",
        "md5": "f3a83ac0c05f889195b0c761b44d1cf2"
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
    return os.path.join(get_project_root(), "libs", "ml-fastvlm", "checkpoints")

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

def download_file(url, dest_path, desc=None):
    """
    Download a file with progress monitoring.
    
    Args:
        url: URL to download
        dest_path: Path to save the file
        desc: Description of the file being downloaded
        
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
            
            # Implement a custom urlretrieve with progress reporting
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
                        
        return True
    except Exception as e:
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
            # Start extraction with progress bar
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"[green]Extracting {os.path.basename(zip_path)}", total=len(zip_ref.namelist()))
                
                # Extract each file
                for i, file in enumerate(zip_ref.namelist()):
                    zip_ref.extract(file, extract_dir)
                    progress.update(task, completed=i+1)
        
        return True
    except Exception as e:
        console.print(f"[red]Error during extraction:[/red] {e}")
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
        console.print(table)
        
        # Print model directory
        console.print(f"\n[bold]Model directory:[/bold] {model_dir}")
        
        return 0
    
    except Exception as e:
        console.print(f"[red]Error listing models:[/red] {str(e)}")
        logger.error(f"Error listing models: {str(e)}")
        return 1

@app.command("download")
def download_model_cmd(
    size: str = typer.Argument(
        "0.5b", help="Model size to download (0.5b, 1.5b, 7b)"
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
    Download a FastVLM model.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Validate size
        if size not in MODEL_INFO:
            console.print(f"[red]Error:[/red] Invalid model size: {size}")
            console.print(f"Valid sizes: {', '.join(MODEL_INFO.keys())}")
            return 1
        
        # Get model info
        info = MODEL_INFO[size]
        model_name = info["name"]
        model_url = info["url"]
        model_md5 = info["md5"]
        
        # Get model directory
        model_dir = get_model_dir()
        model_path = os.path.join(model_dir, model_name)
        
        # Check if model already exists
        if os.path.exists(model_path) and not force:
            # Check for safetensors file as a simple existence check
            safetensors_file = os.path.join(model_path, "model.safetensors")
            if os.path.exists(safetensors_file):
                console.print(f"[yellow]Model {model_name} is already installed.[/yellow]")
                console.print("Use --force to re-download.")
                return 0
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        # Download model
        console.print(f"[bold]Downloading model {model_name} ({info['size_mb']} MB)...[/bold]")
        console.print(f"This may take a while depending on your internet connection.")
        
        # Create a temporary file for the download
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            tmp_path = tmp_file.name
        
        # Download the model
        desc = f"Downloading {model_name} ({size})"
        if not download_file(model_url, tmp_path, desc):
            console.print(f"[red]Failed to download model {model_name}.[/red]")
            return 1
        
        # Verify MD5 checksum
        console.print(f"[bold]Verifying download integrity...[/bold]")
        actual_md5 = calculate_md5(tmp_path)
        if actual_md5 != model_md5:
            console.print(f"[red]MD5 checksum verification failed![/red]")
            console.print(f"Expected: {model_md5}")
            console.print(f"Actual:   {actual_md5}")
            os.remove(tmp_path)
            return 1
        
        # Remove existing model directory if it exists
        if os.path.exists(model_path):
            console.print(f"[yellow]Removing existing model directory...[/yellow]")
            shutil.rmtree(model_path)
        
        # Extract the model
        console.print(f"[bold]Extracting model files...[/bold]")
        if not extract_zip(tmp_path, model_dir):
            console.print(f"[red]Failed to extract model files.[/red]")
            os.remove(tmp_path)
            return 1
        
        # Clean up the temporary file
        os.remove(tmp_path)
        
        # Verify the model was extracted correctly
        safetensors_file = os.path.join(model_path, "model.safetensors")
        if not os.path.exists(safetensors_file):
            console.print(f"[red]Model extraction appears incomplete. Missing expected files.[/red]")
            return 1
        
        console.print(f"[green]Successfully downloaded and installed model {model_name} ({size}).[/green]")
        console.print(f"Model location: {model_path}")
        
        return 0
    
    except Exception as e:
        console.print(f"[red]Error downloading model:[/red] {str(e)}")
        logger.error(f"Error downloading model: {str(e)}")
        return 1

if __name__ == "__main__":
    app()