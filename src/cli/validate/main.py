#!/usr/bin/env python3
"""
Validate subcommand for the File Analyzer CLI

This module implements the 'validate' subcommand, which provides tools for
validating the outputs of file analysis runs against schemas and expected values.
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
import jsonschema

# Import CLI common utilities
from src.cli.common.config import config

# Create Typer app for validate subcommand
app = typer.Typer(help="Validate file analysis outputs")
console = Console()

@app.callback()
def callback():
    """
    Validate file analysis outputs.
    
    The validate command provides tools for validating the outputs
    of file analysis runs against schemas, comparing images, and
    testing for expected values.
    """
    pass

@app.command()
def schema(
    file_path: str = typer.Argument(
        ..., help="Path to JSON file to validate"
    ),
    schema_type: str = typer.Option(
        "fastvlm", "--type", "-t", help="Schema type (fastvlm, analyzer, validate)"
    ),
    schema_version: str = typer.Option(
        "v1.0", "--version", "-v", help="Schema version (v1.0, v1.1)"
    ),
    schema_file: Optional[str] = typer.Option(
        None, "--schema", "-s", help="Path to schema file (overrides type and version)"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Path to output file for validation results"
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Enable strict validation (fail on any warning)"
    ),
):
    """
    Validate a JSON file against a schema.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("file-analyzer.validate")
    
    # Check if file exists
    if not os.path.exists(file_path):
        console.print(f"[red]Error:[/red] File does not exist: {file_path}")
        raise typer.Exit(code=1)
    
    # Load the JSON file
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON file: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not read file: {e}")
        raise typer.Exit(code=1)
    
    # Get the schema file
    if schema_file:
        schema_path = schema_file
    else:
        schema_path = config.get_schema_path(schema_type, schema_version)
        
    if not schema_path or not os.path.exists(schema_path):
        console.print(f"[red]Error:[/red] Schema file not found for {schema_type} version {schema_version}")
        console.print(f"Expected path: {schema_path}")
        console.print(f"You can specify a schema file directly with --schema")
        raise typer.Exit(code=1)
    
    # Load the schema
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid schema file: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not read schema file: {e}")
        raise typer.Exit(code=1)
    
    # Validate against schema
    validation_results = {
        "success": True,
        "file": file_path,
        "schema": str(schema_path),
        "errors": [],
        "warnings": []
    }
    
    try:
        # Do the validation
        jsonschema.validate(data, schema)
        console.print(f"[green]✓[/green] JSON file validates against schema")
    except jsonschema.exceptions.ValidationError as e:
        validation_results["success"] = False
        validation_results["errors"].append({
            "path": ".".join(str(p) for p in e.path),
            "message": e.message,
            "schema_path": ".".join(str(p) for p in e.schema_path)
        })
        console.print(f"[red]✗[/red] JSON file does not validate against schema:")
        console.print(f"   Path: {'.'.join(str(p) for p in e.path)}")
        console.print(f"   Error: {e.message}")
    except jsonschema.exceptions.SchemaError as e:
        validation_results["success"] = False
        validation_results["errors"].append({
            "message": f"Schema error: {e.message}",
            "schema_path": ".".join(str(p) for p in e.schema_path)
        })
        console.print(f"[red]✗[/red] Schema error: {e.message}")
    
    # Additional Validations
    # These are not strict validations but provide additional checks
    
    # 1. Check for empty fields
    if "properties" in schema:
        for prop, details in schema["properties"].items():
            if prop in data and (data[prop] == "" or data[prop] == [] or data[prop] == {}):
                warning = f"Property '{prop}' is empty"
                validation_results["warnings"].append({
                    "path": prop,
                    "message": warning
                })
                console.print(f"[yellow]⚠[/yellow] {warning}")
    
    # 2. Check if all required properties are present
    if "required" in schema:
        for prop in schema["required"]:
            if prop not in data:
                error = f"Required property '{prop}' is missing"
                validation_results["errors"].append({
                    "path": "",
                    "message": error
                })
                console.print(f"[red]✗[/red] {error}")
                validation_results["success"] = False
    
    # Apply strict mode if enabled
    if strict and validation_results["warnings"]:
        validation_results["success"] = False
        console.print(f"[red]✗[/red] Validation failed in strict mode due to warnings")
    
    # Write results to output file if specified
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(validation_results, f, indent=2)
            console.print(f"Validation results written to {output_file}")
        except Exception as e:
            console.print(f"[red]Error:[/red] Could not write output file: {e}")
    
    # Return success status
    if not validation_results["success"]:
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def images(
    image1: str = typer.Argument(
        ..., help="Path to first image"
    ),
    image2: str = typer.Argument(
        ..., help="Path to second image"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Directory for output diff images"
    ),
    method: str = typer.Option(
        "pixel", "--method", "-m", help="Comparison method: pixel, hash, or ssim"
    ),
    threshold: float = typer.Option(
        0.1, "--threshold", "-t", help="Threshold for comparison (0.0-1.0)"
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Fail on any difference (exact match required)"
    ),
):
    """
    Compare two images using various methods.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("file-analyzer.validate")
    
    # Check if images exist
    if not os.path.exists(image1):
        console.print(f"[red]Error:[/red] Image does not exist: {image1}")
        raise typer.Exit(code=1)
    
    if not os.path.exists(image2):
        console.print(f"[red]Error:[/red] Image does not exist: {image2}")
        raise typer.Exit(code=1)
        
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = tempfile.mkdtemp(prefix="fa_image_diff_")
    
    # Result dictionary to track comparison outcomes
    result = {
        "success": False,
        "method": method,
        "threshold": threshold,
        "image1": image1,
        "image2": image2,
        "output_dir": output_dir,
        "details": {}
    }
    
    try:
        from PIL import Image
        
        # Load images
        img1 = Image.open(image1).convert("RGBA")
        img2 = Image.open(image2).convert("RGBA")
        
        # Check image sizes
        if img1.size != img2.size:
            console.print(f"[yellow]Warning:[/yellow] Images have different sizes: {img1.size} vs {img2.size}")
            result["details"]["size_mismatch"] = {
                "image1_size": img1.size,
                "image2_size": img2.size
            }
            
            if strict:
                console.print(f"[red]Error:[/red] Images must have exact same size in strict mode")
                result["details"]["error"] = "Size mismatch in strict mode"
                raise typer.Exit(code=1)
                
        # Perform comparison based on method
        if method == "pixel":
            # Pixel-wise comparison
            try:
                from pixelmatch.contrib.PIL import pixelmatch
                
                diff_output_path = os.path.join(output_dir, "pixel_diff.png")
                img_diff = Image.new("RGBA", img1.size)
                
                mismatch_count = pixelmatch(
                    img1, img2, img_diff,
                    includeAA=True, 
                    threshold=threshold
                )
                
                # Save diff image
                img_diff.save(diff_output_path)
                
                # Calculate mismatch percentage
                total_pixels = img1.size[0] * img1.size[1]
                mismatch_percent = (mismatch_count / total_pixels) * 100
                
                result["details"]["pixel_comparison"] = {
                    "mismatch_count": mismatch_count,
                    "total_pixels": total_pixels,
                    "mismatch_percent": mismatch_percent,
                    "diff_image": diff_output_path
                }
                
                if mismatch_count == 0:
                    console.print(f"[green]✓[/green] Images are pixel-perfect matches")
                    result["success"] = True
                else:
                    if strict:
                        console.print(f"[red]✗[/red] Images differ by {mismatch_count} pixels ({mismatch_percent:.2f}%)")
                        result["success"] = False
                    else:
                        if mismatch_percent < threshold * 100:
                            console.print(f"[green]✓[/green] Images are similar (differ by {mismatch_percent:.2f}% which is below threshold {threshold * 100:.2f}%)")
                            result["success"] = True
                        else:
                            console.print(f"[red]✗[/red] Images differ by {mismatch_percent:.2f}% which exceeds threshold {threshold * 100:.2f}%")
                            result["success"] = False
                            
                console.print(f"Diff image saved to {diff_output_path}")
                
            except ImportError:
                console.print(f"[red]Error:[/red] pixelmatch-py is required for pixel comparison")
                console.print(f"Install it with: pip install pixelmatch")
                result["details"]["error"] = "pixelmatch-py not installed"
                raise typer.Exit(code=1)
        
        elif method == "hash":
            # Perceptual hash comparison
            try:
                import imagehash
                
                # Calculate perceptual hashes
                hash1 = imagehash.phash(img1)
                hash2 = imagehash.phash(img2)
                
                # Calculate hamming distance
                distance = hash1 - hash2
                max_distance = len(hash1.hash) * len(hash1.hash[0])  # Size of the hash
                similarity = 1 - (distance / max_distance)
                
                result["details"]["hash_comparison"] = {
                    "hash1": str(hash1),
                    "hash2": str(hash2),
                    "distance": distance,
                    "max_distance": max_distance,
                    "similarity": similarity
                }
                
                if distance == 0:
                    console.print(f"[green]✓[/green] Images have identical perceptual hashes")
                    result["success"] = True
                else:
                    if strict:
                        console.print(f"[red]✗[/red] Images have different perceptual hashes (distance: {distance})")
                        result["success"] = False
                    else:
                        if similarity >= (1 - threshold):
                            console.print(f"[green]✓[/green] Images are perceptually similar (similarity: {similarity:.2f} which is above threshold {1 - threshold:.2f})")
                            result["success"] = True
                        else:
                            console.print(f"[red]✗[/red] Images are not similar enough (similarity: {similarity:.2f} which is below threshold {1 - threshold:.2f})")
                            result["success"] = False
            
            except ImportError:
                console.print(f"[red]Error:[/red] ImageHash is required for hash comparison")
                console.print(f"Install it with: pip install imagehash")
                result["details"]["error"] = "imagehash not installed"
                raise typer.Exit(code=1)
                
        elif method == "ssim":
            # Structural Similarity Index
            try:
                from skimage.metrics import structural_similarity
                import numpy as np
                
                # Convert to grayscale for SSIM
                img1_gray = img1.convert("L")
                img2_gray = img2.convert("L")
                
                # Convert to numpy arrays
                img1_array = np.array(img1_gray)
                img2_array = np.array(img2_gray)
                
                # Resize if necessary
                if img1_array.shape != img2_array.shape:
                    console.print(f"[yellow]Warning:[/yellow] Resizing images for SSIM comparison")
                    img2_array = np.array(img2_gray.resize(img1_gray.size))
                
                # Calculate SSIM
                ssim_score = structural_similarity(
                    img1_array, img2_array,
                    data_range=255
                )
                
                result["details"]["ssim_comparison"] = {
                    "ssim_score": ssim_score
                }
                
                if ssim_score == 1.0:
                    console.print(f"[green]✓[/green] Images are identical (SSIM: 1.0)")
                    result["success"] = True
                else:
                    if strict:
                        console.print(f"[red]✗[/red] Images differ (SSIM: {ssim_score:.4f})")
                        result["success"] = False
                    else:
                        threshold_adjusted = 1 - threshold  # Convert to similarity threshold
                        if ssim_score >= threshold_adjusted:
                            console.print(f"[green]✓[/green] Images are structurally similar (SSIM: {ssim_score:.4f} which is above threshold {threshold_adjusted:.4f})")
                            result["success"] = True
                        else:
                            console.print(f"[red]✗[/red] Images are not structurally similar enough (SSIM: {ssim_score:.4f} which is below threshold {threshold_adjusted:.4f})")
                            result["success"] = False
            
            except ImportError:
                console.print(f"[red]Error:[/red] scikit-image is required for SSIM comparison")
                console.print(f"Install it with: pip install scikit-image")
                result["details"]["error"] = "scikit-image not installed"
                raise typer.Exit(code=1)
                
        else:
            console.print(f"[red]Error:[/red] Unknown comparison method: {method}")
            console.print(f"Supported methods: pixel, hash, ssim")
            result["details"]["error"] = f"Unknown comparison method: {method}"
            raise typer.Exit(code=1)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        result["details"]["error"] = str(e)
        raise typer.Exit(code=1)
    
    # Write results to output file
    result_file = os.path.join(output_dir, "comparison_result.json")
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    console.print(f"Comparison results saved to {result_file}")
    
    # Return success status
    if not result["success"]:
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def run(
    artifact_dir: str = typer.Argument(
        ..., help="Path to analysis artifact directory"
    ),
    schema_type: str = typer.Option(
        "fastvlm", "--type", "-t", help="Schema type for validation"
    ),
    schema_version: str = typer.Option(
        "v1.0", "--version", "-v", help="Schema version for validation"
    ),
    output_dir: Optional[str] = typer.Option(
        None, "--output", "-o", help="Directory for validation outputs"
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Enable strict validation"
    ),
    fail_fast: bool = typer.Option(
        False, "--fail-fast", "-f", help="Stop on first validation failure"
    ),
):
    """
    Run a comprehensive validation on analysis artifacts.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("file-analyzer.validate")
    
    # Check if artifact directory exists
    if not os.path.exists(artifact_dir):
        console.print(f"[red]Error:[/red] Artifact directory does not exist: {artifact_dir}")
        raise typer.Exit(code=1)
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.path.join(artifact_dir, "validation")
        os.makedirs(output_dir, exist_ok=True)
    
    # Find all JSON files in the artifact directory
    json_files = []
    for root, _, files in os.walk(artifact_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    if not json_files:
        console.print(f"[yellow]Warning:[/yellow] No JSON files found in {artifact_dir}")
    
    # Save validation environment info
    env_info = {
        "timestamp": time.time(),
        "artifact_dir": artifact_dir,
        "output_dir": output_dir,
        "schema_type": schema_type,
        "schema_version": schema_version,
        "strict": strict,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }
    
    env_file = os.path.join(output_dir, "validation_environment.json")
    with open(env_file, 'w') as f:
        json.dump(env_info, f, indent=2)
    
    # Validate all JSON files
    validation_results = []
    
    console.print(f"Validating {len(json_files)} JSON files...")
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Validating files...", total=len(json_files))
        
        for json_file in json_files:
            relative_path = os.path.relpath(json_file, artifact_dir)
            progress.update(task, description=f"Validating [cyan]{relative_path}[/cyan]...")
            
            result = {
                "file": json_file,
                "relative_path": relative_path,
                "success": False,
                "errors": [],
                "warnings": []
            }
            
            # Load JSON file
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                result["errors"].append(f"Invalid JSON: {e}")
                validation_results.append(result)
                
                if fail_fast:
                    logger.error(f"Validation failed on {relative_path}: {e}")
                    break
                    
                progress.update(task, advance=1)
                continue
            except Exception as e:
                result["errors"].append(f"Could not read file: {e}")
                validation_results.append(result)
                
                if fail_fast:
                    logger.error(f"Validation failed on {relative_path}: {e}")
                    break
                    
                progress.update(task, advance=1)
                continue
            
            # Get schema
            schema_path = config.get_schema_path(schema_type, schema_version)
            
            if not schema_path or not os.path.exists(schema_path):
                result["errors"].append(f"Schema not found for {schema_type} version {schema_version}")
                validation_results.append(result)
                
                if fail_fast:
                    logger.error(f"Schema not found for {schema_type} version {schema_version}")
                    break
                    
                progress.update(task, advance=1)
                continue
            
            # Load schema
            try:
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
            except Exception as e:
                result["errors"].append(f"Could not read schema: {e}")
                validation_results.append(result)
                
                if fail_fast:
                    logger.error(f"Could not read schema: {e}")
                    break
                    
                progress.update(task, advance=1)
                continue
            
            # Validate against schema
            try:
                jsonschema.validate(data, schema)
                result["success"] = True
            except jsonschema.exceptions.ValidationError as e:
                result["errors"].append({
                    "path": ".".join(str(p) for p in e.path),
                    "message": e.message,
                    "schema_path": ".".join(str(p) for p in e.schema_path)
                })
            except jsonschema.exceptions.SchemaError as e:
                result["errors"].append({
                    "message": f"Schema error: {e.message}",
                    "schema_path": ".".join(str(p) for p in e.schema_path)
                })
            
            # Additional checks
            # 1. Check for empty fields
            if "properties" in schema:
                for prop, details in schema["properties"].items():
                    if prop in data and (data[prop] == "" or data[prop] == [] or data[prop] == {}):
                        result["warnings"].append({
                            "path": prop,
                            "message": f"Property '{prop}' is empty"
                        })
            
            # 2. Check required fields
            if "required" in schema:
                for prop in schema["required"]:
                    if prop not in data:
                        result["errors"].append({
                            "path": "",
                            "message": f"Required property '{prop}' is missing"
                        })
                        result["success"] = False
            
            # Apply strict mode
            if strict and result["warnings"]:
                result["success"] = False
            
            # Add to results
            validation_results.append(result)
            
            # Check fail-fast
            if fail_fast and not result["success"]:
                logger.error(f"Validation failed on {relative_path}")
                break
                
            progress.update(task, advance=1)
    
    # Compute summary
    passed = sum(1 for r in validation_results if r["success"])
    failed = len(validation_results) - passed
    
    # Print summary table
    table = Table(title=f"Validation Results: {passed} passed, {failed} failed")
    table.add_column("File", style="cyan")
    table.add_column("Result", style="green")
    table.add_column("Errors", style="red")
    table.add_column("Warnings", style="yellow")
    
    for result in validation_results:
        file_path = result["relative_path"]
        success = result["success"]
        errors = len(result["errors"])
        warnings = len(result["warnings"])
        
        result_text = "[green]PASS[/green]" if success else "[red]FAIL[/red]"
        
        table.add_row(file_path, result_text, str(errors), str(warnings))
    
    console.print(table)
    
    # Save results
    summary = {
        "timestamp": time.time(),
        "artifact_dir": artifact_dir,
        "output_dir": output_dir,
        "total_files": len(json_files),
        "passed": passed,
        "failed": failed,
        "results": validation_results
    }
    
    summary_file = os.path.join(output_dir, "validation_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    console.print(f"Validation summary saved to {summary_file}")
    
    # Return success status
    if failed > 0:
        raise typer.Exit(code=1)
    
    return 0

@app.command()
def manifest(
    manifest_file: str = typer.Argument(
        ..., help="Path to manifest file"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o", help="Path to output file for validation results"
    ),
):
    """
    Validate a manifest file and its referenced artifacts.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("file-analyzer.validate")
    
    # Check if manifest file exists
    if not os.path.exists(manifest_file):
        console.print(f"[red]Error:[/red] Manifest file does not exist: {manifest_file}")
        raise typer.Exit(code=1)
    
    # Load the manifest file
    try:
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON in manifest file: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not read manifest file: {e}")
        raise typer.Exit(code=1)
    
    # Validate manifest structure
    if not isinstance(manifest, dict):
        console.print(f"[red]Error:[/red] Manifest must be a JSON object")
        raise typer.Exit(code=1)
    
    # Check for required fields
    required_fields = ["timestamp", "version", "artifacts"]
    missing_fields = [field for field in required_fields if field not in manifest]
    
    if missing_fields:
        console.print(f"[red]Error:[/red] Missing required fields in manifest: {', '.join(missing_fields)}")
        raise typer.Exit(code=1)
    
    # Check artifacts
    if not isinstance(manifest["artifacts"], list):
        console.print(f"[red]Error:[/red] Manifest 'artifacts' must be an array")
        raise typer.Exit(code=1)
    
    # Results tracking
    results = {
        "success": True,
        "manifest": manifest_file,
        "version": manifest.get("version", "unknown"),
        "timestamp": manifest.get("timestamp", "unknown"),
        "artifacts_total": len(manifest["artifacts"]),
        "artifacts_found": 0,
        "artifacts_missing": 0,
        "artifacts": []
    }
    
    # Get manifest directory to resolve relative paths
    manifest_dir = os.path.dirname(os.path.abspath(manifest_file))
    
    # Check each artifact
    for i, artifact in enumerate(manifest["artifacts"]):
        artifact_result = {
            "index": i,
            "success": False,
            "errors": [],
            "warnings": []
        }
        
        # Check artifact structure
        if not isinstance(artifact, dict):
            artifact_result["errors"].append("Artifact must be a JSON object")
            results["artifacts"].append(artifact_result)
            continue
        
        # Check required artifact fields
        required_artifact_fields = ["path", "type"]
        missing_artifact_fields = [field for field in required_artifact_fields if field not in artifact]
        
        if missing_artifact_fields:
            artifact_result["errors"].append(f"Missing required fields: {', '.join(missing_artifact_fields)}")
            results["artifacts"].append(artifact_result)
            continue
        
        # Copy metadata to result
        artifact_result["path"] = artifact["path"]
        artifact_result["type"] = artifact["type"]
        
        # Resolve artifact path (relative to manifest)
        artifact_path = artifact["path"]
        if not os.path.isabs(artifact_path):
            artifact_path = os.path.join(manifest_dir, artifact_path)
        
        # Check if artifact exists
        if not os.path.exists(artifact_path):
            artifact_result["errors"].append(f"Artifact file not found: {artifact_path}")
            results["artifacts_missing"] += 1
        else:
            artifact_result["success"] = True
            results["artifacts_found"] += 1
            
            # Additional checks based on artifact type
            if artifact["type"] == "json":
                try:
                    with open(artifact_path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    artifact_result["errors"].append(f"Invalid JSON: {e}")
                    artifact_result["success"] = False
                except Exception as e:
                    artifact_result["errors"].append(f"Could not read file: {e}")
                    artifact_result["success"] = False
            elif artifact["type"] == "image":
                try:
                    from PIL import Image
                    img = Image.open(artifact_path)
                    artifact_result["metadata"] = {
                        "format": img.format,
                        "size": img.size,
                        "mode": img.mode
                    }
                except Exception as e:
                    artifact_result["errors"].append(f"Could not read image: {e}")
                    artifact_result["success"] = False
        
        # Add to results
        results["artifacts"].append(artifact_result)
    
    # Update success status
    results["success"] = results["artifacts_missing"] == 0 and all(a.get("success", False) for a in results["artifacts"])
    
    # Print summary
    console.print(f"Manifest version: {results['version']}")
    console.print(f"Artifacts: {results['artifacts_found']} found, {results['artifacts_missing']} missing")
    
    if results["success"]:
        console.print(f"[green]✓[/green] All artifacts validated successfully")
    else:
        console.print(f"[red]✗[/red] Validation failed")
        
        # Print details of failed artifacts
        for artifact in results["artifacts"]:
            if not artifact.get("success", False):
                console.print(f"[red]✗[/red] {artifact.get('path', 'unknown')}: {', '.join(artifact.get('errors', []))}")
    
    # Write results to output file if specified
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            console.print(f"Validation results written to {output_file}")
        except Exception as e:
            console.print(f"[red]Error:[/red] Could not write output file: {e}")
    
    # Return success status
    if not results["success"]:
        raise typer.Exit(code=1)
    
    return 0

if __name__ == "__main__":
    app()