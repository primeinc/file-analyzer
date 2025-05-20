#!/usr/bin/env python3
"""
Vision Model Analysis Module

Integrates with file_analyzer.py to provide vision model analysis capabilities:
- FastVLM: Apple's native vision model (fastest option)
- BakLLaVA: Mature VLM with good performance
- Qwen2-VL: Document analysis specialist

Supports image description, object detection, and document understanding.
"""

import os
import sys
import subprocess
import json
import base64
from pathlib import Path
import shutil
from datetime import datetime
import tempfile
import time

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
        "install_cmd": "pip install mlx Pillow && git clone https://github.com/apple/ml-fastvlm.git && cd ml-fastvlm && pip install -e .",
        "check_cmd": "python -c \"import mlx\"",
        "bin": "ml-fastvlm/predict.py",
        "model_options": {
            "default": "ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3",
            "small": "ml-fastvlm/checkpoints/llava-fastvithd_0.5b_stage3",
            "medium": "ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3",
            "large": "ml-fastvlm/checkpoints/llava-fastvithd_7b_stage3"
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
    "output_format": "text",         # text, json
    "model_path": None,              # Custom model path
    "mmproj_path": None,             # For BakLLaVA CLIP model
    "batch_processing": False
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
        if not PIL_AVAILABLE:
            # Skip preprocessing if PIL is not available
            return image_path
            
        try:
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
                
            # Open and resize image
            img = Image.open(image_path)
            
            # Skip processing if image is already optimal size
            orig_width, orig_height = img.size
            if orig_width == width and orig_height == height:
                return image_path
                
            # Preserve aspect ratio
            if orig_width > orig_height:
                new_width = width
                new_height = int(orig_height * (width / orig_width))
            else:
                new_height = height
                new_width = int(orig_width * (height / orig_height))
                
            # Resize image
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Create a new image with the target size and paste resized image
            new_img = Image.new("RGB", (width, height), (0, 0, 0))
            new_img.paste(resized_img, ((width - new_width) // 2, (height - new_height) // 2))
            
            # Save to a temporary file
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"fastvlm_temp_{os.path.basename(image_path)}")
            new_img.save(temp_path)
            
            return temp_path
        except Exception as e:
            print(f"Error preprocessing image: {e}")
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
            
            # Check if we should use the direct predict.py script from ml-fastvlm
            ml_fastvlm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml-fastvlm")
            predict_script = os.path.join(ml_fastvlm_dir, "predict.py")
            
            if os.path.exists(predict_script):
                # Try to use the direct predict.py script
                import subprocess
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
                    print(f"Error running FastVLM predict.py: {e}")
                    if hasattr(e, 'stderr'):
                        print(f"Error output: {e.stderr}")
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
                try:
                    # Try to format as JSON
                    import json
                    result_dict = json.loads(result)
                    result_dict['metadata'] = {
                        'analysis_time': analysis_time,
                        'model': 'FastVLM',
                        'mode': mode
                    }
                    result = json.dumps(result_dict, indent=2)
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, add metrics as text
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
        ml_fastvlm_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml-fastvlm")
        
        # Check if we can use the batch processing capability
        if os.path.exists(os.path.join(ml_fastvlm_dir, "batch_predict.py")):
            # FastVLM batch processing
            try:
                import sys
                import subprocess
                
                # Create a temporary file listing all images to process
                temp_list = os.path.join(tempfile.gettempdir(), "fastvlm_batch_list.txt")
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
                
                # Read results from output files
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
        for orig_path, proc_path in processed_images.items():
            print(f"Analyzing: {orig_path}")
            result = self.analyze_image(proc_path, mode=mode)
            if result:
                results[orig_path] = result
                
                # Save individual result
                base_name = os.path.basename(orig_path)
                output_file = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}_{mode}.txt")
                with open(output_file, 'w') as f:
                    f.write(result)
        
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
    
    def batch_analyze(self, image_dir, output_dir, mode="describe"):
        """
        Batch analyze all images in a directory.
        
        Args:
            image_dir: Directory containing images
            output_dir: Directory to save results
            mode: Analysis mode - describe, detect, or document
            
        Returns:
            Dict mapping image paths to analysis results
        """
        if not os.path.isdir(image_dir):
            print(f"Image directory not found: {image_dir}")
            return {}
            
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
                    output_file = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}_{mode}.txt")
                    with open(output_file, 'w') as f:
                        f.write(result)
                    
        return results
        
    def save_results(self, results, output_file):
        """Save analysis results to a file."""
        if not results:
            return None
            
        output_format = self.config.get("output_format", "text")
        output_file = Path(output_file)
        
        if output_format == "json":
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        else:
            with open(output_file, 'w') as f:
                for image_path, result in results.items():
                    f.write(f"=== {image_path} ===\n")
                    f.write(result)
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
    parser.add_argument("--output", help="Output file or directory")
    parser.add_argument("--batch", action="store_true", help="Process directory in batch mode")
    parser.add_argument("--prompt", help="Custom prompt for analysis")
    parser.add_argument("--model-path", help="Path to model weights")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    config = DEFAULT_VISION_CONFIG.copy()
    config["model"] = args.model
    config["batch_processing"] = args.batch
    config["output_format"] = args.format
    
    if args.model_path:
        config["model_path"] = args.model_path
    
    analyzer = VisionAnalyzer(config)
    
    if os.path.isdir(args.image) and args.batch:
        output_dir = args.output or f"vision_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = analyzer.batch_analyze(args.image, output_dir, args.mode)
        if results:
            print(f"Batch processing complete. Results saved to {output_dir}")
    else:
        result = analyzer.analyze_image(args.image, args.prompt, mode=args.mode)
        if result:
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(result)
                print(f"Analysis saved to {args.output}")
            else:
                # Try to pretty-print JSON if the result is JSON
                if args.format == "json":
                    try:
                        result_dict = json.loads(result) if isinstance(result, str) else result
                        print(json.dumps(result_dict, indent=2))
                    except (json.JSONDecodeError, TypeError):
                        print(result)
                else:
                    print(result)