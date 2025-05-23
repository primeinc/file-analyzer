#!/usr/bin/env python3
"""
FastVLM Error Handler

A utility module for diagnosing and fixing common FastVLM issues.
This module provides tools for:
1. Environment checking for FastVLM dependencies
2. Model file validation
3. Error diagnosis from error messages
4. Common issue fixes

This makes FastVLM more robust in production environments.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

# Availability flag for other modules to check
ERROR_HANDLER_AVAILABLE = True

class FastVLMErrorHandler:
    """Handles FastVLM errors and environment validation."""
    
    @staticmethod
    def check_environment():
        """Check the environment for FastVLM requirements.
        
        Returns:
            list: Issues found, with severity and solutions
        """
        issues = []
        
        # Check Apple Silicon for MLX
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            # Check MLX availability
            try:
                import mlx
                mlx_version = getattr(mlx, "__version__", "unknown")
            except ImportError:
                issues.append({
                    "severity": "error",
                    "message": "MLX framework not found. This is required for FastVLM on Apple Silicon.",
                    "solution": "Run pip install mlx to install the MLX framework."
                })
        else:
            issues.append({
                "severity": "warning",
                "message": "Not running on Apple Silicon. FastVLM with MLX is optimized for M-series chips.",
                "solution": "For optimal performance, run on MacOS with Apple Silicon."
            })
            
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            issues.append({
                "severity": "error",
                "message": f"Python version {python_version.major}.{python_version.minor} is not supported. FastVLM requires Python 3.8+",
                "solution": "Upgrade to Python 3.8 or later."
            })
        
        # Check PIL/Pillow availability
        try:
            from PIL import Image
        except ImportError:
            issues.append({
                "severity": "error",
                "message": "Pillow (PIL) is not installed. This is required for image preprocessing.",
                "solution": "Run pip install Pillow to install the Pillow library."
            })
            
        return issues
    
    @staticmethod
    def check_model_files(model_path):
        """Check FastVLM model files for completeness.
        
        Args:
            model_path: Path to model directory or file
            
        Returns:
            dict: Result with status and message
        """
        model_path = Path(model_path)
        
        # If it's a directory, check for required files
        if model_path.is_dir():
            required_files = ["config.json", "model.safetensors", "tokenizer_config.json", "vocab.json"]
            missing_files = [f for f in required_files if not (model_path / f).exists()]
            
            if missing_files:
                return {
                    "status": "error",
                    "message": f"Model directory is missing required files: {', '.join(missing_files)}",
                    "solution": "Download a complete model or check the model installation."
                }
        else:
            # If it's a file, check the file type
            if not model_path.exists():
                return {
                    "status": "error",
                    "message": f"Model file not found: {model_path}",
                    "solution": "Verify the path or download the model."
                }
            
            # Check file extension
            if model_path.suffix not in [".safetensors", ".bin", ".pt", ".gguf"]:
                return {
                    "status": "warning",
                    "message": f"Unexpected model file extension: {model_path.suffix}",
                    "solution": "Check that this is a valid model file."
                }
        
        return {"status": "success"}
        
    @staticmethod
    def diagnose_error(error_text):
        """Diagnose a FastVLM error from the error message.
        
        Args:
            error_text: Error message from FastVLM
            
        Returns:
            dict: Diagnosis with message and solution, or None if unknown
        """
        # Check for common error patterns
        if "CUDA out of memory" in error_text or "CUDA error" in error_text:
            return {
                "message": "GPU memory error. The model is too large for your GPU.",
                "solution": "Try using a smaller model or reduce batch size."
            }
        elif "No such file or directory" in error_text and "predict.py" in error_text:
            return {
                "message": "predict.py script not found.",
                "solution": "Make sure ml-fastvlm repository is properly cloned."
            }
        elif "No such file or directory" in error_text and ".safetensors" in error_text:
            return {
                "message": "Model file not found.",
                "solution": "Run libs/ml-fastvlm/get_models.sh to download models."
            }
        elif "ModuleNotFoundError" in error_text:
            # Extract the missing module
            import re
            match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", error_text)
            if match:
                module = match.group(1)
                return {
                    "message": f"Missing Python module: {module}",
                    "solution": f"Install the required module: pip install {module}"
                }
        
        # Unknown error
        return None
        
    @staticmethod
    def fix_common_issues():
        """Try to fix common FastVLM issues automatically.
        
        Returns:
            list: Applied fixes, or empty list if none applied
        """
        applied_fixes = []
        
        # Check if ml-fastvlm exists and download if not
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ml_fastvlm_dir = os.path.join(project_root, "ml-fastvlm")
        
        if not os.path.exists(ml_fastvlm_dir):
            try:
                subprocess.run(
                    ["git", "clone", "https://github.com/apple/ml-fastvlm.git", ml_fastvlm_dir],
                    check=True, capture_output=True
                )
                applied_fixes.append("Downloaded ml-fastvlm repository")
            except subprocess.SubprocessError:
                # Skip if git clone fails
                pass
        
        # Install MLX if not available
        try:
            import mlx
        except ImportError:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "mlx"],
                    check=True, capture_output=True
                )
                applied_fixes.append("Installed MLX framework")
            except subprocess.SubprocessError:
                # Skip if pip install fails
                pass
        
        # Install Pillow if not available
        try:
            from PIL import Image
        except ImportError:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "Pillow"],
                    check=True, capture_output=True
                )
                applied_fixes.append("Installed Pillow library")
            except subprocess.SubprocessError:
                # Skip if pip install fails
                pass
        
        return applied_fixes