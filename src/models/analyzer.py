#!/usr/bin/env python3
"""
Model Analyzer - Unified Interface for Model Analysis

This module provides a standardized interface for analyzing files with
various model types. It serves as the main entry point for model-based
analysis in the file analyzer system, with these capabilities:

1. Unified interface for all model types (vision, text, etc.)
2. Support for different analysis modes (describe, detect, document, etc.)
3. Batch processing capabilities for directory analysis
4. Consistent output format with standardized JSON structure
5. Integration with centralized model management
6. Artifact discipline for all output files
"""

import os
import sys
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Fix imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import artifact discipline components
from src.core.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard,
    safe_write
)

# Import model management
from src.models.manager import ModelManager, create_manager

# Import JSON utilities
from src.utils.json_utils import JSONValidator, process_model_output

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ModelAnalyzer:
    """
    Unified interface for analyzing files with various model types.
    
    This class provides a standardized way to analyze files using different
    types of models (vision, text, etc.) while maintaining consistent
    output formats and artifact discipline.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the model analyzer with optional configuration.
        
        Args:
            config: Optional configuration dictionary with potential keys:
                - model_manager: A custom model manager instance
        """
        self.config = config or {}
        
        # Use provided model manager or create a new one
        if "model_manager" in self.config:
            self.model_manager = self.config["model_manager"]
        else:
            self.model_manager = create_manager()
            
        self.results = {}
    
    def analyze_file(self, file_path: str, model_type: str = "vision", 
                   model_name: str = "fastvlm", model_size: Optional[str] = None,
                   prompt: Optional[str] = None, mode: str = "describe", 
                   output_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Analyze a single file with the specified model.
        
        Args:
            file_path: Path to the file to analyze
            model_type: Type of model (vision, text, etc.)
            model_name: Name/ID of the model
            model_size: Size variant of the model
            prompt: Custom prompt for the model
            mode: Analysis mode (describe, detect, document, etc.)
            output_path: Optional path to save the results
            **kwargs: Additional parameters for the model
            
        Returns:
            Dictionary with analysis results
        """
        logger.debug(f"Analyzing {file_path} with {model_name} ({model_size or 'default'}) in {mode} mode")
        
        # Use default output path if not specified
        if not output_path:
            artifact_dir = get_canonical_artifact_path(model_type, f"{model_name}_{mode}")
            file_name = os.path.basename(file_path)
            file_base = os.path.splitext(file_name)[0]
            output_path = os.path.join(artifact_dir, f"{file_base}_result.json")
            logger.debug(f"Using canonical artifact path: {output_path}")
        
        # Run analysis through model manager
        result = self.model_manager.analyze_file(
            file_path,
            model_type=model_type,
            model_name=model_name,
            model_size=model_size,
            prompt=prompt,
            mode=mode,
            output_path=output_path,
            **kwargs
        )
        
        # Store result in results dictionary
        self.results[file_path] = {
            "status": "success" if "error" not in result else "error",
            "model": f"{model_name}_{model_size or 'default'}",
            "mode": mode,
            "output_path": output_path,
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def batch_analyze(self, directory: str, model_type: str = "vision", 
                     model_name: str = "fastvlm", model_size: Optional[str] = None,
                     prompt: Optional[str] = None, mode: str = "describe", 
                     output_dir: Optional[str] = None, max_files: int = 10,
                     file_extensions: Optional[List[str]] = None, 
                     parallel: bool = True, **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple files in a directory.
        
        Args:
            directory: Directory containing files to analyze
            model_type: Type of model (vision, text, etc.)
            model_name: Name/ID of the model
            model_size: Size variant of the model
            prompt: Custom prompt for the model
            mode: Analysis mode (describe, detect, document, etc.)
            output_dir: Optional directory to save results
            max_files: Maximum number of files to process
            file_extensions: List of file extensions to process
            parallel: Whether to process files in parallel
            **kwargs: Additional parameters for the model
            
        Returns:
            Dictionary mapping file paths to analysis results
        """
        logger.debug(f"Batch analyzing {directory} with {model_name} ({model_size or 'default'}) in {mode} mode")
        
        # Use default output directory if not specified
        if not output_dir:
            output_dir = get_canonical_artifact_path(model_type, f"batch_{model_name}_{mode}")
            logger.debug(f"Using canonical artifact path: {output_dir}")
        
        # Use model manager to get files and create model instance
        if not file_extensions:
            # Default extensions based on model type
            if model_type == "vision":
                file_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"]
            else:
                file_extensions = [".txt", ".md", ".html", ".pdf"]
        
        # Process files either in parallel or sequentially
        if parallel:
            return self._parallel_batch_process(
                directory, 
                model_type, 
                model_name, 
                model_size, 
                prompt, 
                mode, 
                output_dir, 
                max_files, 
                file_extensions, 
                **kwargs
            )
        else:
            return self.model_manager.batch_analyze(
                directory,
                model_type=model_type,
                model_name=model_name,
                model_size=model_size,
                prompt=prompt,
                mode=mode,
                output_dir=output_dir,
                max_files=max_files,
                file_extensions=file_extensions,
                **kwargs
            )
    
    def _parallel_batch_process(self, directory: str, model_type: str, 
                              model_name: str, model_size: Optional[str],
                              prompt: Optional[str], mode: str, 
                              output_dir: str, max_files: int,
                              file_extensions: List[str], **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        Process files in parallel using ThreadPoolExecutor.
        
        Args:
            directory: Directory containing files to analyze
            model_type: Type of model (vision, text, etc.)
            model_name: Name/ID of the model
            model_size: Size variant of the model
            prompt: Custom prompt for the model
            mode: Analysis mode (describe, detect, document, etc.)
            output_dir: Directory to save results
            max_files: Maximum number of files to process
            file_extensions: List of file extensions to process
            **kwargs: Additional parameters for the model
            
        Returns:
            Dictionary mapping file paths to analysis results
        """
        # Get files to process
        all_files = self.model_manager._get_files(directory, file_extensions, max_files)
        
        # Create model instance
        model = self.model_manager.create_model(model_type, model_name, model_size, **kwargs)
        if not model:
            return {"error": f"Failed to create model {model_name}"}
        
        # Define processing function
        def process_file(file_path):
            file_name = os.path.basename(file_path)
            file_base = os.path.splitext(file_name)[0]
            file_output_path = os.path.join(output_dir, f"{file_base}_{mode}.json")
            
            try:
                result = model.predict(file_path, prompt=prompt, mode=mode, **kwargs)
                
                # Save result
                with PathGuard(os.path.dirname(file_output_path)):
                    with open(file_output_path, 'w') as f:
                        json.dump(result, f, indent=2)
                
                return file_path, result
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                error_result = {
                    "error": f"Analysis failed: {str(e)}",
                    "metadata": {
                        "model": f"{model_name}_{model_size or 'default'}",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                # Save error result
                with PathGuard(os.path.dirname(file_output_path)):
                    with open(file_output_path, 'w') as f:
                        json.dump(error_result, f, indent=2)
                
                return file_path, error_result
        
        # Process files in parallel
        results = {}
        max_workers = min(os.cpu_count() or 4, len(all_files))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for file_path, result in executor.map(process_file, all_files):
                results[file_path] = result
        
        # Write batch summary
        summary_path = os.path.join(output_dir, "batch_summary.json")
        batch_summary = {
            "processed_files": len(results),
            "successful": sum(1 for r in results.values() if "error" not in r),
            "failed": sum(1 for r in results.values() if "error" in r),
            "model": f"{model_name}_{model_size or 'default'}",
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }
        
        with PathGuard(os.path.dirname(summary_path)):
            with open(summary_path, 'w') as f:
                json.dump(batch_summary, f, indent=2)
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all analyses run during this session.
        
        Returns:
            Dictionary with analysis summary
        """
        return {
            "analyses": len(self.results),
            "successful": sum(1 for r in self.results.values() if r["status"] == "success"),
            "failed": sum(1 for r in self.results.values() if r["status"] == "error"),
            "models_used": list(set(r["model"] for r in self.results.values())),
            "timestamp": datetime.now().isoformat()
        }


# Main entry point if run as script
def main():
    """Main entry point for command-line execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Analyzer")
    parser.add_argument("path", help="File or directory to analyze")
    parser.add_argument("--model", default="fastvlm", help="Model to use")
    parser.add_argument("--size", help="Model size variant")
    parser.add_argument("--mode", default="describe", 
                       choices=["describe", "detect", "document"], 
                       help="Analysis mode")
    parser.add_argument("--batch", action="store_true", 
                       help="Process directory in batch mode")
    parser.add_argument("--output", help="Output file or directory")
    parser.add_argument("--max-files", type=int, default=10, 
                       help="Maximum files to process in batch mode")
    parser.add_argument("--prompt", help="Custom prompt for analysis")
    parser.add_argument("--parallel", action="store_true", default=True,
                       help="Process files in parallel (batch mode only)")
    parser.add_argument("--sequential", action="store_true",
                       help="Process files sequentially (batch mode only)")
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = ModelAnalyzer()
    
    if os.path.isdir(args.path) or args.batch:
        # Batch processing
        parallel = not args.sequential
        results = analyzer.batch_analyze(
            args.path,
            model_name=args.model,
            model_size=args.size,
            mode=args.mode,
            output_dir=args.output,
            max_files=args.max_files,
            prompt=args.prompt,
            parallel=parallel
        )
        
        # Print summary
        summary = analyzer.get_summary()
        print(f"Batch processing complete. Processed {summary['analyses']} files.")
        print(f"Successful: {summary['successful']}, Failed: {summary['failed']}")
        
        if args.output:
            print(f"Results saved to {args.output}")
    else:
        # Single file processing
        result = analyzer.analyze_file(
            args.path,
            model_name=args.model,
            model_size=args.size,
            mode=args.mode,
            output_path=args.output,
            prompt=args.prompt
        )
        
        # Print result (truncated if too large)
        result_json = json.dumps(result, indent=2)
        if len(result_json) > 1000:
            # Truncate large outputs for display
            print(result_json[:1000] + "...\n[Output truncated]")
        else:
            print(result_json)
        
        if args.output:
            print(f"Full result saved to {args.output}")


if __name__ == "__main__":
    main()