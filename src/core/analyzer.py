#!/usr/bin/env python3
"""
Main file analyzer entry point

Provides a unified interface for all file analysis capabilities:
- Metadata extraction
- Duplicate detection
- OCR text extraction
- Malware scanning
- Content searching
- Binary analysis
- AI-powered model analysis

This replaces the previous file_analyzer.py with a more maintainable
Python-only implementation instead of relying on the bash script.
"""

import os
import sys
import argparse
import logging
import json
import re
import shutil
import subprocess
import fnmatch
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import artifact discipline components
from src.core.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard,
    safe_write
)

# Import model analysis components
from src.models.analyzer import ModelAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileAnalyzer:
    """Main class for the file analyzer system."""
    
    def __init__(self, config=None):
        """Initialize the file analyzer with optional configuration."""
        self.config = config or {}
        self.results = {}
        self.model_analyzer = ModelAnalyzer(self.config)
        
        # Set file extensions from config for filtering
        if "file_extensions" in self.config and "images" in self.config["file_extensions"]:
            self.image_extensions = set(self.config["file_extensions"]["images"])
        else:
            self.image_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
            
        # Include/exclude patterns for file filtering
        self.include_patterns = self.config.get("default_include_patterns", [])
        self.exclude_patterns = self.config.get("default_exclude_patterns", [])
        
    def analyze(self, path, options):
        """Main analysis method that coordinates all analysis types."""
        logging.debug(f"Analyzing {path} with options: {options}")
        
        # Create canonical artifact path for this analysis run
        artifact_dir = get_canonical_artifact_path("analysis", "file_analysis")
        logging.debug(f"Using artifact directory: {artifact_dir}")
        
        # Validate path exists
        if not os.path.exists(path):
            logging.error(f"Path does not exist: {path}")
            return {"error": f"Path does not exist: {path}"}
        
        # Add path to results
        self.results["path"] = str(path)
        self.results["time"] = datetime.now().isoformat()
        self.results["analyses"] = {}
        self.results["errors"] = []  # Track all errors encountered
        
        # Update include/exclude patterns if provided in options
        if options.get('include_patterns'):
            self.include_patterns = options.get('include_patterns')
        if options.get('exclude_patterns'):
            self.exclude_patterns = options.get('exclude_patterns')
        
        # Use PathGuard to enforce artifact discipline
        with PathGuard(artifact_dir):
            # Individual analysis components
            if options.get('metadata'):
                self._extract_metadata(path, artifact_dir)
                
            if options.get('duplicates'):
                self._find_duplicates(path, artifact_dir)
                
            if options.get('ocr'):
                self._perform_ocr(path, artifact_dir)
                
            if options.get('virus'):
                self._scan_malware(path, artifact_dir)
                
            if options.get('search'):
                self._search_content(path, options.get('search_text', ''), artifact_dir)
                
            if options.get('binary'):
                self._analyze_binary(path, artifact_dir)
                
            if options.get('vision') or options.get('model'):
                self._analyze_models(
                    path, 
                    options.get('model_type', 'vision'),
                    options.get('model_name', 'fastvlm'), 
                    options.get('model_mode', 'describe'),
                    artifact_dir
                )
            
            # Write summary of all analyses
            self._write_summary(artifact_dir)
            
        return self.results
    
    def _should_process_file(self, file_path):
        """Determine if a file should be processed based on include/exclude patterns."""
        file_path_str = str(file_path)
        
        # If we have include patterns, file must match at least one
        if self.include_patterns and not any(fnmatch.fnmatch(file_path_str, pattern) for pattern in self.include_patterns):
            return False
        
        # If file matches any exclude pattern, skip it
        if any(fnmatch.fnmatch(file_path_str, pattern) for pattern in self.exclude_patterns):
            return False
            
        return True
    
    def _extract_metadata(self, path, artifact_dir):
        """Extract metadata from files."""
        logging.info(f"Extracting metadata from {path}")
        
        # Get list of files to process if it's a directory
        files_to_process = []
        if os.path.isdir(path):
            # If we're processing a directory, collect files first with filtering
            logging.info("Collecting files to process...")
            
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._should_process_file(file_path):
                        files_to_process.append(file_path)
            
            logging.info(f"Found {len(files_to_process)} files to process")
                
            # Limit the number of files to process
            max_files = self.config.get("max_metadata_files", 50)
            if len(files_to_process) > max_files:
                logging.info(f"Limiting to {max_files} files")
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
                logging.info("No matching files found")
                self.results['metadata'] = {"status": "skipped"}
                return None
        else:
            # If it's a single file, just process it directly
            if not self._should_process_file(path):
                logging.info("File excluded by pattern")
                self.results['metadata'] = {"status": "skipped"}
                return None
                
            # Get exiftool options from config
            exiftool_options = self.config.get("tool_options", {}).get("exiftool", [])
            command = ["exiftool", "-json"]
            
            # Check if -json is already in the config options to avoid duplication
            filtered_options = [opt for opt in exiftool_options if opt != "-json"]
            command.extend(filtered_options)
            
            command.append(str(path))
        
        # Add debug information
        logging.info(f"Preparing to extract metadata with command: {' '.join(command)}")
        
        try:
            # Run the command in a subprocess
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            output = result.stdout
            
            if not output:
                logging.error("Command returned no output")
                self.results['metadata'] = {
                    "status": "error",
                    "message": "Command returned no output"
                }
                return None
                
            # Try to parse JSON output
            try:
                # ExifTool might return warnings before the JSON data
                # First try direct parsing
                try:
                    metadata = json.loads(output)
                except json.JSONDecodeError:
                    # If direct parsing fails, try to find and extract valid JSON
                    # Look for various possible JSON starts (array or object)
                    for start_char, end_char in [('{', '}'), ('[', ']')]:
                        json_start = output.find(start_char)
                        if json_start >= 0:
                            # Found potential JSON start, now find matching end
                            json_data = output[json_start:]
                            # Count opening/closing brackets to handle nested structures
                            depth = 0
                            end_pos = -1
                            in_string = False
                            escape_next = False
                            
                            for i, char in enumerate(json_data):
                                if in_string:
                                    if escape_next:
                                        escape_next = False
                                    elif char == '\\':
                                        escape_next = True
                                    elif char == '"':
                                        in_string = False
                                elif char == '"':
                                    in_string = True
                                elif char == start_char:
                                    depth += 1
                                elif char == end_char:
                                    depth -= 1
                                    if depth == 0:
                                        end_pos = i + 1
                                        break
                            
                            if end_pos > 0:
                                # Found valid JSON structure
                                json_data = json_data[:end_pos]
                                try:
                                    metadata = json.loads(json_data)
                                    break  # Successfully parsed JSON
                                except json.JSONDecodeError:
                                    continue  # Try next pattern
                    
                    # If all attempts failed, raise exception
                    if 'metadata' not in locals():
                        raise json.JSONDecodeError("No valid JSON structure found", output, 0)
            except json.JSONDecodeError as e:
                # If full parsing fails, try to get partial output
                logging.error(f"JSON decode error: {str(e)}")
                logging.debug(f"First 500 characters of output: {output[:500]}")
                
                # Write the raw output for debugging
                debug_file = os.path.join(artifact_dir, f"metadata_debug.txt")
                safe_write(debug_file, output)
                
                logging.info(f"Wrote raw output to {debug_file} for debugging")
                
                self.results['metadata'] = {
                    "status": "error",
                    "message": f"JSON decode error: {str(e)}",
                    "debug_file": str(debug_file)
                }
                return None
            
            # Save metadata to file
            output_file = os.path.join(artifact_dir, "metadata.json")
            safe_write(output_file, json.dumps(metadata, indent=2))
            
            logging.info(f"Metadata extraction complete ({len(metadata)} items)")
            logging.info(f"Metadata saved to {output_file}")
                
            self.results['metadata'] = {
                "status": "success",
                "file": str(output_file),
                "count": len(metadata)
            }
            return metadata
                
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing command: {' '.join(command)}")
            logging.error(f"Return code: {e.returncode}")
            logging.error(f"Error output: {e.stderr}")
            
            self.results['metadata'] = {
                "status": "error",
                "message": f"Command failed with code {e.returncode}: {e.stderr}"
            }
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            
            self.results['metadata'] = {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
            return None
        
    def _find_duplicates(self, path, artifact_dir):
        """Find duplicate files."""
        logging.info(f"Finding duplicates in {path}")
        
        if not os.path.isdir(path):
            logging.info("Duplicate finding only works on directories.")
            self.results['duplicates'] = {"status": "skipped", "message": "Not a directory"}
            return None
        
        results_file = os.path.join(artifact_dir, "duplicates.txt")
        command = ["rdfind", "-outputname", results_file, str(path)]
        
        try:
            # Run the command in a subprocess
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            output = result.stdout
            
            if os.path.exists(results_file):
                logging.info(f"Duplicate analysis saved to {results_file}")
                self.results['duplicates'] = {
                    "status": "success",
                    "file": str(results_file)
                }
                return results_file
            else:
                logging.error("Command did not create the expected output file")
                self.results['duplicates'] = {
                    "status": "error",
                    "message": "Command did not create the expected output file"
                }
                return None
                
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing command: {' '.join(command)}")
            logging.error(f"Return code: {e.returncode}")
            logging.error(f"Error output: {e.stderr}")
            
            self.results['duplicates'] = {
                "status": "error",
                "message": f"Command failed with code {e.returncode}: {e.stderr}"
            }
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            
            self.results['duplicates'] = {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
            return None
        
    def _perform_ocr(self, path, artifact_dir):
        """Perform OCR on images."""
        logging.info(f"Performing OCR on images in {path}")
        
        # Get list of image files
        image_files = []
        image_exts = self.config.get("file_extensions", {}).get("images", 
                                                             [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"])
        
        # Collect image files to process
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file_path)[1].lower()
                    if file_ext in image_exts and self._should_process_file(file_path):
                        image_files.append(file_path)
        elif os.path.splitext(path)[1].lower() in image_exts and self._should_process_file(path):
            image_files.append(path)
        else:
            logging.info("No images to process")
            self.results['ocr'] = {"status": "skipped", "message": "No images to process"}
            return None
        
        if not image_files:
            logging.info("No image files found")
            self.results['ocr'] = {"status": "skipped", "message": "No image files found"}
            return None
        
        # Limit the number of images to process
        max_images = self.config.get("max_ocr_images", 50)
        if len(image_files) > max_images:
            logging.info(f"Limiting OCR to {max_images} images")
            image_files = image_files[:max_images]
        
        # Create OCR output directory
        ocr_output_dir = os.path.join(artifact_dir, "ocr_results")
        os.makedirs(ocr_output_dir, exist_ok=True)
        
        # Set up thread pool for parallel processing
        max_workers = self.config.get("max_threads", os.cpu_count() or 4)
        logging.info(f"Using {max_workers} threads for OCR processing")
        
        # Function to process a single image with OCR
        def process_image_ocr(image_path):
            try:
                # Get the image filename for output
                image_filename = os.path.basename(image_path)
                base_name = os.path.splitext(image_filename)[0]
                output_file = os.path.join(ocr_output_dir, f"{base_name}_ocr.txt")
                
                # Run tesseract OCR on the image
                ocr_command = ["tesseract", str(image_path), os.path.splitext(output_file)[0]]
                
                # Add any tesseract options from config
                tesseract_options = self.config.get("tool_options", {}).get("tesseract", [])
                ocr_command.extend(tesseract_options)
                
                subprocess.run(ocr_command, check=True, capture_output=True, text=True)
                
                with open(output_file, 'r') as f:
                    text = f.read().strip()
                    
                return {
                    "image": str(image_path),
                    "text": text,
                    "output_file": output_file,
                    "status": "success"
                }
            except Exception as e:
                logging.error(f"Error processing image {image_path}: {str(e)}")
                return {
                    "image": str(image_path),
                    "error": str(e),
                    "status": "error"
                }
        
        # Process images in parallel
        results = []
        successful = 0
        failed = 0
        
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_image = {executor.submit(process_image_ocr, img): img for img in image_files}
            for future in future_to_image:
                try:
                    result = future.result()
                    results.append(result)
                    if result["status"] == "success":
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logging.error(f"Task exception: {str(e)}")
                    failed += 1
        
        # Save OCR results to a JSON file
        json_output_file = os.path.join(artifact_dir, "ocr_results.json")
        safe_write(json_output_file, json.dumps(results, indent=2))
        
        logging.info(f"OCR processing complete: {successful} successful, {failed} failed")
        self.results['ocr'] = {
            "status": "success",
            "file": str(json_output_file),
            "total": len(results),
            "successful": successful,
            "failed": failed
        }
        
        return results
        
    def _scan_malware(self, path, artifact_dir):
        """Scan for malware."""
        logging.info(f"Scanning for malware in {path}")
        
        # Create output file
        output_file = os.path.join(artifact_dir, "malware_scan.txt")
        
        # Build command with options from config
        clamscan_options = self.config.get("tool_options", {}).get("clamscan", ["-r"])
        command = ["clamscan"]
        command.extend(clamscan_options)
        command.append(str(path))
        
        try:
            # Run the command in a subprocess
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            output = result.stdout
            
            # Save the output to a file
            safe_write(output_file, output)
            
            # Parse the results to get summary information
            scan_summary = {}
            
            # Try to extract lines like "Infected files: 0" from the output
            summary_pattern = r'(Infected files|Scanned files|Data scanned|Time):\s+([\d.]+)\s*([A-Za-z]*)'  
            for match in re.finditer(summary_pattern, output):  
                key, value, unit = match.groups()  
                if unit:  # If there's a unit like MB or seconds
                    scan_summary[key] = f"{value} {unit}"
                else:  
                    scan_summary[key] = value
            
            # Record the results
            if "Infected files" in scan_summary and scan_summary["Infected files"] != "0":
                status = "threat_detected"
            else:
                status = "clean"
                
            self.results['virus'] = {
                "status": status,
                "file": str(output_file),
                "summary": scan_summary
            }
            
            logging.info(f"Malware scan complete. Status: {status}")
            return output_file
                
        except subprocess.CalledProcessError as e:
            # Note: ClamAV returns 1 if it finds infections
            if e.returncode == 1 and e.stdout:
                # This is actually a "success" case where threats were found
                output = e.stdout
                safe_write(output_file, output)
                
                # Try to parse summary information
                scan_summary = {}
                summary_pattern = r'(Infected files|Scanned files|Data scanned|Time):\s+([\d.]+)\s*([A-Za-z]*)'
                for match in re.finditer(summary_pattern, output):
                    key, value, unit = match.groups()
                    if unit:  # If there's a unit like MB or seconds
                        scan_summary[key] = f"{value} {unit}"
                    else:
                        scan_summary[key] = value
                
                self.results['virus'] = {
                    "status": "threat_detected",
                    "file": str(output_file),
                    "summary": scan_summary
                }
                
                logging.info("Malware scan complete. Threats detected.")
                return output_file
            else:
                # This is a genuine error
                logging.error(f"Error executing command: {' '.join(command)}")
                logging.error(f"Return code: {e.returncode}")
                logging.error(f"Error output: {e.stderr}")
                
                self.results['virus'] = {
                    "status": "error",
                    "message": f"Command failed with code {e.returncode}: {e.stderr}"
                }
                return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            
            self.results['virus'] = {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
            return None
        
    def _search_content(self, path, search_text, artifact_dir):
        """Search content for specific text."""
        logging.info(f"Searching for '{search_text}' in {path}")
        
        if not search_text:
            logging.warning("No search text provided")
            self.results['search'] = {"status": "skipped", "message": "No search text provided"}
            return None
        
        # Sanitize the search text for filename use
        safe_search_text = re.sub(r'[\\/*?:"<>|]', '_', search_text)
        output_file = os.path.join(artifact_dir, f"search_{safe_search_text}.txt")
        
        # Build ripgrep command with options from config
        ripgrep_options = self.config.get("tool_options", {}).get("ripgrep", ["-i", "-n", "--color", "never"])
        command = ["rg"]
        command.extend(ripgrep_options)
        
        # Add include/exclude patterns if present
        if self.include_patterns:
            for pattern in self.include_patterns:
                command.extend(["-g", pattern])
        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                command.extend(["-g", f"!{pattern}"])
        
        # Add search pattern and path
        command.append(search_text)
        command.append(str(path))
        
        try:
            # Run the command in a subprocess
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            output = result.stdout
            
            # Save the output to a file
            safe_write(output_file, output)
            
            # Count the number of matches
            match_count = len(output.strip().split('\n')) if output.strip() else 0
            
            self.results['search'] = {
                "status": "success",
                "file": str(output_file),
                "pattern": search_text,
                "matches": match_count
            }
            
            logging.info(f"Search complete. Found {match_count} matches.")
            return output_file
                
        except subprocess.CalledProcessError as e:
            # Note: ripgrep returns 1 when no matches found (not an error)
            if e.returncode == 1 and e.stderr == "":
                self.results['search'] = {
                    "status": "success",
                    "file": str(output_file),
                    "pattern": search_text,
                    "matches": 0
                }
                
                # Create an empty output file
                safe_write(output_file, "")
                
                logging.info("Search complete. No matches found.")
                return output_file
            else:
                # This is a genuine error
                logging.error(f"Error executing command: {' '.join(command)}")
                logging.error(f"Return code: {e.returncode}")
                logging.error(f"Error output: {e.stderr}")
                
                self.results['search'] = {
                    "status": "error",
                    "message": f"Command failed with code {e.returncode}: {e.stderr}"
                }
                return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            
            self.results['search'] = {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
            return None
        
    def _analyze_binary(self, path, artifact_dir):
        """Analyze binary files."""
        logging.info(f"Analyzing binary files in {path}")
        
        # Binwalk only works on files, not directories
        if os.path.isdir(path):
            logging.info("Binary analysis only works on individual files.")
            self.results['binary'] = {"status": "skipped", "message": "Not a file"}
            return None
        
        # Skip files that don't match include patterns or match exclude patterns
        if not self._should_process_file(path):
            logging.info("File excluded by pattern")
            self.results['binary'] = {"status": "skipped", "message": "File excluded by pattern"}
            return None
        
        # Create output file
        filename = os.path.basename(path)
        output_file = os.path.join(artifact_dir, f"binary_analysis_{filename}.txt")
        
        # Build binwalk command with options from config
        binwalk_options = self.config.get("tool_options", {}).get("binwalk", ["-B", "-e", "-M"])
        command = ["binwalk"]
        command.extend(binwalk_options)
        command.append(str(path))
        
        try:
            # Run the command in a subprocess
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            output = result.stdout
            
            # Save the output to a file
            safe_write(output_file, output)
            
            # Try to determine if interesting data was found
            interesting_data_found = False
            if "DECIMAL" in output and "HEXADECIMAL" in output:
                # This indicates binwalk found something
                interesting_data_found = True
            
            self.results['binary'] = {
                "status": "success",
                "file": str(output_file),
                "interesting_data": interesting_data_found
            }
            
            logging.info(f"Binary analysis complete. Data found: {interesting_data_found}")
            return output_file
                
        except subprocess.CalledProcessError as e:
            logging.error(f"Error executing command: {' '.join(command)}")
            logging.error(f"Return code: {e.returncode}")
            logging.error(f"Error output: {e.stderr}")
            
            self.results['binary'] = {
                "status": "error",
                "message": f"Command failed with code {e.returncode}: {e.stderr}"
            }
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            
            self.results['binary'] = {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
            return None
        
    def _analyze_models(self, path, model_type, model_name, model_mode, artifact_dir):
        """
        Analyze files with AI models using the ModelAnalyzer.
        
        Args:
            path: Path to file or directory to analyze
            model_type: Type of model to use (vision, text, etc.)
            model_name: Name of model to use (fastvlm, etc.)
            model_mode: Analysis mode (describe, detect, document, etc.)
            artifact_dir: Directory for output artifacts
        """
        logging.debug(f"Analyzing with {model_name} model in {model_mode} mode")
        
        # Determine if this is a single file or directory
        is_directory = os.path.isdir(path)
        
        # Output path within artifact directory
        output_path = None
        if is_directory:
            output_path = os.path.join(artifact_dir, f"{model_type}_{model_name}_{model_mode}")
            os.makedirs(output_path, exist_ok=True)
        else:
            file_base = os.path.splitext(os.path.basename(path))[0]
            output_path = os.path.join(artifact_dir, f"{file_base}_{model_name}_{model_mode}.json")
        
        # Get model size from config if available
        model_size = self.config.get('vision', {}).get('model_size', None)
        
        try:
            # Run analysis
            if is_directory:
                # Batch processing for directories
                batch_results = self.model_analyzer.batch_analyze(
                    path, 
                    model_type=model_type,
                    model_name=model_name,
                    model_size=model_size,
                    mode=model_mode,
                    output_dir=output_path
                )
                
                # Store summary in results
                summary = self.model_analyzer.get_summary()
                self.results[model_type] = {
                    'status': 'success',
                    'model': model_name,
                    'mode': model_mode,
                    'files_processed': len(batch_results),
                    'successful': summary['successful'],
                    'failed': summary['failed'],
                    'output_dir': output_path
                }
            else:
                # Single file processing
                result = self.model_analyzer.analyze_file(
                    path, 
                    model_type=model_type,
                    model_name=model_name,
                    model_size=model_size,
                    mode=model_mode,
                    output_path=output_path
                )
                
                # Store result in results
                self.results[model_type] = {
                    'status': 'success' if 'error' not in result else 'error',
                    'model': model_name,
                    'mode': model_mode,
                    'output_path': output_path,
                    'results': [{"json_result": result}] if 'error' not in result else None
                }
                
                # If there was an error in the result, capture it
                if 'error' in result:
                    self.results[model_type]['error'] = result['error']
                    
        except Exception as e:
            import traceback
            logger = logging.getLogger("src.core.analyzer")
            logger.exception("Model analysis failed")
            
            # Capture full error details including traceback
            error_details = {
                'status': 'error',
                'error': str(e),
                'error_type': type(e).__name__,
                'model': model_name,
                'mode': model_mode,
                'output_path': output_path if output_path and os.path.exists(output_path) else None,
                'traceback': traceback.format_exc()
            }
            
            # Store error details in results
            self.results[model_type] = error_details
            
            # Log diagnostic information
            logger.error(f"Model analysis error details: {error_details}")
        
    def _write_summary(self, artifact_dir):
        """Write a summary of all analyses with full error details."""
        summary_file = os.path.join(artifact_dir, "analysis_summary.json")
        
        # Ensure error information is preserved in the summary
        summary_data = self.results.copy()
        
        # Add timestamp and analysis metadata
        summary_data['_metadata'] = {
            'analysis_time': datetime.now().isoformat(),
            'artifact_dir': artifact_dir,
            'total_analyses': len([k for k in self.results.keys() if k != '_metadata'])
        }
        
        safe_write(summary_file, json.dumps(summary_data, indent=2))
        logging.debug(f"Summary written to {summary_file}")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="File Analysis System")
    
    # Required arguments
    parser.add_argument("path", nargs="?", help="Path to analyze (file or directory)", 
                      default=".")
    
    # Analysis options
    parser.add_argument("-a", "--all", action="store_true", help="Run all analyses")
    parser.add_argument("-m", "--metadata", action="store_true", help="Extract metadata")
    parser.add_argument("-d", "--duplicates", action="store_true", help="Find duplicates")
    parser.add_argument("-o", "--ocr", action="store_true", help="Perform OCR on images")
    parser.add_argument("-v", "--virus", action="store_true", help="Scan for malware")
    parser.add_argument("-s", "--search", metavar="TEXT", help="Search content")
    parser.add_argument("-b", "--binary", action="store_true", help="Analyze binary files")
    parser.add_argument("-V", "--vision", action="store_true", help="Analyze images with AI vision models")
    
    # Model analysis options
    parser.add_argument("--model", help="Specify model to use for analysis")
    parser.add_argument("--model-type", choices=["vision", "text"], default="vision", 
                      help="Type of model to use")
    parser.add_argument("--model-size", help="Size/variant of the model to use")
    
    # Output options
    parser.add_argument("-r", "--results", metavar="DIR", help="Output directory")
    
    # Verification option
    parser.add_argument("--verify", action="store_true", 
                      help="Verify installation and dependencies")
    
    # Vision options
    parser.add_argument("--vision-model", choices=["fastvlm", "bakllava", "qwen2vl"], 
                      default="fastvlm", help="Vision model to use")
    parser.add_argument("--vision-mode", choices=["describe", "detect", "document"], 
                      default="describe", help="Vision analysis mode")
    
    return parser.parse_args()

def verify_installation():
    """Verify the installation and dependencies."""
    print("Verifying file-analyzer installation...")
    
    # Create a dictionary to track verification results
    verification = {
        "system": {},
        "core_dependencies": {},
        "external_tools": {},
        "vision_models": {}
    }
    
    # System information
    import platform
    verification["system"]["os"] = platform.system()
    verification["system"]["version"] = platform.version()
    verification["system"]["python"] = platform.python_version()
    
    # Check core dependencies
    try:
        import PIL
        verification["core_dependencies"]["pillow"] = str(PIL.__version__)
    except ImportError:
        verification["core_dependencies"]["pillow"] = "Not installed"
    
    # Check external tools
    tools = ["exiftool", "tesseract", "clamscan", "rdfind", "rg", "binwalk"]
    for tool in tools:
        try:
            result = subprocess.run(["which", tool], capture_output=True, text=True)
            if result.returncode == 0:
                verification["external_tools"][tool] = "Installed: " + result.stdout.strip()
            else:
                verification["external_tools"][tool] = "Not found"
        except Exception:
            verification["external_tools"][tool] = "Error checking"
    
    # Check vision models
    try:
        # Import without initialization to avoid loading models
        from src.model_manager import create_manager
        manager = create_manager()
        for model_name in manager.adapters:
            verification["vision_models"][model_name] = "Available"
    except Exception as e:
        verification["vision_models"]["error"] = str(e)
    
    # Print verification results
    print("\nSystem Information:")
    for key, value in verification["system"].items():
        print(f"  {key}: {value}")
    
    print("\nCore Dependencies:")
    for key, value in verification["core_dependencies"].items():
        print(f"  {key}: {value}")
    
    print("\nExternal Tools:")
    for key, value in verification["external_tools"].items():
        print(f"  {key}: {value}")
    
    print("\nVision Models:")
    for key, value in verification["vision_models"].items():
        print(f"  {key}: {value}")
    
    print("\nVerification complete.")
    return verification

def main():
    """Entry point for the file analyzer."""
    args = parse_args()
    
    # Handle verification mode
    if args.verify:
        verify_installation()
        return 0
    
    # Create options dictionary from arguments
    options = {
        'metadata': args.metadata or args.all,
        'duplicates': args.duplicates or args.all,
        'ocr': args.ocr or args.all,
        'virus': args.virus or args.all,
        'search': args.search is not None or args.all,
        'search_text': args.search or '',
        'binary': args.binary or args.all,
        'vision': args.vision or args.all,
        'model': args.model is not None,
        'model_type': args.model_type,
        'model_name': args.model or args.vision_model,
        'model_mode': args.vision_mode,
        'results_dir': args.results
    }
    
    # Create configuration dictionary
    config = {
        'vision': {
            'model': args.vision_model,
            'model_size': args.model_size,
            'mode': args.vision_mode
        }
    }
    
    # Initialize and run the analyzer
    analyzer = FileAnalyzer(config)
    results = analyzer.analyze(args.path, options)
    
    # Return success
    return 0

if __name__ == "__main__":
    sys.exit(main())