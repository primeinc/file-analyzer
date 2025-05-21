#!/usr/bin/env python3
"""
Model Manager - Centralized Model Management Interface

This module provides a unified interface for managing all model types
in the file analyzer system. It handles:
1. Model discovery and registration
2. Model loading and initialization
3. Model inference and result processing
4. Standard result formatting with validation

The system supports different model types (vision, text, etc.) and provides
a consistent interface regardless of underlying model implementation.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path
import importlib
from abc import ABC, abstractmethod

# Import artifact discipline components
from src.core.artifact_guard import (
    get_canonical_artifact_path,
    validate_artifact_path,
    PathGuard,
    safe_write
)

# Import JSON utilities
from src.utils.json_utils import JSONValidator, process_model_output, get_json_prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default model paths
DEFAULT_MODEL_DIR = os.path.expanduser("~/.local/share/file_analyzer/models")
MODEL_TYPES = ["vision", "text"]

class ModelInterface(ABC):
    """Abstract base class for all models in the system."""
    
    @abstractmethod
    def __init__(self, model_path: str, **kwargs):
        """Initialize the model with the specified path and parameters."""
        pass
    
    @abstractmethod
    def predict(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """Run prediction with the model and return standardized results."""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get model information including type, version, and capabilities."""
        pass
    
    @classmethod
    def supports_input_type(cls, input_type: str) -> bool:
        """Check if the model supports the given input type."""
        return False

class ModelManager:
    """Central manager for all models in the system."""
    
    def __init__(self):
        """Initialize the model manager."""
        self.models = {}
        self.adapters = {}
        self.model_configs = {}
        self._load_model_configs()
        self._register_adapters()
    
    def _load_model_configs(self):
        """Load model configurations from config files."""
        # Load from main config.json
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if "vision" in config:
                        self.model_configs["vision"] = config["vision"]
            except Exception as e:
                logger.error(f"Error loading config.json: {e}")
        
        # Load from model_config.py if it exists
        try:
            from src.models.config import MODEL_CONFIGS
            self.model_configs.update(MODEL_CONFIGS)
        except ImportError:
            logger.warning("model_config.py not found, using defaults")
    
    def _register_adapters(self):
        """Register available model adapters."""
        # Register vision adapters
        try:
            # Try importing FastVLM adapter
            from src.models.fastvlm.adapter import create_adapter, FastVLMAdapter
            self.adapters["fastvlm"] = FastVLMAdapter
            logger.info("Registered FastVLM adapter")
        except ImportError:
            logger.info("FastVLM adapter not available")
        
        # Add any additional adapters here
    
    def get_adapter(self, model_type: str, model_name: str) -> Optional[ModelInterface]:
        """
        Get an appropriate adapter for the specified model type and name.
        
        Args:
            model_type: Type of model (vision, text, etc.)
            model_name: Name/ID of the model (fastvlm, bakllava, etc.)
            
        Returns:
            ModelInterface or None if no adapter is available
        """
        if model_name in self.adapters:
            return self.adapters[model_name]
        
        # Try dynamic import
        try:
            module_name = f"src.{model_name.lower()}_adapter"
            adapter_module = importlib.import_module(module_name)
            if hasattr(adapter_module, "create_adapter"):
                # Cache the adapter for future use
                self.adapters[model_name] = adapter_module.create_adapter
                return adapter_module.create_adapter
        except ImportError:
            logger.warning(f"No adapter found for {model_name}")
        
        return None
    
    def create_model(self, model_type: str, model_name: str, model_size: Optional[str] = None, **kwargs) -> Optional[ModelInterface]:
        """
        Create a model instance with the appropriate adapter.
        
        Args:
            model_type: Type of model (vision, text, etc.)
            model_name: Name/ID of the model
            model_size: Size variant of the model (0.5b, 1.5b, 7b, etc.)
            **kwargs: Additional parameters to pass to the adapter
            
        Returns:
            ModelInterface instance or None if creation fails
        """
        # Get the appropriate adapter
        adapter_func = self.get_adapter(model_type, model_name)
        if not adapter_func:
            logger.error(f"No adapter available for {model_name} {model_type} model")
            return None
        
        try:
            # Create the model instance
            model = adapter_func(model_type=model_name, model_size=model_size, **kwargs)
            return model
        except Exception as e:
            logger.error(f"Error creating model {model_name}: {e}")
            return None
    
    def get_available_models(self, model_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get a dictionary of available models and their sizes.
        
        Args:
            model_type: Optional filter for model type
            
        Returns:
            Dictionary mapping model names to available sizes
        """
        available_models = {}
        
        # If specific model type is requested
        if model_type:
            if model_type == "vision":
                # Check for FastVLM
                if "fastvlm" in self.adapters:
                    available_models["fastvlm"] = ["0.5b", "1.5b", "7b"]
        else:
            # Return all available models
            if "fastvlm" in self.adapters:
                available_models["fastvlm"] = ["0.5b", "1.5b", "7b"]
        
        return available_models
    
    def analyze_file(self, file_path: str, model_type: str = "vision", 
                   model_name: str = "fastvlm", model_size: Optional[str] = None,
                   prompt: Optional[str] = None, mode: str = "describe", 
                   output_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Analyze a file with the specified model.
        
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
        # Validate input file exists
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        
        # Create model instance
        model = self.create_model(model_type, model_name, model_size, **kwargs)
        if not model:
            return {"error": f"Failed to create model {model_name}"}
        
        # Run prediction
        try:
            start_time = datetime.now()
            result = model.predict(file_path, prompt=prompt, mode=mode, **kwargs)
            end_time = datetime.now()
            
            # Add timing metadata if not present
            if isinstance(result, dict) and "metadata" in result:
                if "execution_time" not in result["metadata"]:
                    result["metadata"]["execution_time"] = (end_time - start_time).total_seconds()
            
            # Save results if output path is specified
            if output_path:
                self._save_result(result, output_path)
            
            return result
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "metadata": {
                    "model": f"{model_name}_{model_size or 'default'}",
                    "execution_time": (datetime.now() - start_time).total_seconds(),
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    def batch_analyze(self, input_dir: str, model_type: str = "vision", 
                     model_name: str = "fastvlm", model_size: Optional[str] = None,
                     prompt: Optional[str] = None, mode: str = "describe", 
                     output_dir: Optional[str] = None, max_files: int = 10,
                     file_extensions: Optional[List[str]] = None, **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple files in a directory.
        
        Args:
            input_dir: Directory containing files to analyze
            model_type: Type of model (vision, text, etc.)
            model_name: Name/ID of the model
            model_size: Size variant of the model
            prompt: Custom prompt for the model
            mode: Analysis mode (describe, detect, document, etc.)
            output_dir: Optional directory to save results
            max_files: Maximum number of files to process
            file_extensions: List of file extensions to process
            **kwargs: Additional parameters for the model
            
        Returns:
            Dictionary mapping file paths to analysis results
        """
        # Validate input directory exists
        if not os.path.isdir(input_dir):
            return {"error": f"Directory not found: {input_dir}"}
        
        # Get list of files to process
        files = self._get_files(input_dir, file_extensions, max_files)
        if not files:
            return {"error": f"No matching files found in {input_dir}"}
        
        # Create output directory if specified
        if output_dir:
            if not validate_artifact_path(output_dir):
                # Use canonical path instead
                output_dir = get_canonical_artifact_path(model_type, f"batch_{model_name}_{mode}")
                logger.info(f"Using canonical artifact path: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        
        # Create model instance
        model = self.create_model(model_type, model_name, model_size, **kwargs)
        if not model:
            return {"error": f"Failed to create model {model_name}"}
        
        # Process each file
        results = {}
        for file_path in files:
            logger.info(f"Analyzing {file_path}")
            
            # Generate output path for this file if needed
            file_output_path = None
            if output_dir:
                file_name = os.path.basename(file_path)
                file_base = os.path.splitext(file_name)[0]
                file_output_path = os.path.join(output_dir, f"{file_base}_{mode}.json")
            
            # Run analysis
            try:
                result = model.predict(file_path, prompt=prompt, mode=mode, **kwargs)
                results[file_path] = result
                
                # Save individual result if output directory is specified
                if file_output_path:
                    self._save_result(result, file_output_path)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
                results[file_path] = {
                    "error": f"Analysis failed: {str(e)}",
                    "metadata": {
                        "model": f"{model_name}_{model_size or 'default'}",
                        "timestamp": datetime.now().isoformat()
                    }
                }
        
        # Write batch summary if output directory is specified
        if output_dir:
            summary_path = os.path.join(output_dir, "batch_summary.json")
            batch_summary = {
                "processed_files": len(results),
                "successful": sum(1 for r in results.values() if "error" not in r),
                "failed": sum(1 for r in results.values() if "error" in r),
                "model": f"{model_name}_{model_size or 'default'}",
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            }
            self._save_result(batch_summary, summary_path)
        
        return results
    
    def _get_files(self, directory: str, extensions: Optional[List[str]] = None, 
                 max_files: int = 10) -> List[str]:
        """
        Get a list of files in a directory with the specified extensions.
        
        Args:
            directory: Directory to search
            extensions: List of file extensions to include
            max_files: Maximum number of files to return
            
        Returns:
            List of file paths
        """
        if not extensions:
            # Default extensions for vision models
            extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"]
        
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if any(filename.lower().endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, filename))
                    if len(files) >= max_files:
                        return files
        
        return files
    
    def _save_result(self, result: Dict[str, Any], output_path: str) -> None:
        """
        Save analysis result to a file.
        
        Args:
            result: Analysis result
            output_path: Path to save the result
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Use PathGuard for artifact discipline
        with PathGuard(os.path.dirname(output_path)):
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)


def create_manager() -> ModelManager:
    """Create and initialize a model manager instance."""
    return ModelManager()


# Example usage when run directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Manager")
    parser.add_argument("--file", help="File to analyze")
    parser.add_argument("--model", default="fastvlm", help="Model to use")
    parser.add_argument("--size", help="Model size")
    parser.add_argument("--mode", default="describe", choices=["describe", "detect", "document"], 
                       help="Analysis mode")
    parser.add_argument("--output", help="Output file or directory")
    
    args = parser.parse_args()
    
    manager = create_manager()
    
    if args.file:
        result = manager.analyze_file(
            args.file, 
            model_name=args.model, 
            model_size=args.size,
            mode=args.mode,
            output_path=args.output
        )
        
        print(json.dumps(result, indent=2))
    else:
        # Show available models
        models = manager.get_available_models()
        print("Available models:")
        for model_name, sizes in models.items():
            size_str = ", ".join(sizes)
            print(f"  - {model_name} ({size_str})")