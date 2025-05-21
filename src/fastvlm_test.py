#!/usr/bin/env python3
"""
FastVLM Test Script

This script demonstrates how to use FastVLM for image analysis with the file-analyzer project.
It uses the Apple ML-FastVLM model for efficient vision language processing on Apple Silicon.
"""

import os
import sys
import argparse
import json
from pathlib import Path
import time
from datetime import datetime

# Import error handler
try:
    from src.fastvlm_errors import FastVLMErrorHandler
    ERROR_HANDLER_AVAILABLE = True
except ImportError:
    # For backward compatibility, check various import paths
    try:
        from fastvlm_errors import FastVLMErrorHandler
        ERROR_HANDLER_AVAILABLE = True
    except ImportError:
        # Create a minimal error handler class if not available
        class FastVLMErrorHandler:
            @staticmethod
            def check_environment():
                return []
                
            @staticmethod
            def check_model_files(path):
                return {"status": "success"}
                
            @staticmethod
            def diagnose_error(error_text):
                return None
                
            @staticmethod
            def fix_common_issues():
                return []
                
        ERROR_HANDLER_AVAILABLE = True
        print("Warning: Created minimal FastVLM error handler")

# Determine if MLX and FastVLM are available
try:
    import mlx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("Warning: MLX framework not found. Please install with 'pip install mlx'")

# Ensure project root is in sys.path for module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Check if we've downloaded the ml-fastvlm repository
# First check in project root, then in tools directory for backward compatibility
ML_FASTVLM_PATH = Path(project_root) / "ml-fastvlm"
if ML_FASTVLM_PATH.exists():
    sys.path.append(str(ML_FASTVLM_PATH))
else:
    # Try tools directory as fallback
    ML_FASTVLM_PATH = Path(__file__).parent / "ml-fastvlm"
    if ML_FASTVLM_PATH.exists():
        sys.path.append(str(ML_FASTVLM_PATH))
    else:
        print(f"Warning: ml-fastvlm directory not found at {project_root}/ml-fastvlm or {Path(__file__).parent}/ml-fastvlm")
        ML_FASTVLM_PATH = None

# Import from our vision analyzer module
from src.vision import VisionAnalyzer

class FastVLMAnalyzer:
    """FastVLM image analyzer for Apple Silicon."""
    
    def __init__(self, model_path=None, checkpoint_dir=None):
        """Initialize the FastVLM analyzer.
        
        Args:
            model_path: Path to the FastVLM model
            checkpoint_dir: Directory containing FastVLM checkpoints
        """
        self.model_path = model_path
        self.checkpoint_dir = checkpoint_dir or (ML_FASTVLM_PATH / "checkpoints" if ML_FASTVLM_PATH else None)
        self.model_loaded = False
        self.vision_analyzer = None
        
        # Check environment before proceeding
        if ERROR_HANDLER_AVAILABLE:
            issues = FastVLMErrorHandler.check_environment()
            if issues:
                for issue in issues:
                    if issue['severity'] == 'error':
                        print(f"ERROR: {issue['message']}")
                        print(f"Solution: {issue['solution']}")
                    else:
                        print(f"WARNING: {issue['message']}")
                        print(f"Solution: {issue['solution']}")
        
        # Check if MLX is available
        if not MLX_AVAILABLE:
            print("MLX framework not available. FastVLM requires MLX for Apple Silicon optimization.")
            return
            
        # Set up vision analyzer with FastVLM configuration
        vision_config = {
            "model": "fastvlm",
            "model_path": self.model_path,
            "output_format": "json",
            "description_mode": "detailed"
        }
        
        self.vision_analyzer = VisionAnalyzer(vision_config)
        
    def check_model(self):
        """Check if FastVLM model is available."""
        if self.model_path and Path(self.model_path).exists():
            print(f"FastVLM model found at: {self.model_path}")
            # Verify model files if error handler is available
            if ERROR_HANDLER_AVAILABLE:
                check_result = FastVLMErrorHandler.check_model_files(self.model_path)
                if check_result['status'] != 'success':
                    print(f"WARNING: {check_result['message']}")
                    print(f"Solution: {check_result['solution']}")
            return True
            
        if self.checkpoint_dir and Path(self.checkpoint_dir).exists():
            # Look for appropriate model directories (extracted models)
            model_dirs = list(Path(self.checkpoint_dir).glob("llava-fastvithd_*"))
            if model_dirs:
                print(f"Found FastVLM model directories: {[m.name for m in model_dirs]}")
                # Prefer 1.5B model if available
                for model_dir in model_dirs:
                    if "1.5b_stage3" in str(model_dir):
                        self.model_path = str(model_dir)
                        print(f"Using 1.5B Stage 3 model: {self.model_path}")
                        return True
                # Otherwise use the first available model
                self.model_path = str(model_dirs[0])
                print(f"Using model: {self.model_path}")
                return True
                
        print("FastVLM model not found. Please download a model using get_models.sh")
        return False
        
    def analyze_image(self, image_path, prompt=None, mode="describe"):
        """Analyze an image using FastVLM.
        
        Args:
            image_path: Path to the image file
            prompt: Optional custom prompt
            mode: Analysis mode - describe, detect, or document
            
        Returns:
            Analysis result
        """
        if not self.vision_analyzer:
            print("Vision analyzer not initialized.")
            return None
            
        if not Path(image_path).exists():
            print(f"Image not found: {image_path}")
            return None
            
        # Time the analysis for performance metrics
        start_time = time.time()
        result = self.vision_analyzer.analyze_image(image_path, prompt, mode)
        end_time = time.time()
        
        analysis_time = end_time - start_time
        
        if result:
            # Add performance metrics
            metadata = {
                "analysis_time": analysis_time,
                "timestamp": datetime.now().isoformat(),
                "model": "FastVLM",
                "image_path": image_path,
                "mode": mode
            }
            
            # Format output based on type
            if isinstance(result, dict):
                result["metadata"] = metadata
            else:
                try:
                    # If it's JSON-formatted string
                    result_dict = json.loads(result)
                    result_dict["metadata"] = metadata
                    result = json.dumps(result_dict, indent=2)
                except json.JSONDecodeError:
                    # If it's plain text
                    result = f"[FastVLM Analysis]\nTime: {analysis_time:.2f} seconds\n\n{result}"
                    
        return result
        
    def direct_predict(self, image_path, prompt):
        """Use the direct predict.py script from ml-fastvlm if available."""
        if not ML_FASTVLM_PATH:
            print("ml-fastvlm repository not found.")
            return None
            
        if not self.check_model():
            return None
            
        predict_script = ML_FASTVLM_PATH / "predict.py"
        if not predict_script.exists():
            print(f"Predict script not found at {predict_script}")
            return None
            
        import subprocess
        
        # Check if the model path is a directory
        if Path(self.model_path).is_dir():
            model_path = self.model_path
        else:
            model_path = self.checkpoint_dir
        
        cmd = [
            sys.executable,
            str(predict_script),
            "--model-path", str(model_path),
            "--image-file", str(image_path),
            "--prompt", prompt or "Describe the image."
        ]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            
            return {
                "result": result.stdout,
                "metadata": {
                    "analysis_time": analysis_time,
                    "timestamp": datetime.now().isoformat(),
                    "model": "FastVLM",
                    "image_path": image_path,
                    "prompt": prompt
                }
            }
        except subprocess.SubprocessError as e:
            error_msg = f"Error running FastVLM predict.py: {e}"
            stderr_output = e.stderr if hasattr(e, 'stderr') else ""
            print(error_msg)
            if stderr_output:
                print(f"Error output: {stderr_output}")
                
            # Diagnose error if error handler is available
            if ERROR_HANDLER_AVAILABLE:
                diagnosis = FastVLMErrorHandler.diagnose_error(str(e) + stderr_output)
                if diagnosis:
                    print(f"Diagnosis: {diagnosis['message']}")
                    print(f"Suggested solution: {diagnosis['solution']}")
                    
                # Try to fix common issues
                print("Attempting to fix common issues...")
                fixes = FastVLMErrorHandler.fix_common_issues()
                if fixes:
                    for fix in fixes:
                        print(f"Applied fix: {fix}")
                else:
                    print("No automatic fixes available.")
            return None
        
    def batch_analyze(self, image_dir, output_dir, mode="describe"):
        """Batch analyze images with FastVLM."""
        if not self.vision_analyzer:
            print("Vision analyzer not initialized.")
            return None
            
        return self.vision_analyzer.batch_analyze(image_dir, output_dir, mode)

# Main function for standalone usage
def main():
    parser = argparse.ArgumentParser(description="FastVLM Image Analyzer")
    parser.add_argument("--image", help="Path to image file or directory")
    parser.add_argument("--model", help="Path to FastVLM model")
    parser.add_argument("--checkpoint-dir", help="Directory containing FastVLM checkpoints")
    parser.add_argument("--mode", choices=["describe", "detect", "document"], default="describe",
                        help="Analysis mode")
    parser.add_argument("--prompt", help="Custom prompt for image analysis")
    parser.add_argument("--output", help="Output file or directory")
    parser.add_argument("--batch", action="store_true", help="Process directory in batch mode")
    parser.add_argument("--direct", action="store_true", 
                       help="Use direct predict.py script from ml-fastvlm")
    
    args = parser.parse_args()
    
    # Check if input image is provided
    if not args.image:
        parser.print_help()
        sys.exit(1)
        
    # Initialize FastVLM analyzer
    analyzer = FastVLMAnalyzer(args.model, args.checkpoint_dir)
    
    if args.batch and os.path.isdir(args.image):
        # Batch process directory
        output_dir = args.output or f"fastvlm_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = analyzer.batch_analyze(args.image, output_dir, args.mode)
        
        if results:
            print(f"Batch processing complete. Results saved to {output_dir}")
        else:
            print("Batch processing failed.")
    else:
        # Process single image
        if args.direct:
            result = analyzer.direct_predict(args.image, args.prompt)
        else:
            result = analyzer.analyze_image(args.image, args.prompt, args.mode)
            
        if result:
            if args.output:
                with open(args.output, 'w') as f:
                    if isinstance(result, dict):
                        json.dump(result, f, indent=2)
                    else:
                        f.write(result)
                print(f"Analysis saved to {args.output}")
            else:
                if isinstance(result, dict):
                    print(json.dumps(result, indent=2))
                else:
                    print(result)
        else:
            print("Analysis failed.")

# Standalone execution
if __name__ == "__main__":
    main()