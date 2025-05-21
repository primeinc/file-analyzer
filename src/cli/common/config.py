#!/usr/bin/env python3
"""
Centralized configuration for the File Analyzer CLI.

This module provides a unified configuration interface for the CLI,
leveraging the existing model_config.py for model management and extending
it with CLI-specific settings.
"""

import os
import json
import logging
import platform
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple, Union

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

# Helper function to find the project root directory
def find_project_root(markers: Tuple[str, ...] = ("pyproject.toml", ".git", "config.json", "setup.py", "setup.cfg", "README.md"), 
                     fallback: bool = True) -> Optional[Path]:
    """
    Find the project root directory by looking for common marker files or directories.
    
    Args:
        markers: A tuple of files/directories that indicate the project root 
                (default: common project files like pyproject.toml, .git, etc.)
        fallback: Whether to use fallback paths if no markers are found
        
    Returns:
        Path to the project root directory, or None if no markers are found and fallback=False
    """
    current_path = Path(__file__).resolve()
    
    # Try to find any marker in parent directories
    for parent in current_path.parents:
        for marker in markers:
            if (parent / marker).exists():
                logger.debug(f"Found project root marker '{marker}' at {parent}")
                return parent
            
    # If no markers found and fallback is enabled
    if fallback:
        logger.warning(f"No project root markers {markers} found. Using fallback paths.")
        
        # First fallback: Use parent dir of src
        for parent in current_path.parents:
            if parent.name == "src" and parent.parent:
                logger.debug(f"Using 'src' parent directory as project root: {parent.parent}")
                return parent.parent
        
        # Second fallback: Use 3 levels up from current file (typical CLI structure)
        if len(current_path.parents) >= 3:
            logger.debug(f"Using 3 levels up as project root: {current_path.parents[2]}")
            return current_path.parents[2]
        
        # Last resort: Use current working directory
        logger.warning("Using current working directory as fallback project root")
        return Path.cwd()
    
    # Return None if no markers found and fallback disabled
    logger.warning(f"No project root markers {markers} found and fallback disabled")
    return None

# Project root directory with graceful fallback
PROJECT_ROOT = find_project_root() or Path.cwd()

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
    
    The Config class is designed to be resilient to missing config files
    or project root directories, allowing basic CLI functionality to work
    even without a properly configured environment.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to configuration file (defaults to config.json in project root,
                         or the value of FA_CONFIG_FILE environment variable if set)
                         Can be None if no config file is available
        """
        # Check for environment variable first
        env_config_file = os.getenv('FA_CONFIG_FILE')
        
        # Priority: 1. Explicit config_file parameter, 2. FA_CONFIG_FILE env var, 3. Default config file
        if config_file:
            self.config_file = Path(config_file)
        elif env_config_file and Path(env_config_file).exists():
            logger.debug(f"Using config file from FA_CONFIG_FILE: {env_config_file}")
            self.config_file = Path(env_config_file)
        # Handle case where DEFAULT_CONFIG_FILE might point to a missing file
        elif DEFAULT_CONFIG_FILE and Path(DEFAULT_CONFIG_FILE).exists():
            self.config_file = DEFAULT_CONFIG_FILE
        # Fallback to None if no valid config file
        else:
            logger.warning("No valid configuration file found, using environment variables and defaults only")
            self.config_file = None
            
        # Load config with graceful fallback to empty dict
        self.config = self._load_config()
        
        # Determine schemas_dir with fallback
        schemas_dir = SCHEMA_DIR if SCHEMA_DIR and SCHEMA_DIR.exists() else None
        if not schemas_dir and PROJECT_ROOT:
            # Try alternate schema locations if SCHEMA_DIR doesn't exist
            candidates = [
                PROJECT_ROOT / "schemas",
                PROJECT_ROOT / "src" / "schemas",
                Path.cwd() / "schemas"
            ]
            for candidate in candidates:
                if candidate.exists():
                    schemas_dir = candidate
                    break
                    
        # Add runtime information with safe defaults and fallbacks
        self.runtime = {
            "project_root": str(PROJECT_ROOT) if PROJECT_ROOT else str(Path.cwd()),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "platform": platform.platform(),
            "artifact_discipline": ARTIFACT_DISCIPLINE,
            "schemas_dir": str(schemas_dir) if schemas_dir else "schemas",
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary with empty dict as fallback
        """
        # Handle case where config_file is None
        if not self.config_file:
            logger.debug("No configuration file specified, using defaults")
            return {}
            
        # Handle case where config_file doesn't exist
        if not self.config_file.exists():
            logger.warning(f"Configuration file {self.config_file} not found, using defaults")
            return {}
            
        # Try to load and parse the config file
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.debug(f"Loaded configuration from {self.config_file}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file {self.config_file}: {e}")
            logger.warning("Using default configuration instead")
            return {}
        except (IOError, PermissionError) as e:
            logger.error(f"Error accessing configuration file {self.config_file}: {e}")
            logger.warning("Using default configuration instead")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
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
        # Try using schema directory from runtime settings
        schemas_dir_str = self.runtime.get("schemas_dir")
        if not schemas_dir_str:
            logger.warning("No schemas directory configured")
            return None
            
        # Convert string path to Path object
        try:
            schemas_dir = Path(schemas_dir_str)
        except Exception as e:
            logger.error(f"Invalid schemas directory path: {e}")
            return None
        
        # Check multiple possible schema locations
        schema_locations = [
            schemas_dir / schema_type / version,  # Standard: schemas/type/version/
            schemas_dir / version / schema_type,  # Alternative: schemas/version/type/
            schemas_dir / schema_type,            # Simplified: schemas/type/
            schemas_dir                           # Direct: schemas/
        ]
        
        # Try each location
        for schema_path in schema_locations:
            if not schema_path.exists():
                continue
                
            # Try different file naming patterns
            schema_files = [
                schema_path / "schema.json",                # Standard: schema.json
                schema_path / f"{schema_type}.json",        # Type-specific: type.json
                schema_path / f"{schema_type}_{version}.json", # Versioned: type_version.json
                schema_path / "schema" / "schema.json"      # Nested: schema/schema.json
            ]
            
            # Return first matching file
            for schema_file in schema_files:
                if schema_file.exists():
                    return schema_file
                    
        # No schema file found after trying all locations
        logger.warning(f"No schema file found for {schema_type} version {version}")
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
        try:
            # Try to use artifact discipline if available
            if ARTIFACT_DISCIPLINE:
                return get_canonical_artifact_path(artifact_type, context)
                
            # Fallback without artifact discipline
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Use PROJECT_ROOT if available, otherwise fall back to current directory
            base_dir = PROJECT_ROOT if PROJECT_ROOT else Path.cwd()
            
            # Create artifacts directory path
            output_dir = os.path.join(base_dir, "artifacts", artifact_type, 
                               f"{context}_{timestamp}")
            
            # Ensure directory exists
            os.makedirs(output_dir, exist_ok=True)
            return output_dir
            
        except (OSError, PermissionError, FileNotFoundError) as e:
            # Ultimate fallback: temporary directory - capture filesystem-related errors
            logger.error(f"Error creating artifact path: {e}")
            logger.warning("Using fallback temporary directory for artifacts")
        except Exception as e:
            # Unexpected errors should be re-raised after logging
            logger.critical(f"Unexpected error creating artifact path: {e}")
            raise
            
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix=f"file_analyzer_{artifact_type}_")
            return temp_dir

# Create a global configuration instance
config = Config()

if __name__ == "__main__":
    # Simple test
    print(f"Project root: {config.runtime['project_root']}")
    print(f"Available models: {config.list_available_models()}")
    print(f"Tool options: {config.get('tool_options', {})}")