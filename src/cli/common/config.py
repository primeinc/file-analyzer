#!/usr/bin/env python3
"""
Centralized configuration for the File Analyzer CLI.

This module provides a unified configuration interface for the CLI,
leveraging the existing model_config.py for model management and extending
it with CLI-specific settings.
"""

import os
import sys
import json
import logging
import platform
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple

# Import model configuration
from src.model_config import (
    get_model_path,
    list_available_models,
    get_model_info,
    download_model,
    create_artifact_path_for_model_output,
    MODEL_CHECKPOINTS,
    DEFAULT_MODEL_TYPE,
    DEFAULT_MODEL_SIZE,
)

# Import artifact discipline if available
try:
    from src.artifact_guard import (
        get_canonical_artifact_path,
        validate_artifact_path,
        PathGuard,
        safe_write
    )
    ARTIFACT_DISCIPLINE = True
except ImportError:
    ARTIFACT_DISCIPLINE = False
    logging.warning("Artifact discipline tools not available. Using fallback paths.")

# Configure logging
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Default configuration file
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "config.json"

# Schema directory
SCHEMA_DIR = PROJECT_ROOT / "schemas"

class Config:
    """
    Centralized configuration for the File Analyzer CLI.
    
    This class provides a unified interface for accessing configuration
    settings from various sources (config files, environment variables,
    command-line arguments) in a prioritized manner.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to configuration file (defaults to config.json in project root)
        """
        self.config_file = Path(config_file) if config_file else DEFAULT_CONFIG_FILE
        self.config = self._load_config()
        
        # Add runtime information
        self.runtime = {
            "project_root": str(PROJECT_ROOT),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "platform": platform.platform(),
            "artifact_discipline": ARTIFACT_DISCIPLINE,
            "schemas_dir": str(SCHEMA_DIR),
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
        """
        if not self.config_file.exists():
            logger.warning(f"Configuration file {self.config_file} not found, using defaults")
            return {}
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.debug(f"Loaded configuration from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check environment variables first
        env_key = f"FA_{key.upper()}"
        if env_key in os.environ:
            return os.environ[env_key]
            
        # Check configuration file
        if key in self.config:
            return self.config[key]
            
        # Use default value
        return default
    
    def get_model_path(self, model_type: str = DEFAULT_MODEL_TYPE, 
                      model_size: str = DEFAULT_MODEL_SIZE) -> Optional[str]:
        """
        Get path to model (wrapper for model_config.py).
        
        Args:
            model_type: Model type (e.g., "fastvlm")
            model_size: Model size (e.g., "0.5b", "1.5b", "7b")
            
        Returns:
            Path to model or None if not found
        """
        return get_model_path(model_type, model_size)
    
    def list_available_models(self) -> Dict[str, List[str]]:
        """
        List available models (wrapper for model_config.py).
        
        Returns:
            Dictionary mapping model types to available sizes
        """
        return list_available_models()
    
    def get_model_info(self, model_type: str = DEFAULT_MODEL_TYPE, 
                      model_size: str = DEFAULT_MODEL_SIZE) -> Dict[str, Any]:
        """
        Get model information (wrapper for model_config.py).
        
        Args:
            model_type: Model type (e.g., "fastvlm")
            model_size: Model size (e.g., "0.5b", "1.5b", "7b")
            
        Returns:
            Dictionary with model information
        """
        return get_model_info(model_type, model_size)
    
    def download_model(self, model_type: str = DEFAULT_MODEL_TYPE, 
                      model_size: str = DEFAULT_MODEL_SIZE,
                      force: bool = False) -> Tuple[bool, str]:
        """
        Download model (wrapper for model_config.py).
        
        Args:
            model_type: Model type (e.g., "fastvlm")
            model_size: Model size (e.g., "0.5b", "1.5b", "7b")
            force: Force re-download even if model exists
            
        Returns:
            Tuple of (success, message)
        """
        return download_model(model_type, model_size, force)
    
    def get_schema_path(self, schema_type: str, version: str = "v1.0") -> Optional[Path]:
        """
        Get path to JSON schema file.
        
        Args:
            schema_type: Schema type (e.g., "fastvlm", "analyzer", "validate")
            version: Schema version (e.g., "v1.0", "v1.1")
            
        Returns:
            Path to schema file or None if not found
        """
        schema_path = SCHEMA_DIR / schema_type / version
        
        if not schema_path.exists():
            logger.warning(f"Schema directory {schema_path} not found")
            return None
            
        # Look for main schema file
        schema_file = schema_path / "schema.json"
        if schema_file.exists():
            return schema_file
            
        # Look for type-specific schema file
        schema_file = schema_path / f"{schema_type}.json"
        if schema_file.exists():
            return schema_file
            
        logger.warning(f"Schema file not found in {schema_path}")
        return None
    
    def get_artifact_path(self, artifact_type: str, context: str) -> str:
        """
        Get canonical artifact path.
        
        Args:
            artifact_type: Artifact type (e.g., "analysis", "vision", "test")
            context: Context string for the artifact
            
        Returns:
            Canonical artifact path
        """
        if not ARTIFACT_DISCIPLINE:
            # Fallback without artifact discipline
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(PROJECT_ROOT, "artifacts", artifact_type, 
                               f"{context}_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            return output_dir
            
        # Use artifact discipline
        return get_canonical_artifact_path(artifact_type, context)

# Create a global configuration instance
config = Config()

if __name__ == "__main__":
    # Simple test
    print(f"Project root: {config.runtime['project_root']}")
    print(f"Available models: {config.list_available_models()}")
    print(f"Tool options: {config.get('tool_options', {})}")