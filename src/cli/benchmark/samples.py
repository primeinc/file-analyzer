#!/usr/bin/env python3
"""
Sample data generator for benchmark testing

This module provides functionality to generate and manage sample data
for benchmarking without running actual models.
"""

import os
import sys
import json
import time
import random
import hashlib
import typer
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

# Import CLI common utilities
from src.cli.common.config import config
from src.cli.main import console

# Import artifact_guard utilities
from src.core.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard
)

# Import benchmark utilities
from src.cli.benchmark.utils import find_test_images, get_image_info

# Get canonical artifact path for cache
CACHE_DIR = get_canonical_artifact_path("benchmark", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "benchmark_sample_data.json")

# Sample image descriptions for different categories
DESCRIPTIONS = {
    # Natural scenes
    "nature": [
        "A beautiful landscape with mountains and a lake reflecting the sky.",
        "A forest scene with sunlight streaming through the trees and a path leading into the distance.",
        "A beach with white sand and turquoise water, palm trees lining the shore.",
        "A meadow filled with wildflowers under a blue sky with scattered clouds."
    ],
    # Animals
    "animals": [
        "A majestic lion sitting on a rock in the savanna, surveying its territory.",
        "Two playful dolphins jumping out of the water in synchrony.",
        "A colorful parrot perched on a branch, its vibrant feathers clearly visible.",
        "A family of elephants walking across an open plain, with baby elephants protected by the adults."
    ],
    # People
    "people": [
        "A group of friends smiling and laughing together at a social gathering.",
        "A person concentrating deeply while playing a musical instrument.",
        "A child with a joyful expression blowing bubbles in a park.",
        "Two people walking hand in hand on a beach at sunset."
    ],
    # Urban scenes
    "urban": [
        "A skyline of a modern city with skyscrapers reflecting the sunlight.",
        "A narrow cobblestone street in an old European city with historic buildings.",
        "A busy marketplace with vendors selling colorful goods and produce.",
        "A quiet café with outdoor seating and people enjoying their drinks."
    ],
    # Food
    "food": [
        "A beautifully plated dish with vibrant colors and artistic presentation.",
        "A rustic wooden table with an assortment of fresh fruits and vegetables.",
        "A steaming cup of coffee next to a freshly baked pastry on a cafe table.",
        "A traditional meal with multiple dishes arranged on a dining table."
    ],
    # Objects
    "objects": [
        "A vintage camera on a wooden surface with soft lighting.",
        "A collection of antique books with worn leather covers on a bookshelf.",
        "A sleek modern smartphone displaying a colorful application.",
        "A handcrafted ceramic vase with an intricate pattern."
    ],
    # Abstract
    "abstract": [
        "This image appears to be an abstract artwork with vibrant colors and geometric shapes.",
        "A pattern of repeating elements creating an optical illusion effect.",
        "This appears to be a digital art piece with flowing forms and gradient colors.",
        "A minimalist composition with simple shapes and a limited color palette."
    ],
    # Charts
    "charts": [
        "A bar chart comparing data across multiple categories with clear labels.",
        "A line graph showing trends over time with multiple data series.",
        "A pie chart illustrating the distribution of resources or percentages.",
        "A complex data visualization combining multiple chart types to present information."
    ],
    # Unknown
    "unknown": [
        "The image shows a scene with various elements that are difficult to categorize specifically.",
        "This appears to be a composite image with multiple subjects and themes.",
        "The image content is unclear or ambiguous in nature.",
        "This image contains a mix of different elements and subjects."
    ]
}

# Create Typer app for samples command
app = typer.Typer(help="Generate benchmark sample data")

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

def get_image_hash(image_path):
    """
    Generate a simple hash for an image path to use as cache key.
    
    Args:
        image_path: Path to the image
        
    Returns:
        str: MD5 hash of the image path and file stats
    """
    path_str = str(image_path)
    stats = os.stat(image_path)
    hash_str = f"{path_str}_{stats.st_size}_{stats.st_mtime}"
    return hashlib.md5(hash_str.encode()).hexdigest()

def categorize_image(image_path):
    """
    Assign a category to an image based on its filename.
    This is a simple heuristic to simulate image content recognition.
    
    Args:
        image_path: Path to the image
        
    Returns:
        str: Category name
    """
    filename = os.path.basename(image_path).lower()
    
    # Check filename for category hints
    categories = {
        "nature": ["nature", "landscape", "forest", "beach", "mountain", "tree", "sky", "lake"],
        "animals": ["animal", "dog", "cat", "bird", "wildlife", "pet", "zoo"],
        "people": ["person", "people", "face", "portrait", "human", "child"],
        "urban": ["city", "building", "street", "urban", "architecture"],
        "food": ["food", "meal", "dish", "fruit", "vegetable", "dessert"],
        "objects": ["object", "item", "product", "device", "tool", "furniture"],
        "abstract": ["abstract", "art", "pattern", "design", "texture"],
        "charts": ["chart", "graph", "plot", "diagram", "data", "infographic"]
    }
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in filename:
                return category
    
    # Use hash of filename to assign a random but consistent category
    filename_hash = hash(filename) % 9
    categories_list = list(categories.keys()) + ["unknown"]
    return categories_list[filename_hash]

def generate_sample_response(image_path, category=None):
    """
    Generate a sample response for an image without using actual model.
    
    Args:
        image_path: Path to the image
        category: Optional category to use (if None, will be determined)
        
    Returns:
        dict: Sample response data
    """
    # Determine category if not provided
    if category is None:
        category = categorize_image(image_path)
    
    # Get description options for category
    descriptions = DESCRIPTIONS.get(category, DESCRIPTIONS["unknown"])
    
    # Use filename hash to get consistent but "random" choice
    filename = os.path.basename(image_path)
    index = hash(filename) % len(descriptions)
    description = descriptions[index]
    
    # Tags based on category
    tags = {
        "nature": ["landscape", "outdoors", "scenic", "nature"],
        "animals": ["wildlife", "animal", "fauna", "creature"],
        "people": ["person", "portrait", "human", "face"],
        "urban": ["city", "building", "architecture", "urban"],
        "food": ["food", "cuisine", "meal", "culinary"],
        "objects": ["object", "item", "product", "still life"],
        "abstract": ["abstract", "art", "pattern", "design"],
        "charts": ["chart", "graph", "data", "visualization"],
        "unknown": ["scene", "mixed", "miscellaneous", "general"]
    }.get(category, ["image", "scene", "photo"])
    
    # Create fake timing data
    tokens = random.randint(50, 150)
    total_time = random.uniform(1.0, 5.0)
    ttft = random.uniform(0.3, 1.2)
    
    # Create sample response
    response = {
        "image_path": str(image_path),
        "category": category,
        "description": description,
        "tags": tags,
        "confidence": round(random.uniform(0.85, 0.99), 2),
        "time_to_first_token": ttft,
        "total_processing_time": total_time,
        "token_rate": tokens / total_time if total_time > 0 else 0,
        "total_tokens": tokens,
        "generated_at": datetime.now().isoformat()
    }
    
    return response

def create_or_load_cache():
    """
    Create or load the cache file for sample response data.
    
    Returns:
        dict: Cache data structure
    """
    # Make sure cache directory exists
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Try to load existing cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            console.print(f"[yellow]Cache file exists but could not be read. Creating new cache.[/yellow]")
    
    # Create new cache
    return {"images": {}, "metadata": {"created_at": datetime.now().isoformat()}}

def save_cache(cache_data):
    """
    Save cache data to the cache file.
    
    Args:
        cache_data: Cache data to save
        
    Returns:
        bool: Success status
    """
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        return True
    except (IOError, PermissionError) as e:
        console.print(f"[red]Error saving cache file: {str(e)}[/red]")
        return False

def get_or_generate_response(image_path, cache, force_generate=False):
    """
    Get response from cache or generate a new one.
    
    Args:
        image_path: Path to the image
        cache: Cache data structure
        force_generate: Whether to force regeneration
        
    Returns:
        dict: Response data
    """
    # Get image hash
    image_hash = get_image_hash(image_path)
    
    # Check cache if not forcing regeneration
    if not force_generate and image_hash in cache["images"]:
        return cache["images"][image_hash]
    
    # Generate new response
    response = generate_sample_response(image_path)
    
    # Save to cache
    cache["images"][image_hash] = response
    
    return response

def generate_benchmark_data(output_file=None, use_cache=True, force_generate=False):
    """
    Generate benchmark data for all test images.
    
    Args:
        output_file: Path to save output file (if None, uses canonical path)
        use_cache: Whether to use/update cache
        force_generate: Whether to force regeneration of all responses
        
    Returns:
        dict: Benchmark data
    """
    # Find test images
    images = find_test_images()
    
    if not images:
        console.print("[red]No test images found.[/red]")
        return {}
    
    # Load or create cache if using it
    cache = create_or_load_cache() if use_cache else {"images": {}}
    
    # Create benchmark data structure
    benchmark_data = {
        "generated_at": datetime.now().isoformat(),
        "images": {},
        "summary": {
            "image_count": len(images),
            "categories": {}
        }
    }
    
    # Process each image
    console.print(f"[bold]Generating sample benchmark data for {len(images)} images...[/bold]")
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Processing images...", total=len(images))
        
        for i, image_path in enumerate(images):
            # Update progress
            progress.update(task, description=f"[green]Processing {image_path.name} ({i+1}/{len(images)})")
            
            try:
                # Get or generate response
                response = get_or_generate_response(image_path, cache, force_generate)
                
                # Add to benchmark data
                benchmark_data["images"][image_path.name] = response
                
                # Update category summary
                category = response.get("category", "unknown")
                if category not in benchmark_data["summary"]["categories"]:
                    benchmark_data["summary"]["categories"][category] = 0
                benchmark_data["summary"]["categories"][category] += 1
                
                # Advance progress
                progress.update(task, advance=1)
                
            except Exception as e:
                console.print(f"[red]Error processing {image_path.name}: {str(e)}[/red]")
                progress.update(task, advance=1)
    
    # Save cache if using it
    if use_cache:
        save_cache(cache)
    
    # Create output file path if not provided
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = get_canonical_artifact_path("benchmark", f"samples_{timestamp}")
        output_file = os.path.join(output_dir, "benchmark_data.json")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save benchmark data
    try:
        with open(output_file, 'w') as f:
            json.dump(benchmark_data, f, indent=2)
        console.print(f"[green]Benchmark data saved to: {output_file}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving benchmark data: {str(e)}[/red]")
    
    # Print summary
    console.print("\n[bold]Benchmark Data Summary:[/bold]")
    console.print(f"Generated samples for [green]{len(benchmark_data['images'])}[/green] images")
    
    # Print category distribution
    if benchmark_data["summary"]["categories"]:
        table = Table(title="Category Distribution")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Percentage", style="yellow")
        
        total = len(benchmark_data["images"])
        for category, count in benchmark_data["summary"]["categories"].items():
            percentage = (count / total) * 100 if total > 0 else 0
            table.add_row(category, str(count), f"{percentage:.1f}%")
            
        console.print(table)
    
    return benchmark_data

@app.callback()
def callback():
    """
    Generate and manage benchmark sample data.
    
    The samples command provides utilities for generating sample benchmark data
    without running actual models, which is useful for testing.
    """
    pass

@app.command("generate")
def generate(
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file for benchmark data"
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache", help="Don't use or update cache"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force regeneration of all responses"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Generate benchmark sample data.
    
    Creates sample model response data for test images without running actual models.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Generate benchmark data
        generate_benchmark_data(output_file, not no_cache, force)
        return 0
    
    except Exception as e:
        console.print(f"[red]Error generating benchmark data:[/red] {str(e)}")
        logger.error(f"Error generating benchmark data: {str(e)}")
        return 1

@app.command("cache")
def cache(
    clear: bool = typer.Option(
        False, "--clear", "-c", help="Clear the cache"
    ),
    info: bool = typer.Option(
        True, "--info", "-i", help="Show cache information"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress all output except errors"
    ),
):
    """
    Manage benchmark sample data cache.
    
    View or clear the cache of pregenerated sample responses.
    """
    # Get configured logger
    logger = get_logger(verbose, quiet)
    
    try:
        # Check if cache exists
        if not os.path.exists(CACHE_FILE):
            console.print("[yellow]Cache file does not exist.[/yellow]")
            return 0
        
        # Clear cache if requested
        if clear:
            try:
                os.remove(CACHE_FILE)
                console.print("[green]Cache file cleared.[/green]")
            except Exception as e:
                console.print(f"[red]Error clearing cache: {str(e)}[/red]")
                return 1
            return 0
        
        # Show cache info
        if info:
            try:
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                
                # Get file info
                file_size = os.path.getsize(CACHE_FILE)
                file_size_formatted = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB"
                
                # Print cache info
                console.print(f"[bold]Cache File:[/bold] {CACHE_FILE}")
                console.print(f"[bold]Size:[/bold] {file_size_formatted}")
                
                # Get cache metadata
                created_at = cache_data.get("metadata", {}).get("created_at", "Unknown")
                console.print(f"[bold]Created:[/bold] {created_at}")
                
                # Get cached images count
                image_count = len(cache_data.get("images", {}))
                console.print(f"[bold]Cached Images:[/bold] {image_count}")
                
                if verbose and image_count > 0:
                    # Create table of cached images
                    table = Table(title="Cached Images")
                    table.add_column("Image", style="cyan")
                    table.add_column("Category", style="green")
                    table.add_column("Generated At", style="yellow")
                    
                    for image_hash, data in cache_data.get("images", {}).items():
                        image_path = data.get("image_path", "Unknown")
                        category = data.get("category", "Unknown")
                        generated_at = data.get("generated_at", "Unknown")
                        
                        # Shorten path for display
                        image_name = os.path.basename(image_path)
                        
                        table.add_row(image_name, category, generated_at)
                    
                    console.print(table)
            
            except Exception as e:
                console.print(f"[red]Error reading cache: {str(e)}[/red]")
                return 1
        
        return 0
    
    except Exception as e:
        console.print(f"[red]Error managing cache:[/red] {str(e)}")
        logger.error(f"Error managing cache: {str(e)}")
        return 1

if __name__ == "__main__":
    app()