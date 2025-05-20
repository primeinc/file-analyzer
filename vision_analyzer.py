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

# Vision model options
VISION_MODELS = {
    "fastvlm": {
        "name": "FastVLM",
        "description": "Apple's native vision model (fastest option)",
        "install_cmd": "pip install mlx mlx-fastvlm",
        "check_cmd": "python -c \"import mlx_fastvlm\"",
        "bin": "fastvlm",
        "model_options": {
            "default": "apple/fastvlm-1.5b-instruct"
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
            model_path = self.config.get("model_path") or self.model_info["model_options"]["default"]
            creativity = 0.7 if self.config.get("description_mode") == "creative" else 0.0
            
            if mode == "describe":
                cmd = ["fastvlm", "describe", "--model", model_path, "--image", image_path]
                if creativity > 0:
                    cmd.extend(["--creative", str(creativity)])
            elif mode == "detect":
                cmd = ["fastvlm", "detect", "--model", model_path, "--image", image_path, "--threshold", "0.6"]
            else:  # document mode
                cmd = ["fastvlm", "describe", "--model", model_path, "--image", image_path]
                
            result = self.run_command(cmd)
            
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
        
        # Process each image individually
        results = {}
        for image_file in image_files:
            print(f"Analyzing: {image_file}")
            result = self.analyze_image(image_file, mode=mode)
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
    
    parser = argparse.ArgumentParser(description="Vision Model Analysis")
    parser.add_argument("--image", required=True, help="Path to image file or directory")
    parser.add_argument("--model", default="fastvlm", choices=VISION_MODELS.keys(), help="Vision model to use")
    parser.add_argument("--mode", default="describe", choices=["describe", "detect", "document"], help="Analysis mode")
    parser.add_argument("--output", help="Output file or directory")
    parser.add_argument("--batch", action="store_true", help="Process directory in batch mode")
    
    args = parser.parse_args()
    
    config = DEFAULT_VISION_CONFIG.copy()
    config["model"] = args.model
    config["batch_processing"] = args.batch
    
    analyzer = VisionAnalyzer(config)
    
    if os.path.isdir(args.image) and args.batch:
        output_dir = args.output or f"vision_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = analyzer.batch_analyze(args.image, output_dir, args.mode)
        if results:
            print(f"Batch processing complete. Results saved to {output_dir}")
    else:
        result = analyzer.analyze_image(args.image, mode=args.mode)
        if result:
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(result)
                print(f"Analysis saved to {args.output}")
            else:
                print(result)