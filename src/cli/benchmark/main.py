#!/usr/bin/env python3
"""
Benchmark subcommand for the File Analyzer CLI

This module implements the 'benchmark' subcommand, which provides
a Typer-based interface for benchmark functionality.
"""

import os
import sys
import time
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import statistics

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Import CLI common utilities
from src.cli.common.config import config
from src.cli.main import console

# Import artifact_guard utilities
from src.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard
)

# Import local modules
from src.fastvlm_analyzer import FastVLMAnalyzer

# Check if PIL is available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import subcommands
from src.cli.benchmark.samples import app as samples_app

# Create Typer app for benchmark subcommand
app = typer.Typer(help="Benchmark model performance")

# Add samples subcommand
app.add_typer(samples_app, name="samples")

def get_logger(verbose: bool = False, quiet: bool = False):
    """
    Get the logger for benchmark commands and update log level if needed.
    
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
    Perform model benchmark operations.
    
    Benchmark commands allow testing model performance on different datasets.
    """
    pass

def download_test_images(output_dir=None):
    """
    Download sample test images of different types if not available.
    
    Args:
        output_dir: Directory to save images. If None, uses canonical artifact path
        
    Returns:
        List of paths to downloaded or existing images
    """
    # Standard test URLs
    test_images = [
        {
            "url": "https://github.com/apple/ml-fastvlm/raw/main/docs/fastvlm-emoji.gif",
            "filename": "emoji.gif",
            "description": "Emoji stickers on hands"
        },
        {
            "url": "https://github.com/apple/ml-fastvlm/raw/main/docs/fastvlm-counting.gif", 
            "filename": "counting.gif",
            "description": "Counting fingers"
        },
        {
            "url": "https://github.com/apple/ml-fastvlm/raw/main/docs/fastvlm-handwriting.gif",
            "filename": "handwriting.gif",
            "description": "Handwritten text"
        },
        {
            "url": "https://raw.githubusercontent.com/apple/ml-fastvlm/main/docs/acc_vs_latency_qwen-2.png",
            "filename": "chart.png",
            "description": "Accuracy vs latency chart"
        }
    ]
    
    # Create canonical artifact path for test images
    if output_dir is None:
        output_dir = get_canonical_artifact_path("benchmark", "test_images")
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if images already exist
    downloaded_paths = []
    console.print("[bold]Downloading test images for benchmarking...[/bold]")
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        overall_task = progress.add_task("[green]Downloading images...", total=len(test_images))
        
        for i, image_info in enumerate(test_images):
            # Set output path for this image
            file_path = os.path.join(output_dir, image_info["filename"])
            downloaded_paths.append(file_path)
            
            # Skip if file already exists
            if os.path.exists(file_path):
                progress.update(overall_task, advance=1, description=f"[green]Using existing {image_info['filename']} ({i+1}/{len(test_images)})")
                continue
                
            try:
                # Download image
                task_desc = f"[green]Downloading {image_info['filename']} ({i+1}/{len(test_images)})"
                progress.update(overall_task, description=task_desc)
                
                # Use urllib to download the file
                import urllib.request
                urllib.request.urlretrieve(image_info["url"], file_path)
                
                # Update progress
                progress.update(overall_task, advance=1)
                
            except Exception as e:
                console.print(f"[red]Error downloading {image_info['filename']}:[/red] {str(e)}")
    
    return downloaded_paths

def find_test_images():
    """
    Find test images in canonical artifact paths and test_data directory.
    
    Attempts multiple strategies to find suitable test images:
    1. Checks canonical benchmark test_images directory
    2. Checks test_data/images directory
    3. Downloads sample images if none found
    
    Returns:
        List of Path objects pointing to test images
    """
    # Look in canonical benchmark path
    benchmark_path = get_canonical_artifact_path("benchmark", "test_images")
    image_list = []
    
    # Check if directory exists and contains images
    if os.path.exists(benchmark_path):
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp"]:
            image_list.extend(list(Path(benchmark_path).glob(f"*{ext}")))
    
    # If no images found in benchmark path, check test_data directory
    if not image_list:
        # Get project root
        project_root = Path(__file__).resolve().parents[3]
        test_path = project_root / "test_data" / "images"
        
        if test_path.exists():
            console.print(f"[yellow]No images found in benchmark directory. Checking {test_path}...[/yellow]")
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp"]:
                image_list.extend(list(test_path.glob(f"*{ext}")))
    
    # If still no images found, download sample images
    if not image_list:
        console.print("[yellow]No test images found. Downloading sample images...[/yellow]")
        downloaded_paths = download_test_images()
        image_list = [Path(p) for p in downloaded_paths if os.path.exists(p)]
    
    return image_list

def format_size(path):
    """Format file size nicely"""
    size_bytes = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def get_image_info(image_path):
    """Get image dimensions and size"""
    if not PIL_AVAILABLE:
        return {"size": format_size(image_path), "dimensions": "Unknown (PIL not available)"}
    
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            return {
                "size": format_size(image_path),
                "dimensions": f"{width}x{height}",
                "format": img.format
            }
    except Exception as e:
        return {"size": format_size(image_path), "dimensions": f"Error: {str(e)}"}

def run_benchmark(analyzer, images, output_file=None):
    """
    Run benchmark on provided images and collect metrics.
    
    Args:
        analyzer: FastVLMAnalyzer instance
        images: List of image paths to benchmark
        output_file: Path to save benchmark results (if None, uses canonical path)
        
    Returns:
        Dict with benchmark results
    """
    if not images:
        console.print("[red]Error:[/red] No test images available for benchmarking")
        return {}
        
    # Create results directory using canonical artifact paths
    if output_file is None:
        output_dir = get_canonical_artifact_path("benchmark", f"fastvlm_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        output_file = os.path.join(output_dir, "benchmark_results.json")
    else:
        output_dir = os.path.dirname(output_file)
        
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if we can run the benchmark
    if not PIL_AVAILABLE:
        console.print("[red]Error:[/red] PIL/Pillow library is required for benchmarking")
        return {}
    
    # Print benchmark settings
    console.print(f"\n[bold]Running FastVLM Benchmark[/bold]")
    console.print(f"[bold]Images:[/bold] {len(images)}")
    
    # Get model info
    model_info = analyzer.get_model_info()
    if model_info:
        console.print(f"[bold]Model:[/bold] {model_info.get('name', 'Unknown')}")
        console.print(f"[bold]Size:[/bold] {model_info.get('size', 'Unknown')}")
        console.print(f"[bold]Backend:[/bold] {model_info.get('backend', 'Unknown')}")
    
    # Create results structure
    results = {
        "timestamp": datetime.now().isoformat(),
        "model_info": model_info,
        "system_info": {
            "os": sys.platform,
            "python": sys.version
        },
        "images": {},
        "summary": {}
    }
    
    # Lists to track metrics
    load_times = []
    ttft_times = []  # Time to first token
    total_times = []
    token_rates = []
    
    # Run benchmark for each image
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        benchmark_task = progress.add_task("[green]Running benchmark...", total=len(images))
        
        for i, image_path in enumerate(images):
            try:
                # Update progress description
                image_name = image_path.name
                progress.update(benchmark_task, description=f"[green]Processing {image_name} ({i+1}/{len(images)})")
                
                # Get image info
                image_info = get_image_info(image_path)
                
                # Run model and measure performance
                load_start = time.time()
                result = analyzer.analyze_image_benchmark(str(image_path))
                load_end = time.time()
                
                # Extract metrics
                load_time = load_end - load_start
                ttft = result.get("time_to_first_token", 0)
                total_processing_time = result.get("total_processing_time", 0)
                tokens = result.get("total_tokens", 0)
                token_rate = tokens / total_processing_time if total_processing_time > 0 and tokens > 0 else 0
                
                # Store metrics
                load_times.append(load_time)
                ttft_times.append(ttft)
                total_times.append(total_processing_time)
                token_rates.append(token_rate)
                
                # Store result for this image
                results["images"][image_name] = {
                    "path": str(image_path),
                    "info": image_info,
                    "load_time": load_time,
                    "time_to_first_token": ttft,
                    "total_processing_time": total_processing_time,
                    "total_tokens": tokens,
                    "token_rate": token_rate,
                    "response": result.get("response", "")
                }
                
                # Update progress
                progress.update(benchmark_task, advance=1)
                
            except Exception as e:
                console.print(f"[red]Error processing {image_name}:[/red] {str(e)}")
                progress.update(benchmark_task, advance=1)
    
    # Calculate summary statistics if we have results
    if load_times:
        results["summary"] = {
            "image_count": len(images),
            "load_time": {
                "mean": statistics.mean(load_times),
                "median": statistics.median(load_times),
                "min": min(load_times),
                "max": max(load_times)
            },
            "time_to_first_token": {
                "mean": statistics.mean(ttft_times),
                "median": statistics.median(ttft_times),
                "min": min(ttft_times),
                "max": max(ttft_times)
            },
            "total_processing_time": {
                "mean": statistics.mean(total_times),
                "median": statistics.median(total_times),
                "min": min(total_times),
                "max": max(total_times)
            },
            "token_rate": {
                "mean": statistics.mean(token_rates),
                "median": statistics.median(token_rates),
                "min": min(token_rates),
                "max": max(token_rates)
            }
        }
    
    # Print summary
    if results["summary"]:
        console.print("\n[bold]Benchmark Summary:[/bold]")
        console.print(f"Images processed: [green]{results['summary']['image_count']}[/green]")
        console.print(f"Average loading time: [green]{results['summary']['load_time']['mean']:.4f}s[/green]")
        console.print(f"Average time to first token: [green]{results['summary']['time_to_first_token']['mean']:.4f}s[/green]")
        console.print(f"Average processing time: [green]{results['summary']['total_processing_time']['mean']:.4f}s[/green]")
        console.print(f"Average token rate: [green]{results['summary']['token_rate']['mean']:.2f} tokens/s[/green]")
    
    # Save results to file
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        console.print(f"\nResults saved to: [bold]{output_file}[/bold]")
    except Exception as e:
        console.print(f"[red]Error saving results:[/red] {str(e)}")
    
    return results

@app.command("run")
def run(
    model_path: Optional[str] = typer.Option(
        None, "--model", "-m", help="Path to FastVLM model"
    ),
    images_dir: Optional[str] = typer.Option(
        None, "--images", "-i", help="Directory containing test images"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for benchmark results"
    ),
    canonical: bool = typer.Option(
        False, "--canonical", "-c", help="Force use of canonical artifact paths"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Run FastVLM benchmark tests.
    
    Benchmarks the performance of FastVLM on different image types
    and records metrics like time-to-first-token and processing speed.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Initialize analyzer
        analyzer = FastVLMAnalyzer(model_path=model_path)
        
        # Find test images
        if images_dir and os.path.exists(images_dir) and not canonical:
            # Check if the provided directory is a canonical artifact path
            if validate_artifact_path(images_dir):
                image_dir = Path(images_dir)
                images = []
                for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"]:
                    images.extend(list(image_dir.glob(f"*{ext}")))
                if images:
                    console.print(f"[green]Using {len(images)} images from provided canonical artifact path[/green]")
                else:
                    console.print(f"[yellow]No images found in provided directory. Searching canonical artifact paths...[/yellow]")
                    images = find_test_images()
            else:
                console.print(f"[yellow]Warning: Provided image directory {images_dir} is not a canonical artifact path[/yellow]")
                console.print(f"[yellow]Consider moving images to canonical artifact paths[/yellow]")
                console.print(f"[yellow]Searching canonical artifact paths instead...[/yellow]")
                images = find_test_images()
        else:
            images = find_test_images()
        
        # Run benchmark
        run_benchmark(analyzer, images, output_file)
        
        return 0
    
    except Exception as e:
        console.print(f"[red]Error running benchmark:[/red] {str(e)}")
        logger.error(f"Error running benchmark: {str(e)}")
        return 1

@app.command("images")
def images(
    download: bool = typer.Option(
        False, "--download", "-d", help="Download test images"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output directory for downloaded images"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Manage benchmark test images.
    
    Lists available test images or downloads sample images for benchmarking.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        if download:
            # Download test images
            downloaded_paths = download_test_images(output_dir)
            console.print(f"[green]Downloaded {len(downloaded_paths)} test images[/green]")
            
            # Print image list
            table = Table(title="Downloaded Test Images")
            table.add_column("Filename", style="cyan")
            table.add_column("Path", style="green")
            table.add_column("Size", style="blue")
            
            for path in downloaded_paths:
                if os.path.exists(path):
                    size = format_size(path)
                    table.add_row(os.path.basename(path), path, size)
            
            console.print(table)
            
        else:
            # Find and list test images
            images = find_test_images()
            
            if not images:
                console.print("[yellow]No test images found[/yellow]")
                console.print("Use 'fa benchmark images --download' to download sample images")
                return 0
            
            # Print image list
            table = Table(title="Available Test Images")
            table.add_column("Filename", style="cyan")
            table.add_column("Path", style="green")
            table.add_column("Size", style="blue")
            table.add_column("Dimensions", style="yellow")
            
            for image in images:
                info = get_image_info(image)
                table.add_row(
                    image.name, 
                    str(image), 
                    info.get("size", "Unknown"),
                    info.get("dimensions", "Unknown")
                )
            
            console.print(table)
        
        return 0
    
    except Exception as e:
        console.print(f"[red]Error managing benchmark images:[/red] {str(e)}")
        logger.error(f"Error managing benchmark images: {str(e)}")
        return 1

if __name__ == "__main__":
    app()