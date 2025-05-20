#!/usr/bin/env python3
"""
Error handling module for FastVLM integration.

This module provides error detection and recovery for common FastVLM issues.
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path

class FastVLMErrorHandler:
    """Handler for common FastVLM errors."""
    
    @staticmethod
    def check_environment():
        """Check if the environment is suitable for running FastVLM."""
        issues = []
        
        # Check if running on Apple Silicon
        if platform.system() != "Darwin" or "arm64" not in platform.machine().lower():
            issues.append({
                "severity": "warning",
                "message": "FastVLM is optimized for Apple Silicon (M-series) chips.",
                "solution": "Performance may be suboptimal on other architectures."
            })
            
        # Check MLX installation
        try:
            import mlx
            mlx_version = getattr(mlx, "__version__", "unknown")
            if not hasattr(mlx, "core") and not hasattr(mlx, "array"):
                issues.append({
                    "severity": "error",
                    "message": f"MLX installation is incomplete or corrupted (version {mlx_version}).",
                    "solution": "Reinstall MLX using: pip install -U mlx"
                })
        except ImportError:
            issues.append({
                "severity": "error",
                "message": "MLX framework not installed.",
                "solution": "Install MLX using: pip install mlx"
            })
            
        # Check disk space
        try:
            _, _, free = shutil.disk_usage(os.getcwd())
            free_gb = free / (1024**3)
            if free_gb < 5:
                issues.append({
                    "severity": "warning",
                    "message": f"Low disk space: {free_gb:.1f}GB available.",
                    "solution": "FastVLM model files require at least 5GB of free space."
                })
        except Exception:
            pass
            
        # Check memory
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            if available_gb < 8:
                issues.append({
                    "severity": "warning",
                    "message": f"Limited memory: {available_gb:.1f}GB available.",
                    "solution": "FastVLM works best with at least 8GB of available RAM."
                })
        except ImportError:
            pass
            
        return issues
    
    @staticmethod
    def diagnose_error(error_message):
        """Diagnose common errors from error messages."""
        error_patterns = {
            "No such file or directory": {
                "message": "File not found error",
                "solution": "Check if all model files are properly downloaded and extracted."
            },
            "ModuleNotFoundError": {
                "message": "Missing required Python module",
                "solution": "Install required dependencies with 'pip install mlx Pillow requests'."
            },
            "CUDA": {
                "message": "CUDA-related error (not relevant for Apple Silicon)",
                "solution": "FastVLM on Apple Silicon uses Metal, not CUDA. CUDA-related errors can be ignored."
            },
            "Metal": {
                "message": "Metal GPU acceleration error",
                "solution": "Check if Metal is available on your Mac. Try updating macOS."
            },
            "out of memory": {
                "message": "Out of memory error",
                "solution": "Try using a smaller model or reducing batch size/image resolution."
            },
            "ValueError: Expected image of type PIL.Image.Image": {
                "message": "Image format error",
                "solution": "Ensure the image is a valid format (JPG, PNG, etc.) that can be opened with PIL."
            }
        }
        
        if not error_message:
            return None
            
        for pattern, diagnosis in error_patterns.items():
            if pattern in error_message:
                return diagnosis
                
        return {
            "message": "Unknown error",
            "solution": "Check logs for details and make sure model files are correctly downloaded."
        }
    
    @staticmethod
    def fix_common_issues():
        """Attempt to fix common installation issues."""
        fixes_applied = []
        
        # Fix 1: Update MLX
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "mlx"], 
                          check=True, capture_output=True)
            fixes_applied.append("Updated MLX to latest version")
        except subprocess.SubprocessError:
            pass
            
        # Fix 2: Install Pillow
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "Pillow"], 
                          check=True, capture_output=True)
            fixes_applied.append("Installed/updated Pillow for image processing")
        except subprocess.SubprocessError:
            pass
            
        # Fix 3: Clear any temporary preprocessed images
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            for temp_file in Path(temp_dir).glob("fastvlm_temp_*"):
                temp_file.unlink()
            fixes_applied.append("Removed temporary preprocessed images")
        except Exception:
            pass
            
        return fixes_applied
        
    @staticmethod
    def check_model_files(model_dir):
        """Check if model files are properly installed."""
        if not model_dir or not os.path.exists(model_dir):
            return {
                "status": "error",
                "message": f"Model directory not found: {model_dir}",
                "solution": "Run get_models.sh to download model files."
            }
            
        required_files = ["config.json", "tokenizer.json", "model-00001-of-00001.safetensors"]
        missing_files = []
        
        for file in required_files:
            if not os.path.exists(os.path.join(model_dir, file)):
                missing_files.append(file)
                
        if missing_files:
            return {
                "status": "error",
                "message": f"Missing required model files: {', '.join(missing_files)}",
                "solution": "Model directory exists but is incomplete. Re-run get_models.sh."
            }
            
        return {
            "status": "success",
            "message": "Model files are correctly installed.",
            "files": [f for f in os.listdir(model_dir) if not f.startswith('.')]
        }

# Direct usage example
if __name__ == "__main__":
    print("FastVLM Error Diagnostics:")
    
    # Check environment
    print("\nEnvironment Check:")
    issues = FastVLMErrorHandler.check_environment()
    if issues:
        for issue in issues:
            print(f"  {issue['severity'].upper()}: {issue['message']}")
            print(f"  Solution: {issue['solution']}")
    else:
        print("  No issues detected in environment.")
        
    # Check model files
    print("\nModel Files Check:")
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                           "ml-fastvlm/checkpoints/llava-fastvithd_1.5b_stage3")
    check_result = FastVLMErrorHandler.check_model_files(model_dir)
    print(f"  Status: {check_result['status'].upper()}")
    print(f"  {check_result['message']}")
    
    # Fix common issues
    print("\nApplying Fixes:")
    fixes = FastVLMErrorHandler.fix_common_issues()
    if fixes:
        for fix in fixes:
            print(f"  ✓ {fix}")
    else:
        print("  No fixes applied.")