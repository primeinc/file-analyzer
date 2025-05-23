#!/usr/bin/env python3
"""
Vision Model Analysis Module

Integrates with file_analyzer.py to provide vision model analysis capabilities:
- FastVLM: Apple's native vision model (fastest option)
- BakLLaVA: Mature VLM with good performance
- Qwen2-VL: Document analysis specialist

Supports image description, object detection, and document understanding
with robust JSON output capabilities:

- Structured JSON output with standard fields (description, tags, metadata)
- Automatic retry logic for handling invalid model responses
- Extraction of JSON from text when possible
- Performance metrics collection (response time, model info, etc.)
- Support for different analysis modes (describe, detect, document)

All vision analysis results are provided in a consistent JSON format
for easy integration with other systems.
"""

import os
import sys
import subprocess
import json
import base64
from pathlib import Path
import shutil
from datetime import datetime
import time
import re
import logging

# Fix Python module imports
# First add the project root to the path so we can use relative imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import artifact path management
from src.core.artifact_guard import get_canonical_artifact_path, PathGuard, validate_artifact_path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Try to import PIL for image preprocessing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Vision model options
VISION_MODELS = {
    "fastvlm": {
        "name": "FastVLM",
        "description": "Apple's native vision model (fastest option)",
        "install_cmd": "pip install mlx Pillow && git clone https://github.com/apple/ml-fastvlm.git libs/ml-fastvlm && cd libs/ml-fastvlm && pip install -e .",
        "check_cmd": "python -c \"import mlx\"",
        "bin": "libs/ml-fastvlm/predict.py",
        "model_options": {
            "default": "libs/ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3",
            "small": "libs/ml-fastvlm/checkpoints/llava-fastvithd_0.5b_stage3",
            "medium": "libs/ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3",
            "large": "libs/ml-fastvlm/checkpoints/llava-fastvithd_7b_stage3"
        },
        "resolution": {
            "default": "512x512",
            "text": "768x768",  # Better for document analysis
            "objects": "384x384" # Sufficient for object detection
        }
    },
    "bakllava": {
        "name": "BakLLaVA",
        "description": "Mature VLM with good performance",
        "install_cmd": "git clone https://github.com/Fuzzy-Search/realtime-bakllava && cd realtime-bakllava && make",
        "bin": "llama-cpp",
        "model_options": {
            "default": "BakLLaVA-1-Q4_K_M.gguf",
            "clip": "BakLLaVA-1-clip-model.gguf"
        }
    },
    "qwen2vl": {
        "name": "Qwen2-VL",
        "description": "Document analysis specialist",
        "install_cmd": "pip install mlx-vlm",
        "check_cmd": "python -c \"import mlx_vlm\"",
        "bin": "mlx_vlm",
        "model_options": {
            "default": "Qwen2-VL-7B-Instruct-4bit"
        }
    }
}

# Default configuration for vision analysis
DEFAULT_VISION_CONFIG = {
    "model": "fastvlm",
    "max_images": 10,
    "resolution": "512x512",
    "description_mode": "standard",  # standard, creative, detailed
    "output_format": "json",         # text, json (default to json for better integration)
    "model_path": None,              # Custom model path
    "mmproj_path": None,             # For BakLLaVA CLIP model
    "batch_processing": False,
    "max_retries": 3                 # Max retries for JSON validation
}

class VisionAnalyzer:
    """Class for analyzing images using vision language models."""
    
    def __init__(self, config=None):
        """Initialize the vision analyzer with the provided configuration."""
        self.config = config or DEFAULT_VISION_CONFIG.copy()
        self.model_name = self.config.get("model", "fastvlm")
        self.model_info = VISION_MODELS.get(self.model_name, VISION_MODELS["fastvlm"])
        
        # Set up image processing parameters
        resolution = self.config.get("resolution")
        if not resolution and "resolution" in self.model_info:
            resolution_options = self.model_info.get("resolution", {})
            resolution = resolution_options.get("default")
        
        self.resolution = resolution or "512x512"
        
        # Determine model size/variant
        self.model_size = self._determine_model_size()
        
    def _determine_model_size(self):
        """Determine the model size/variant based on model name and path.
        
        Returns:
            str: Model size/variant (e.g., "0.5B", "1.5B", "7B") or empty string if unknown
        """
        if self.model_name == "fastvlm":
            # Get model_path from config or default options
            model_path = str(self.config.get("model_path") or self.model_info["model_options"]["default"])
            
            # Determine size from path
            if "0.5b" in model_path.lower():
                return "0.5B"
            elif "1.5b" in model_path.lower():
                return "1.5B"
            elif "7b" in model_path.lower():
                return "7B"
        
        # Add logic for other models as needed
        return ""

    def get_model_display_name(self):
        """Get a display name for the model including size information if available.
        
        Returns:
            str: Model name with size information (e.g., "FastVLM 1.5B")
        """
        if self.model_size:
            return f"{self.model_info['name']} {self.model_size}"
        return self.model_info["name"]
            
    def check_dependencies(self):
        """Check if the required dependencies for the selected vision model are installed."""
        model_info = self.model_info
        
        # Check if the binary exists in PATH
        binary = model_info.get("bin")
        if not shutil.which(binary) and binary != "llama-cpp":
            # For non-llama-cpp models, try the check command if available
            check_cmd = model_info.get("check_cmd")
            if check_cmd:
                try:
                    subprocess.run(check_cmd, shell=True, check=True, 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    return True
                except subprocess.CalledProcessError:
                    return False
            return False
            
        return True
            
    def install_dependencies(self):
        """Install the required dependencies for the selected vision model."""
        install_cmd = self.model_info.get("install_cmd")
        if not install_cmd:
            print(f"No installation command available for {self.model_name}")
            return False
            
        try:
            print(f"Installing dependencies for {self.model_info['name']}...")
            subprocess.run(install_cmd, shell=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            return False

    def run_command(self, command, shell=False):
        """Run a command and return its output."""
        try:
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

    def preprocess_image(self, image_path, mode="describe"):
        """
        Preprocess an image for optimal performance with vision models.
        
        Args:
            image_path: Path to the image file
            mode: Analysis mode to determine optimal preprocessing
            
        Returns:
            Path to preprocessed image (or original if preprocessing not available)
        """
        # IMPORTANT: Always log preprocessing attempt - this is a critical requirement
        print(f"PREPROCESSING IMAGE: {image_path}")
        
        # Check if this image has already been preprocessed to avoid duplicate preprocessing
        # Images in our canonical temp directory with our prefix are already preprocessed
        canonical_tmp_dir = get_canonical_artifact_path("tmp", "preprocessed_images")
        if "fastvlm_temp_" in os.path.basename(image_path) and canonical_tmp_dir in image_path:
            print(f"Image already preprocessed, skipping duplicate preprocessing")
            return image_path
        
        if not PIL_AVAILABLE:
            # Skip preprocessing if PIL is not available
            print(f"⚠️ WARNING: PIL not available, skipping preprocessing. RAW IMAGE WILL BE USED!")
            return image_path
            
        try:
            # Get original image size for comparison
            orig_size = os.path.getsize(image_path)
            print(f"Original image size: {orig_size/1024:.1f}KB")
            
            # Get resolution based on mode
            resolution = self.resolution
            if "resolution" in self.model_info:
                resolution_options = self.model_info.get("resolution", {})
                if mode == "document" and "text" in resolution_options:
                    resolution = resolution_options.get("text")
                elif mode == "detect" and "objects" in resolution_options:
                    resolution = resolution_options.get("objects")
            
            # Parse resolution
            try:
                width, height = map(int, resolution.split("x"))
            except (ValueError, AttributeError):
                width, height = 512, 512
                
            print(f"Target resolution: {width}x{height}")
                
            # Open and resize image
            img = Image.open(image_path)
            
            # Log original dimensions
            orig_width, orig_height = img.size
            print(f"Original dimensions: {orig_width}x{orig_height}")
            
            # ALWAYS PROCESS THE IMAGE regardless of current size
            # Images should be normalized even if already at target resolution
            # This ensures consistent performance across different image sources
            print(f"ALWAYS PROCESSING: Image will be normalized to target resolution regardless of current size")
            
            # Preserve aspect ratio when scaling
            if orig_width > orig_height:
                new_width = width
                new_height = int(orig_height * (width / orig_width))
            else:
                new_height = height
                new_width = int(orig_width * (height / orig_height))
                
            print(f"New dimensions with preserved aspect ratio: {new_width}x{new_height}")
                
            # Resize image
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Create a new image with the target size and paste resized image
            new_img = Image.new("RGB", (width, height), (0, 0, 0))
            new_img.paste(resized_img, ((width - new_width) // 2, (height - new_height) // 2))
            
            # Save to a canonical artifact path instead of system temp directory
            temp_dir = get_canonical_artifact_path("tmp", "preprocessed_images")
            temp_path = os.path.join(temp_dir, f"fastvlm_temp_{os.path.basename(image_path)}")
            # Ensure the directory exists
            os.makedirs(temp_dir, exist_ok=True)
            new_img.save(temp_path)
            
            # Log size reduction
            new_size = os.path.getsize(temp_path)
            reduction = (1 - new_size/orig_size) * 100
            print(f"PREPROCESSED: {orig_size/1024:.1f}KB → {new_size/1024:.1f}KB ({reduction:.1f}% reduction)")
            
            return temp_path
        except Exception as e:
            print(f"⚠️ ERROR preprocessing image: {e}")
            print(f"⚠️ WARNING: Using original image without preprocessing!")
            return image_path
    
    def analyze_image(self, image_path, prompt=None, mode="describe"):
        """
        Analyze an image using the selected vision model.
        
        Args:
            image_path: Path to the image file
            prompt: Custom prompt to use for analysis (optional)
            mode: Analysis mode - describe, detect, or document
            
        Returns:
            Analysis result as string or dict
        """
        if not os.path.exists(image_path):
            print(f"Image not found: {image_path}")
            return None
            
        if not self.check_dependencies():
            print(f"Required dependencies for {self.model_info['name']} not found.")
            print(f"Run `{self.model_info['install_cmd']}` to install them.")
            return None
            
        # Preprocess image for optimal performance
        processed_image_path = self.preprocess_image(image_path, mode)
            
        model_name = self.model_name
        
        # Set default prompt based on mode if not provided
        if not prompt:
            if mode == "describe":
                prompt = "Describe this image in detail."
            elif mode == "detect":
                prompt = "List all objects visible in this image with their approximate locations."
            elif mode == "document":
                prompt = "Extract all text from this document and format it properly."
        
        result = None
        
        # FastVLM analysis
        if model_name == "fastvlm":
            import sys
            import time
            
            # Track performance metrics
            start_time = time.time()
            
            model_path = self.config.get("model_path") or self.model_info["model_options"]["default"]
            creativity = 0.7 if self.config.get("description_mode") == "creative" else 0.0
            output_format = self.config.get("output_format", "json")
            max_retries = self.config.get("max_retries", 3)
            
            # Check if we should use the JSON-specific implementation
            if output_format == "json":
                try:
                    # Import the improved JSON module from src directory
                    from src.models.fastvlm.json import run_fastvlm_json_analysis
                    
                    # Determine appropriate JSON prompt based on mode
                    if mode == "describe":
                        json_prompt = """Describe this image in a highly detailed, dense manner. 
                        Output your answer ONLY as a valid JSON object with two fields:
                        - 'description': a verbose, information-dense description.
                        - 'tags': a list of all applicable tags as an array of strings.
                        
                        Your entire response MUST be a valid, parseable JSON object."""
                    elif mode == "detect":
                        json_prompt = """Analyze the objects in this image.
                        Output your answer ONLY as a valid JSON object with these fields:
                        - 'objects': an array of objects detected, each with 'name' and 'location' properties
                        - 'description': a brief scene description
                        
                        Your entire response MUST be a valid, parseable JSON object."""
                    elif mode == "document":
                        json_prompt = """Extract all text content from this document image.
                        Output your answer ONLY as a valid JSON object with these fields:
                        - 'text': all the extracted text content, preserving layout where possible
                        - 'document_type': the type of document detected
                        
                        Your entire response MUST be a valid, parseable JSON object."""
                    
                    # Use the improved JSON-specific implementation
                    json_result = run_fastvlm_json_analysis(
                        processed_image_path, 
                        model_path, 
                        prompt=json_prompt,
                        max_retries=max_retries
                    )
                    
                    if json_result:
                        # Add mode to metadata
                        if "metadata" in json_result:
                            json_result["metadata"]["mode"] = mode
                        
                        # Return the result directly as a dictionary
                        return json_result
                        
                except (ImportError, Exception) as e:
                    logging.warning(f"Error using JSON-specific implementation: {e}. Falling back to standard method.")
            
            # Fallback to the original implementation
            # Check for the predict.py script in the project directory first
            ml_fastvlm_dir = os.path.join(project_root, "libs", "ml-fastvlm")
            predict_script = os.path.join(ml_fastvlm_dir, "predict.py")
            
            if os.path.exists(predict_script):
                # Try to use the direct predict.py script
                import subprocess
                print(f"Using FastVLM predict.py script at {predict_script}")
                cmd = [
                    sys.executable,
                    predict_script,
                    "--model-path", model_path,
                    "--image-file", processed_image_path,
                    "--prompt", prompt
                ]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    result = result.stdout
                except subprocess.SubprocessError as e:
                    logging.error(f"Error running FastVLM predict.py: {e}")
                    if hasattr(e, 'stderr'):
                        logging.error(f"Error output: {e.stderr}")
                    result = None
            else:
                # Fallback to command-line invocation
                if mode == "describe":
                    cmd = ["fastvlm", "describe", "--model", model_path, "--image", processed_image_path]
                    if creativity > 0:
                        cmd.extend(["--creative", str(creativity)])
                elif mode == "detect":
                    cmd = ["fastvlm", "detect", "--model", model_path, "--image", processed_image_path, "--threshold", "0.6"]
                else:  # document mode
                    cmd = ["fastvlm", "describe", "--model", model_path, "--image", processed_image_path]
                    
                result = self.run_command(cmd)
                
            # Add performance metrics if successful
            end_time = time.time()
            if result:
                analysis_time = end_time - start_time
                if output_format == "json":
                    try:
                        # Try to format as JSON
                        import json
                        result_dict = json.loads(result)
                        result_dict['metadata'] = {
                            'analysis_time': analysis_time,
                            'model': 'FastVLM',
                            'mode': mode
                        }
                        return result_dict  # Return as dictionary for better integration
                    except (json.JSONDecodeError, TypeError):
                        # Import the centralized JSON utilities for consistent handling
                        try:
                            from src.utils.json_utils import JSONValidator, process_model_output
                            
                            # Use the centralized method for JSON processing
                            metadata = {
                                'analysis_time': analysis_time,
                                'model': 'FastVLM',
                                'mode': mode
                            }
                            
                            # Process the output with consistent utilities
                            return process_model_output(result, mode=mode, metadata=metadata)
                            
                        except ImportError:
                            # Fallback if utilities not available (should not happen)
                            # Log the issue so it gets noticed
                            logging.error("Failed to import centralized JSON utilities!")
                            
                            # Return formatted response with error flag
                            return {
                                "text": result,
                                "metadata": {
                                    'analysis_time': analysis_time,
                                    'model': 'FastVLM',
                                    'mode': mode,
                                    'json_parsing_failed': True,
                                    'missing_json_utils': True
                                }
                            }
                else:
                    # Return text format with metrics
                    result = f"[FastVLM Analysis - {analysis_time:.2f}s]\n\n{result}"
            
        # BakLLaVA analysis
        elif model_name == "bakllava":
            model_path = self.config.get("model_path") or self.model_info["model_options"]["default"]
            mmproj_path = self.config.get("mmproj_path") or self.model_info["model_options"]["clip"]
            
            # Check if using Fuzzy-Search implementation
            if os.path.exists("./realtime-bakllava/server"):
                # Start server mode (background process)
                server_cmd = [
                    "./realtime-bakllava/server",
                    "-m", model_path,
                    "--mmproj", mmproj_path,
                    "-ngl", "1"
                ]
                # This would need a more complex implementation with server/client mode
                print("BakLLaVA server mode not yet implemented")
                return None
            else:
                # Using llama.cpp directly
                llama_path = shutil.which("llama-cpp") or "./llama.cpp/main"
                cmd = [
                    llama_path,
                    "-m", model_path,
                    "--mmproj", mmproj_path,
                    "-ngl", "1",
                    "--image", image_path,
                    "--prompt", prompt
                ]
                result = self.run_command(cmd)
                
        # Qwen2-VL analysis
        elif model_name == "qwen2vl":
            model_path = self.config.get("model_path") or self.model_info["model_options"]["default"]
            
            cmd = [
                "python", "-m", "mlx_vlm.cli",
                "--model", model_path,
                "--image", image_path,
                "--prompt", prompt
            ]
            result = self.run_command(cmd)
            
        # Handle result return type consistency
        if result and self.config.get("output_format") == "json":
            # If we want JSON but have a string, try to convert it
            if isinstance(result, str):
                try:
                    # Try to convert to dictionary
                    result_dict = json.loads(result)
                    return result_dict
                except json.JSONDecodeError:
                    # Return as structured data with text field
                    return {
                        "text": result,
                        "metadata": {
                            "model": self.model_name,
                            "mode": mode,
                            "json_parsing_failed": True
                        }
                    }
            # If already a dict, ensure it has metadata
            elif isinstance(result, dict) and "metadata" not in result:
                result["metadata"] = {
                    "model": self.model_name,
                    "mode": mode,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
        return result
            
    def _batch_process_fastvlm(self, processed_images, output_dir, mode):
        """
        Specialized batch processing method for FastVLM models.
        
        Args:
            processed_images: Dict mapping original paths to preprocessed image paths
            output_dir: Directory to save results
            mode: Analysis mode
            
        Returns:
            Dict mapping image paths to analysis results
        """
        results = {}
        ml_fastvlm_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "libs", "ml-fastvlm")
        
        # Validate output_dir is a canonical artifact path
        if not validate_artifact_path(output_dir):
            print(f"Warning: Output directory {output_dir} is not a canonical artifact path")
            print(f"Creating canonical artifact path for batch processing")
            output_dir = get_canonical_artifact_path("vision", f"batch_{self.model_name}_{mode}")
            print(f"Using canonical artifact path: {output_dir}")
        
        # Check if we can use the batch processing capability
        if os.path.exists(os.path.join(ml_fastvlm_dir, "batch_predict.py")):
            # FastVLM batch processing
            try:
                import sys
                import subprocess
                
                # Create a temporary file listing all images to process in a canonical artifact path
                temp_dir = get_canonical_artifact_path("tmp", "fastvlm_batch_list")
                temp_list = os.path.join(temp_dir, "image_list.txt")
                
                with open(temp_list, 'w') as f:
                    for orig_path, proc_path in processed_images.items():
                        f.write(f"{proc_path}\n")
                
                # Get model path
                model_path = self.config.get("model_path") or self.model_info["model_options"]["default"]
                
                # Run batch processing
                cmd = [
                    sys.executable,
                    os.path.join(ml_fastvlm_dir, "batch_predict.py"),
                    "--model-path", model_path,
                    "--image-list", temp_list,
                    "--output-dir", output_dir,
                    "--prompt", self._get_prompt_for_mode(mode)
                ]
                
                print(f"Running FastVLM batch processing...")
                subprocess.run(cmd, check=True)
                
                # Read results from output files within PathGuard context
                with PathGuard(output_dir):
                    for orig_path in processed_images.keys():
                        base_name = os.path.basename(orig_path)
                        result_file = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}_result.txt")
                        if os.path.exists(result_file):
                            with open(result_file, 'r') as f:
                                results[orig_path] = f.read()
                
                return results
            except Exception as e:
                print(f"Error in batch processing: {e}")
                # Fall back to individual processing
        
        # Individual processing as fallback
        with PathGuard(output_dir):
            for orig_path, proc_path in processed_images.items():
                print(f"Analyzing: {orig_path}")
                result = self.analyze_image(proc_path, mode=mode)
                if result:
                    results[orig_path] = result
                    
                    # Save individual result
                    base_name = os.path.basename(orig_path)
                    file_ext = ".json" if self.config.get("output_format") == "json" else ".txt"
                    output_file = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}_{mode}{file_ext}")
                    with open(output_file, 'w') as f:
                        if isinstance(result, dict):
                            # Handle dict result properly for JSON format
                            json.dump(result, f, indent=2)
                        else:
                            # Handle string result
                            f.write(str(result))
        
        return results
    
    def _get_prompt_for_mode(self, mode):
        """Get appropriate prompt based on analysis mode."""
        if mode == "describe":
            return "Describe this image in detail."
        elif mode == "detect":
            return "List all objects visible in this image with their approximate locations."
        elif mode == "document":
            return "Extract all text from this document and format it properly."
        return "Describe this image."
    
    def batch_analyze(self, image_dir, output_dir=None, mode="describe"):
        """
        Batch analyze all images in a directory.
        
        Args:
            image_dir: Directory containing images
            output_dir: Directory to save results (if None, uses canonical artifact path)
            mode: Analysis mode - describe, detect, or document
            
        Returns:
            Dict mapping image paths to analysis results
        """
        if not os.path.isdir(image_dir):
            print(f"Image directory not found: {image_dir}")
            return {}
            
        # Use canonical artifact path if output_dir is not specified
        if output_dir is None:
            # Create a canonical artifact directory
            output_dir = get_canonical_artifact_path("vision", f"{self.model_name}_{mode}")
            print(f"Using canonical artifact path: {output_dir}")
        else:
            # Validate the provided output directory
            if not validate_artifact_path(output_dir):
                print(f"Warning: Output directory {output_dir} is not a canonical artifact path")
                print(f"Consider using get_canonical_artifact_path() from src.core.artifact_guard")
            
            # Create output directory if it doesn't exist
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Find all image files
        image_exts = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"]
        image_files = []
        
        for root, _, files in os.walk(image_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_exts):
                    image_files.append(os.path.join(root, file))
        
        if not image_files:
            print(f"No image files found in {image_dir}")
            return None
            
        # Limit number of images if specified
        max_images = self.config.get("max_images", 10)
        if len(image_files) > max_images:
            print(f"Limiting to {max_images} images (out of {len(image_files)} found)")
            image_files = image_files[:max_images]
            
        # First preprocess all images in parallel
        from concurrent.futures import ThreadPoolExecutor
        max_workers = self.config.get("max_threads", os.cpu_count() or 4)
        
        # Define preprocessing function
        def preprocess_batch_image(img_path):
            return img_path, self.preprocess_image(img_path, mode)
            
        print(f"Preprocessing {len(image_files)} images using {max_workers} threads...")
        processed_images = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for orig_path, proc_path in executor.map(preprocess_batch_image, image_files):
                processed_images[orig_path] = proc_path
        
        # Use PathGuard to ensure all output file operations respect artifact discipline
        with PathGuard(output_dir):
            # FastVLM batch processing
            if self.model_name == "fastvlm" and self.config.get("batch_processing", False):
                model_path = self.config.get("model_path") or self.model_info["model_options"]["default"]
                cmd = [
                    "fastvlm", "batch",
                    "--model", model_path,
                    "--input_dir", image_dir,
                    "--output_dir", output_dir
                ]
                self.run_command(cmd)
                
                # Read the results from output files
                results = {}
                for image_file in image_files:
                    base_name = os.path.basename(image_file)
                    output_file = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}.txt")
                    if os.path.exists(output_file):
                        with open(output_file, 'r') as f:
                            results[image_file] = f.read()
                            
                return results
            
            # Process images with better performance for FastVLM
            results = {}
            
            # Check if we're using FastVLM for more efficient batch processing
            if self.model_name == "fastvlm" and hasattr(self, "_batch_process_fastvlm"):
                # Use specialized batch processing for FastVLM
                results = self._batch_process_fastvlm(processed_images, output_dir, mode)
            else:
                # Process each image individually
                for image_file, processed_image in processed_images.items():
                    print(f"Analyzing: {image_file}")
                    result = self.analyze_image(processed_image, mode=mode)
                    if result:
                        results[image_file] = result
                        
                        # Save individual result
                        base_name = os.path.basename(image_file)
                        file_ext = ".json" if self.config.get("output_format") == "json" else ".txt"
                        output_file = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}_{mode}{file_ext}")
                        
                        with open(output_file, 'w') as f:
                            if isinstance(result, dict):
                                # Handle dict result properly for JSON format
                                json.dump(result, f, indent=2)
                            else:
                                # Handle string result
                                f.write(str(result))
                        
            return results
        
    def save_results(self, results, output_file=None):
        """
        Save analysis results to a file.
        
        Args:
            results: Results dictionary to save
            output_file: Path to save results (if None, uses canonical artifact path)
            
        Returns:
            Path to the saved results file
        """
        if not results:
            return None
            
        output_format = self.config.get("output_format", "json")  # Default to JSON
        
        # Use canonical artifact path if output_file is not specified
        if output_file is None:
            # Create a canonical artifact directory
            artifact_dir = get_canonical_artifact_path("vision", f"{self.model_name}_results")
            
            # Determine appropriate file name based on format
            if output_format == "json":
                output_file = os.path.join(artifact_dir, "results.json")
            elif output_format == "markdown":
                output_file = os.path.join(artifact_dir, "results.md")
            else:
                output_file = os.path.join(artifact_dir, "results.txt")
                
            print(f"Using canonical artifact path: {output_file}")
        else:
            # Validate the provided output file
            if not validate_artifact_path(output_file):
                print(f"Warning: Output file {output_file} is not in a canonical artifact path")
                print(f"Consider using get_canonical_artifact_path() from src.core.artifact_guard")
            
            # Convert to Path object for easier extension handling
            output_file = Path(output_file)
            
            # Ensure the file extension matches the format
            if output_format == "json" and not str(output_file).endswith(".json"):
                output_file = output_file.with_suffix(".json")
            elif output_format == "markdown" and not str(output_file).endswith((".md", ".markdown")):
                output_file = output_file.with_suffix(".md")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(str(output_file)), exist_ok=True)
        
        # Use PathGuard to ensure all file operations respect artifact discipline
        with PathGuard(os.path.dirname(str(output_file))):
            if output_format == "json":
                # Ensure JSON serializable - handle any non-serializable objects
                def clean_for_json(obj):
                    if isinstance(obj, dict):
                        return {k: clean_for_json(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [clean_for_json(i) for i in obj]
                    elif isinstance(obj, (str, int, float, bool, type(None))):
                        return obj
                    else:
                        return str(obj)
                
                clean_results = clean_for_json(results)
                
                with open(output_file, 'w') as f:
                    json.dump(clean_results, f, indent=2)
                    
                # Validate the output file is valid JSON
                try:
                    with open(output_file, 'r') as f:
                        json.load(f)
                    logging.info(f"Successfully saved valid JSON to {output_file}")
                except json.JSONDecodeError as e:
                    logging.error(f"Error: Generated invalid JSON in {output_file}: {e}")
            
            elif output_format == "markdown":
                with open(output_file, 'w') as f:
                    f.write("# Vision Analysis Results\n\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Model: {self.model_info['name']}\n\n")
                    
                    for image_path, result in results.items():
                        f.write(f"## Image: {os.path.basename(image_path)}\n\n")
                        
                        # Add image path as link that can work locally
                        f.write(f"Path: [{image_path}]({image_path})\n\n")
                        
                        if isinstance(result, dict):
                            # Format nicely in markdown
                            if "description" in result:
                                f.write("### Description\n\n")
                                f.write(f"{result['description']}\n\n")
                            
                            if "tags" in result and isinstance(result["tags"], list):
                                f.write("### Tags\n\n")
                                for tag in result["tags"]:
                                    f.write(f"- {tag}\n")
                                f.write("\n")
                            
                            if "objects" in result and isinstance(result["objects"], list):
                                f.write("### Objects Detected\n\n")
                                for obj in result["objects"]:
                                    if isinstance(obj, dict) and "name" in obj:
                                        location = obj.get("location", "")
                                        f.write(f"- **{obj['name']}**: {location}\n")
                                    else:
                                        f.write(f"- {obj}\n")
                                f.write("\n")
                                
                            if "text" in result:
                                f.write("### Text Content\n\n")
                                f.write("```\n")
                                f.write(result["text"])
                                f.write("\n```\n\n")
                                
                            if "metadata" in result:
                                f.write("### Metadata\n\n")
                                f.write("```json\n")
                                f.write(json.dumps(result["metadata"], indent=2))
                                f.write("\n```\n\n")
                                
                        else:
                            # For plain text results
                            f.write("### Analysis\n\n")
                            f.write("```\n")
                            f.write(str(result))
                            f.write("\n```\n\n")
                        
                        f.write("---\n\n")
                    
                    # Add a summary section
                    f.write("## Summary\n\n")
                    f.write(f"- Total images analyzed: {len(results)}\n")
                    f.write(f"- Analysis mode: {self.config.get('vision_mode', 'describe')}\n")
                    
            else:  # text format (default fallback)
                with open(output_file, 'w') as f:
                    for image_path, result in results.items():
                        f.write(f"=== {image_path} ===\n")
                        if isinstance(result, dict):
                            # Handle dictionary result in text mode
                            if "text" in result:
                                f.write(result["text"])
                            else:
                                f.write(json.dumps(result, indent=2))
                        else:
                            f.write(str(result))
                        f.write("\n\n")
                    
        return str(output_file)
                
# Simple example usage if run directly
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Vision Model Analysis")
    parser.add_argument("--image", required=True, help="Path to image file or directory")
    parser.add_argument("--model", default="fastvlm", choices=VISION_MODELS.keys(), help="Vision model to use")
    parser.add_argument("--mode", default="describe", choices=["describe", "detect", "document"], help="Analysis mode")
    parser.add_argument("--output", help="Output file or directory (defaults to canonical artifact path)")
    parser.add_argument("--batch", action="store_true", help="Process directory in batch mode")
    parser.add_argument("--prompt", help="Custom prompt for analysis")
    parser.add_argument("--model-path", help="Path to model weights")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    config = DEFAULT_VISION_CONFIG.copy()
    config["model"] = args.model
    config["batch_processing"] = args.batch
    config["output_format"] = args.format
    
    if args.model_path:
        config["model_path"] = args.model_path
    
    analyzer = VisionAnalyzer(config)
    
    # Use canonical artifact paths by default
    if os.path.isdir(args.image) and args.batch:
        # For batch processing directories
        if args.output:
            # If explicit output directory is provided, use it
            if not validate_artifact_path(args.output):
                print(f"Warning: Output directory {args.output} is not a canonical artifact path")
                print(f"Consider using automatic canonical paths by omitting --output")
            output_dir = args.output
        else:
            # Create a canonical artifact directory for batch results
            output_dir = get_canonical_artifact_path("vision", f"batch_{args.model}_{args.mode}")
            print(f"Using canonical artifact path: {output_dir}")
            
        # Perform batch analysis
        results = analyzer.batch_analyze(args.image, output_dir, args.mode)
        if results:
            print(f"Batch processing complete. Results saved to {output_dir}")
    else:
        # For single image analysis
        result = analyzer.analyze_image(args.image, args.prompt, mode=args.mode)
        if result:
            if args.output:
                # If explicit output file is provided, validate and use it
                if not validate_artifact_path(args.output):
                    print(f"Warning: Output file {args.output} is not in a canonical artifact path")
                    print(f"Consider using automatic canonical paths by omitting --output")
                    
                # Use PathGuard to protect file operations
                with PathGuard(os.path.dirname(args.output)):
                    with open(args.output, 'w') as f:
                        if isinstance(result, dict):
                            # Handle dict result properly for JSON format
                            json.dump(result, f, indent=2)
                        else:
                            # Handle string result
                            f.write(str(result))
                print(f"Analysis saved to {args.output}")
            else:
                # Use canonical artifact path for the output
                artifact_dir = get_canonical_artifact_path("vision", f"single_{args.model}_{args.mode}")
                output_file = os.path.join(artifact_dir, "result")
                
                # Determine file extension based on format
                if args.format == "json":
                    output_file += ".json"
                elif args.format == "markdown":
                    output_file += ".md"
                else:
                    output_file += ".txt"
                
                # Save results using PathGuard
                with PathGuard(artifact_dir):
                    with open(output_file, 'w') as f:
                        if isinstance(result, dict) and args.format == "json":
                            # Handle dict result properly for JSON format
                            json.dump(result, f, indent=2)
                        else:
                            # Handle string result or other formats
                            f.write(str(result))
                
                print(f"Analysis saved to canonical path: {output_file}")
                
                # Also print to console for convenience
                if args.format == "json":
                    try:
                        if isinstance(result, dict):
                            print(json.dumps(result, indent=2))
                        else:
                            result_dict = json.loads(result) if isinstance(result, str) else {"text": str(result)}
                            print(json.dumps(result_dict, indent=2))
                    except (json.JSONDecodeError, TypeError):
                        print(result)
                else:
                    print(result)