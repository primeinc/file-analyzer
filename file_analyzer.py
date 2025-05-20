#!/usr/bin/env python3
"""
Unified File Analysis System

Combines multiple tools for comprehensive file analysis:
- ExifTool: Metadata extraction
- rdfind: Duplicate detection
- Tesseract: OCR for images
- ClamAV: Malware scanning
- ripgrep: Content searching
- binwalk: Binary analysis
- Vision Models: AI-powered image analysis (FastVLM, BakLLaVA, Qwen2-VL)
"""

import os
import sys
import subprocess
import argparse
import json
import shutil
import time
import fnmatch
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Import vision analyzer module
try:
    from vision_analyzer import VisionAnalyzer, DEFAULT_VISION_CONFIG, VISION_MODELS
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

# Required external tools and their corresponding analysis types
REQUIRED_TOOLS = {
    "exiftool": "metadata",
    "rdfind": "duplicates",
    "tesseract": "ocr",
    "clamscan": "malware",
    "rg": "search",
    "binwalk": "binary",
    "python": "vision"  # Python is required for vision analysis
}

# Default configuration
DEFAULT_CONFIG = {
    "default_output_dir": "analysis_results",
    "max_threads": os.cpu_count(),
    "max_ocr_images": 50,
    "file_extensions": {
        "images": [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"]
    },
    "tool_options": {},
    "default_include_patterns": [],
    "default_exclude_patterns": [],
    "vision": {} if not VISION_AVAILABLE else DEFAULT_VISION_CONFIG
}

def load_config(config_path=None):
    """Load configuration from a JSON file with fallback to defaults."""
    config = DEFAULT_CONFIG.copy()
    
    # Look for config file in default locations if not specified
    if not config_path:
        # Try current directory first
        if Path("config.json").exists():
            config_path = "config.json"
        # Then try user's home directory
        elif Path.home().joinpath(".config/file_analyzer/config.json").exists():
            config_path = Path.home().joinpath(".config/file_analyzer/config.json")
    
    # Load config from file if available
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                
            # Update default config with file config
            for key, value in file_config.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value
                    
            print(f"Loaded configuration from {config_path}")
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
    
    return config

def check_dependencies(required_tools=None):
    """Check if required external tools are installed and available in PATH."""
    if required_tools is None:
        required_tools = REQUIRED_TOOLS
    
    missing_tools = {}
    
    for tool, analysis_type in required_tools.items():
        if shutil.which(tool) is None:
            missing_tools[tool] = analysis_type
    
    return missing_tools

class ProgressIndicator:
    """Simple progress indicator for long-running operations."""
    
    def __init__(self, description="Processing", interval=0.2):
        self.description = description
        self.interval = interval
        self.running = False
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current_index = 0
        self.start_time = None
    
    def start(self):
        """Start displaying the progress indicator."""
        self.running = True
        self.start_time = time.time()
        self._update()
    
    def stop(self, message="Done"):
        """Stop the progress indicator and display a completion message."""
        self.running = False
        elapsed = time.time() - self.start_time if self.start_time else 0
        sys.stdout.write(f"\r{self.description}: {message} (took {elapsed:.1f}s)       \n")
    
    def _update(self):
        """Update the spinner animation."""
        if not self.running:
            return
        
        spinner = self.spinner_chars[self.current_index]
        sys.stdout.write(f"\r{self.description}: {spinner} ")
        sys.stdout.flush()
        
        self.current_index = (self.current_index + 1) % len(self.spinner_chars)
        
        # Schedule the next update
        def _next_update():
            if self.running:
                time.sleep(self.interval)
                self._update()
        
        # Use a separate thread to avoid blocking
        import threading
        threading.Thread(target=_next_update).start()


class FileAnalyzer:
    def __init__(self, path, output_dir=None, verbose=True, include_patterns=None, exclude_patterns=None, config=None):
        self.path = Path(path).expanduser().absolute()
        if not self.path.exists():
            raise FileNotFoundError(f"Path does not exist: {self.path}")
        
        # Load configuration
        self.config = config or load_config()
        
        # Set output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        elif "default_output_dir" in self.config:
            self.output_dir = Path(self.config["default_output_dir"])
        else:
            self.output_dir = Path.cwd()
            
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {
            "path": str(self.path),
            "time": datetime.now().isoformat(),
            "analyses": {}
        }
        
        # Set file extensions from config
        if "file_extensions" in self.config and "images" in self.config["file_extensions"]:
            self.image_extensions = set(self.config["file_extensions"]["images"])
        else:
            self.image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif'}
            
        self.verbose = verbose
        
        # Combine user-specified patterns with defaults from config
        self.include_patterns = list(include_patterns or [])
        if not self.include_patterns and "default_include_patterns" in self.config:
            self.include_patterns = list(self.config["default_include_patterns"])
            
        self.exclude_patterns = list(exclude_patterns or [])
        if not self.exclude_patterns and "default_exclude_patterns" in self.config:
            self.exclude_patterns = list(self.config["default_exclude_patterns"])
        
    def should_process_file(self, file_path):
        """Determine if a file should be processed based on include/exclude patterns."""
        file_path_str = str(file_path)
        
        # If we have include patterns, file must match at least one
        if self.include_patterns and not any(fnmatch.fnmatch(file_path_str, pattern) for pattern in self.include_patterns):
            return False
        
        # If file matches any exclude pattern, skip it
        if any(fnmatch.fnmatch(file_path_str, pattern) for pattern in self.exclude_patterns):
            return False
            
        return True
        
    def run_command(self, command, shell=False):
        try:
            if self.verbose:
                print(f"Running command: {' '.join(str(c) for c in command)}")
            result = subprocess.run(command, shell=shell, check=True, 
                                  capture_output=True, text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {' '.join(str(c) for c in command)}")
            print(f"Return code: {e.returncode}")
            print(f"Error output: {e.stderr}")
            return None
        except Exception as e:
            print(f"Unexpected error running command: {' '.join(str(c) for c in command)}")
            print(f"Error: {str(e)}")
            return None

    def extract_metadata(self):
        if self.verbose:
            print(f"Extracting metadata from {self.path}...")
            progress = ProgressIndicator("Extracting metadata")
            progress.start()
        
        # Get list of files to process if it's a directory
        files_to_process = []
        if self.path.is_dir():
            # If we're processing a directory, collect files first with filtering
            if self.verbose:
                print("Collecting files to process...")
            
            for root, _, files in os.walk(self.path):
                for file in files:
                    file_path = Path(root) / file
                    if self.should_process_file(file_path):
                        files_to_process.append(file_path)
            
            if self.verbose:
                print(f"Found {len(files_to_process)} files to process")
                
            # Limit the number of files to process
            max_files = self.config.get("max_metadata_files", 50)
            if len(files_to_process) > max_files:
                if self.verbose:
                    print(f"Limiting to {max_files} files")
                files_to_process = files_to_process[:max_files]
                
            # Process collected files directly
            if files_to_process:
                # Get exiftool options from config
                exiftool_options = self.config.get("tool_options", {}).get("exiftool", [])
                command = ["exiftool", "-json"]
                
                # Check if -json is already in the config options to avoid duplication
                filtered_options = [opt for opt in exiftool_options if opt != "-json"]
                command.extend(filtered_options)
                
                # Add all files to process
                for file_path in files_to_process:
                    command.append(str(file_path))
            else:
                if self.verbose:
                    progress.stop("No matching files found")
                self.results["analyses"]["metadata"] = {"status": "skipped"}
                return None
        else:
            # If it's a single file, just process it directly
            if not self.should_process_file(self.path):
                if self.verbose:
                    progress.stop("File excluded by pattern")
                self.results["analyses"]["metadata"] = {"status": "skipped"}
                return None
                
            # Get exiftool options from config
            exiftool_options = self.config.get("tool_options", {}).get("exiftool", [])
            command = ["exiftool", "-json"]
            
            # Check if -json is already in the config options to avoid duplication
            filtered_options = [opt for opt in exiftool_options if opt != "-json"]
            command.extend(filtered_options)
            
            command.append(str(self.path))
        
        # Add debug information
        if self.verbose:
            print(f"Preparing to extract metadata with command: {' '.join(command)}")
        
        output = self.run_command(command)
        
        if not output:
            if self.verbose:
                progress.stop("Failed to extract metadata")
            self.results["analyses"]["metadata"] = {
                "status": "error",
                "message": "Command failed or returned no output"
            }
            return None
            
        try:
            # Try to parse JSON output
            try:
                # ExifTool might return warnings before the JSON data
                # Try to find the start of the JSON data (opening bracket)
                json_start = output.find('[')
                if json_start >= 0:
                    json_data = output[json_start:]
                    metadata = json.loads(json_data)
                else:
                    raise json.JSONDecodeError("No JSON start marker found", output, 0)
            except json.JSONDecodeError as e:
                # If full parsing fails, try to get partial output
                if self.verbose:
                    print(f"JSON decode error: {str(e)}")
                    print(f"First 500 characters of output: {output[:500]}")
                
                # Write the raw output for debugging
                debug_file = self.output_dir / f"metadata_debug_{self.timestamp}.txt"
                with open(debug_file, 'w') as f:
                    f.write(output)
                
                if self.verbose:
                    print(f"Wrote raw output to {debug_file} for debugging")
                    progress.stop("Failed (JSON decode error)")
                
                self.results["analyses"]["metadata"] = {
                    "status": "error",
                    "message": f"JSON decode error: {str(e)}",
                    "debug_file": str(debug_file)
                }
                return None
            
            # Save metadata to file
            output_file = self.output_dir / f"metadata_{self.timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            if self.verbose:
                progress.stop(f"Complete ({len(metadata)} items)")
                print(f"Metadata saved to {output_file}")
                
            self.results["analyses"]["metadata"] = {
                "status": "success",
                "file": str(output_file),
                "count": len(metadata)
            }
            return metadata
            
        except Exception as e:
            if self.verbose:
                progress.stop(f"Failed with error: {str(e)}")
            self.results["analyses"]["metadata"] = {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
            return None

    def find_duplicates(self):
        print(f"Finding duplicates in {self.path}...")
        
        if self.path.is_file():
            print("Duplicate finding only works on directories.")
            self.results["analyses"]["duplicates"] = {"status": "skipped"}
            return None
        
        results_file = self.output_dir / f"duplicates_{self.timestamp}.txt"
        command = ["rdfind", "-outputname", str(results_file), str(self.path)]
        output = self.run_command(command)
        
        if output and results_file.exists():
            print(f"Duplicate analysis saved to {results_file}")
            self.results["analyses"]["duplicates"] = {
                "status": "success",
                "file": str(results_file)
            }
            return results_file
        else:
            self.results["analyses"]["duplicates"] = {"status": "error"}
            return None

    def perform_ocr(self):
        if self.verbose:
            print(f"Performing OCR on images in {self.path}...")
            progress = ProgressIndicator("Searching for image files")
            progress.start()
        
        # Find image files
        image_files = []
        if self.path.is_dir():
            for root, _, files in os.walk(self.path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in self.image_extensions and self.should_process_file(file_path):
                        image_files.append(file_path)
        elif self.path.suffix.lower() in self.image_extensions and self.should_process_file(self.path):
            image_files.append(self.path)
        
        if not image_files:
            if self.verbose:
                progress.stop("No images found")
            self.results["analyses"]["ocr"] = {"status": "skipped"}
            return None
        
        if self.verbose:
            progress.stop(f"Found {len(image_files)} image(s)")
            progress = ProgressIndicator(f"Processing {min(len(image_files), 50)} images")
            progress.start()
        
        # Get max images from config (default to 50)
        max_ocr_images = self.config.get("max_ocr_images", 50)
        max_threads = self.config.get("max_threads", os.cpu_count())
        
        # Process images with limits
        ocr_results = {}
        
        def process_image(img_path):
            try:
                # Get tesseract options from config
                tesseract_options = self.config.get("tool_options", {}).get("tesseract", [])
                command = ["tesseract"]
                command.extend(tesseract_options)
                command.extend([str(img_path), "stdout"])
                
                output = self.run_command(command)
                return str(img_path), output.strip() if output else "No text extracted"
            except Exception as e:
                return str(img_path), f"Error: {str(e)}"
        
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            for img_path, text in executor.map(process_image, image_files[:max_ocr_images]):
                ocr_results[img_path] = text
        
        # Save results
        output_file = self.output_dir / f"ocr_results_{self.timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(ocr_results, f, indent=2)
        
        if self.verbose:
            progress.stop(f"Completed OCR on {len(ocr_results)} images")
            print(f"OCR results saved to {output_file}")
            
        self.results["analyses"]["ocr"] = {
            "status": "success",
            "file": str(output_file),
            "count": len(ocr_results)
        }
        
        return ocr_results

    def scan_malware(self):
        print(f"Scanning for malware in {self.path}...")
        
        command = ["clamscan", "-r", "--bell", "-i", str(self.path)]
        output = self.run_command(command)
        
        if output:
            output_file = self.output_dir / f"malware_scan_{self.timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write(output)
            
            print(f"Malware scan results saved to {output_file}")
            self.results["analyses"]["malware"] = {
                "status": "success",
                "file": str(output_file)
            }
            return output
        else:
            self.results["analyses"]["malware"] = {"status": "error"}
            return None

    def search_content(self, search_text):
        if self.verbose:
            print(f"Searching for '{search_text}' in {self.path}...")
            progress = ProgressIndicator("Searching content")
            progress.start()
        
        if not search_text:
            if self.verbose:
                progress.stop("No search text provided")
            self.results["analyses"]["search"] = {"status": "skipped"}
            return None
        
        command = ["rg", "-i", "--line-number", search_text, str(self.path)]
        
        # Apply file type filtering
        if self.include_patterns:
            for pattern in self.include_patterns:
                command.extend(["-g", pattern])
        
        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                command.extend(["-g", f"!{pattern}"])
        
        output = self.run_command(command)
        
        if output:
            output_file = self.output_dir / f"search_{search_text}_{self.timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write(output)
            
            match_count = len(output.splitlines())
            if self.verbose:
                progress.stop(f"Found {match_count} matches")
                print(f"Results saved to {output_file}")
                
            self.results["analyses"]["search"] = {
                "status": "success", 
                "query": search_text,
                "file": str(output_file),
                "matches": match_count
            }
            return output
        else:
            if self.verbose:
                progress.stop("No matches found")
                
            self.results["analyses"]["search"] = {
                "status": "completed",
                "query": search_text,
                "matches": 0
            }
            return None

    def analyze_binary(self):
        print(f"Analyzing binary content in {self.path}...")
        
        if self.path.is_dir():
            print("Binary analysis needs a specific file.")
            self.results["analyses"]["binary"] = {"status": "skipped"}
            return None
        
        command = ["binwalk", "-B", "-e", "--term", str(self.path)]
        output = self.run_command(command)
        
        if output:
            output_file = self.output_dir / f"binary_analysis_{self.timestamp}.txt"
            with open(output_file, 'w') as f:
                f.write(output)
            
            print(f"Binary analysis saved to {output_file}")
            self.results["analyses"]["binary"] = {
                "status": "success",
                "file": str(output_file)
            }
            return output
        else:
            self.results["analyses"]["binary"] = {"status": "error"}
            return None
            
    def analyze_images_with_vision(self, mode="describe"):
        """Analyze images using vision models."""
        if not VISION_AVAILABLE:
            print("Vision analysis module not available.")
            self.results["analyses"]["vision"] = {"status": "skipped", "message": "Vision module not available"}
            return None
            
        if self.verbose:
            print(f"Analyzing images in {self.path} with vision models...")
            progress = ProgressIndicator("Initializing vision analysis")
            progress.start()
            
        # Find image files
        image_files = []
        if self.path.is_dir():
            for root, _, files in os.walk(self.path):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in self.image_extensions and self.should_process_file(file_path):
                        image_files.append(file_path)
        elif self.path.suffix.lower() in self.image_extensions and self.should_process_file(self.path):
            image_files.append(self.path)
            
        if not image_files:
            if self.verbose:
                progress.stop("No images found")
            self.results["analyses"]["vision"] = {"status": "skipped", "message": "No images found"}
            return None
            
        # Set up vision analyzer with configuration
        vision_config = self.config.get("vision", {})
        analyzer = VisionAnalyzer(vision_config)
        
        # Check dependencies
        if not analyzer.check_dependencies():
            if self.verbose:
                progress.stop("Missing vision model dependencies")
                print(f"Required dependencies for {analyzer.model_info['name']} not installed.")
                print(f"Run '{analyzer.model_info['install_cmd']}' to install.")
            self.results["analyses"]["vision"] = {
                "status": "error", 
                "message": f"Missing dependencies for {analyzer.model_info['name']}"
            }
            return None
            
        if self.verbose:
            progress.stop(f"Found {len(image_files)} image(s)")
            model_name = analyzer.model_info["name"]
            print(f"Using {model_name} model for vision analysis")
            progress = ProgressIndicator(f"Analyzing images with {model_name}")
            progress.start()
            
        # Determine if batch processing or individual
        results = {}
        max_images = vision_config.get("max_images", 10)  # Limit the number of images to process
        
        if len(image_files) > max_images:
            if self.verbose:
                print(f"Limiting to {max_images} images (out of {len(image_files)})")
            image_files = image_files[:max_images]
            
        # Process images based on configuration
        if self.path.is_dir() and vision_config.get("batch_processing", False):
            # Batch processing for directory
            batch_output_dir = Path(self.output_dir) / f"vision_{self.timestamp}"
            batch_output_dir.mkdir(exist_ok=True, parents=True)
            results = analyzer.batch_analyze(str(self.path), str(batch_output_dir), mode)
        else:
            # Process each image individually
            for image_path in image_files:
                if self.verbose:
                    print(f"Analyzing image: {image_path}")
                result = analyzer.analyze_image(str(image_path), mode=mode)
                if result:
                    results[str(image_path)] = result
                    
        if not results:
            if self.verbose:
                progress.stop("Analysis failed")
            self.results["analyses"]["vision"] = {"status": "error", "message": "Analysis failed"}
            return None
            
        # Save results to file
        if results:
            output_file = self.output_dir / f"vision_analysis_{self.timestamp}.{vision_config.get('output_format', 'text')}" 
            
            # Collect performance metrics
            total_time = 0
            avg_time = 0
            model_name = analyzer.model_info["name"]
            model_size = ""
            
            # Extract model size/variant if possible
            if model_name == "FastVLM":
                model_path = str(analyzer.model_path)
                if "0.5b" in model_path.lower():
                    model_size = "0.5B"
                elif "1.5b" in model_path.lower():
                    model_size = "1.5B"
                elif "7b" in model_path.lower():
                    model_size = "7B"
            
            # Calculate metrics
            for result_text in results.values():
                # Try to extract timing information
                try:
                    if isinstance(result_text, dict) and "metadata" in result_text:
                        if "analysis_time" in result_text["metadata"]:
                            total_time += result_text["metadata"]["analysis_time"]
                    elif isinstance(result_text, str) and "Analysis - " in result_text:
                        # Extract time from formatted string
                        time_str = result_text.split("Analysis - ")[1].split("s")[0]
                        total_time += float(time_str)
                except (ValueError, IndexError, KeyError, AttributeError):
                    pass
            
            # Calculate average time
            if results:
                avg_time = total_time / len(results)
            
            # Add to results metadata
            performance_metrics = {
                "model": f"{model_name}{' ' + model_size if model_size else ''}",
                "total_time": total_time,
                "average_time": avg_time,
                "images_processed": len(results)
            }
            
            # Add to summary results
            performance_summary = f"\nPerformance Metrics:\n"
            performance_summary += f"  Model: {performance_metrics['model']}\n"
            performance_summary += f"  Total processing time: {total_time:.2f}s\n"
            performance_summary += f"  Average per image: {avg_time:.2f}s\n"
            performance_summary += f"  Images processed: {performance_metrics['images_processed']}\n"
            
            # Save results with performance metrics
            saved_file = analyzer.save_results(results, output_file)
            
            # Save performance metrics separately
            metrics_file = self.output_dir / f"vision_metrics_{self.timestamp}.json"
            with open(metrics_file, 'w') as f:
                json.dump(performance_metrics, f, indent=2)
            
            if self.verbose:
                progress.stop(f"Completed analysis of {len(results)} images")
                if saved_file:
                    print(f"Vision analysis results saved to {saved_file}")
                    print(performance_summary)
                    print(f"Detailed metrics saved to {metrics_file}")
                else:
                    print("No results were saved")
            
            # Include metrics in the results
            self.results["analyses"]["vision"] = {
                "status": "success",
                "file": str(saved_file) if saved_file else None,
                "model": performance_metrics["model"],
                "mode": mode,
                "count": len(results),
                "performance": performance_metrics
            }
        else:
            if self.verbose:
                progress.stop("No results to save")
            self.results["analyses"]["vision"] = {"status": "completed", "message": "No results to save"}
            return None
            
        self.results["analyses"]["vision"] = {
            "status": "success",
            "file": str(output_file),
            "model": analyzer.model_info["name"],
            "mode": mode,
            "count": len(results)
        }
        
        return results

    def save_results(self):
        results_file = self.output_dir / f"analysis_summary_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nAnalysis complete. Summary saved to {results_file}")
        return results_file


def main():
    # Create a parser with more detailed help
    parser = argparse.ArgumentParser(
        description='File Analysis System - Comprehensive file analysis tool',
        epilog='''
Examples:
  # Run all analyses on a directory
  %(prog)s --all ~/Documents
  
  # Extract metadata and find duplicates
  %(prog)s --metadata --duplicates ~/Pictures
  
  # Search for specific content
  %(prog)s --search "password" ~/Downloads
  
  # OCR images in a directory
  %(prog)s --ocr ~/Screenshots
  
  # Analyze images with vision models
  %(prog)s --vision ~/Pictures
  
  # Vision analysis with specific mode
  %(prog)s --vision --vision-mode document ~/Documents
  
  # Include only specific file types
  %(prog)s --all --include "*.jpg" --include "*.png" ~/Pictures
  
  # Exclude specific patterns
  %(prog)s --all --exclude "*.log" --exclude "*.tmp" ~/Documents
  
  # Use a custom config file and quiet mode
  %(prog)s --all --config ~/my_config.json --quiet ~/Documents
  
  # Metadata extraction with custom output directory
  %(prog)s --metadata --output ~/analysis_results ~/Documents
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add arguments with more detailed help
    parser.add_argument('path', help='Path to file/directory to analyze')
    parser.add_argument('--metadata', '-m', action='store_true', 
                        help='Extract metadata using ExifTool (file type, dates, camera info, etc.)')
    parser.add_argument('--duplicates', '-d', action='store_true', 
                        help='Find duplicate files using rdfind (only works on directories)')
    parser.add_argument('--ocr', '-o', action='store_true', 
                        help='Perform OCR on images using Tesseract (extracts text from images)')
    parser.add_argument('--malware', '-v', action='store_true', 
                        help='Scan for malware using ClamAV (virus detection)')
    parser.add_argument('--search', '-s', 
                        help='Search content using ripgrep (find text in files)')
    parser.add_argument('--binary', '-b', action='store_true', 
                        help='Analyze binary content using binwalk (identify embedded files)')
    parser.add_argument('--vision', '-V', action='store_true',
                        help='Analyze images using AI vision models (FastVLM, BakLLaVA, etc.)')
    parser.add_argument('--vision-model', 
                        choices=['fastvlm', 'bakllava', 'qwen2vl'] if VISION_AVAILABLE else None,
                        help='Specify which vision model to use for analysis')
    parser.add_argument('--vision-mode',
                        choices=['describe', 'detect', 'document'],
                        default='describe',
                        help='Vision analysis mode: describe (default), detect objects, or document OCR')
    parser.add_argument('--all', '-a', action='store_true', 
                        help='Run all analyses (equivalent to -m -d -o -v -b, does not include vision)')
    parser.add_argument('--output', '-r', 
                        help='Output directory for results (default: current directory or config)')
    parser.add_argument('--skip-dependency-check', action='store_true', 
                        help='Skip checking for required external tools (use if tools are installed but not in PATH)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Quiet mode with minimal output (no progress indicators)')
    parser.add_argument('--include', '-i', action='append', 
                        help='Include only files matching pattern (glob syntax, can be used multiple times)')
    parser.add_argument('--exclude', '-x', action='append',
                        help='Exclude files matching pattern (glob syntax, can be used multiple times)')
    parser.add_argument('--config', '-c', 
                        help='Path to custom configuration file (JSON format)')
    
    args = parser.parse_args()
    
    try:
        # Determine which analyses to run
        run_all = args.all or not any([
            args.metadata, args.duplicates, args.ocr, 
            args.malware, args.search, args.binary, args.vision
        ])
        
        # Check for required tools based on requested analyses
        if not args.skip_dependency_check:
            tools_to_check = {}
            if run_all or args.metadata:
                tools_to_check["exiftool"] = "metadata"
            if run_all or args.duplicates:
                tools_to_check["rdfind"] = "duplicates"
            if run_all or args.ocr:
                tools_to_check["tesseract"] = "ocr"
            if run_all or args.malware:
                tools_to_check["clamscan"] = "malware"
            if args.search:
                tools_to_check["rg"] = "search"
            if (run_all or args.binary):
                tools_to_check["binwalk"] = "binary"
            if args.vision:
                tools_to_check["python"] = "vision"
            
            missing_tools = check_dependencies(tools_to_check)
            
            if missing_tools:
                print("ERROR: Missing required tools for requested analyses:")
                for tool, analysis in missing_tools.items():
                    print(f"  - {tool}: required for {analysis} analysis")
                print("\nPlease install the missing tools and try again.")
                print("Installation instructions can be found in the project documentation.")
                sys.exit(1)
        
        # Load configuration
        config = load_config(args.config)
        
        # Update vision-specific configuration if needed
        if args.vision and VISION_AVAILABLE:
            if "vision" not in config:
                config["vision"] = DEFAULT_VISION_CONFIG.copy()
            if args.vision_model:
                config["vision"]["model"] = args.vision_model
        
        # Initialize file analyzer with configuration
        analyzer = FileAnalyzer(
            args.path, 
            args.output, 
            verbose=not args.quiet,
            include_patterns=args.include,
            exclude_patterns=args.exclude,
            config=config
        )
        
        if run_all or args.metadata:
            analyzer.extract_metadata()
        
        if run_all or args.duplicates:
            analyzer.find_duplicates()
        
        if run_all or args.ocr:
            analyzer.perform_ocr()
        
        if run_all or args.malware:
            analyzer.scan_malware()
        
        if args.search:
            analyzer.search_content(args.search)
        
        if (run_all or args.binary) and not args.path.is_dir():
            analyzer.analyze_binary()
            
        if args.vision and VISION_AVAILABLE:
            analyzer.analyze_images_with_vision(args.vision_mode)
        
        analyzer.save_results()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()