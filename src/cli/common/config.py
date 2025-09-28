#!/usr/bin/env python3
"""
Centralized configuration for the File Analyzer CLI.

This module provides a unified configuration interface for the CLI,
now powered by the new Pydantic-based configuration system for
robust, type-safe configuration management.

MIGRATION NOTE: This module now uses src.config as its backend while
maintaining full backwards compatibility with existing CLI usage.
"""

import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

# Import the new configuration system
try:
    from src.config import settings, paths
    NEW_CONFIG_AVAILABLE = True
except ImportError:
    NEW_CONFIG_AVAILABLE = False
    logging.warning("New configuration system not available, using legacy fallback")

# Import model configuration (fallback for legacy compatibility)
try:
    from src.models.config import (
        DEFAULT_MODEL_SIZE,
        DEFAULT_MODEL_TYPE,
        download_model,
        get_model_info,
        get_model_path as legacy_get_model_path,
        list_available_models,
    )
except ImportError:
    # Fallback defaults if model config is not available
    DEFAULT_MODEL_SIZE = "1.5b"
    DEFAULT_MODEL_TYPE = "fastvlm"
    
    def download_model(*args, **kwargs):
        return False, "Model download not available"
    
    def get_model_info(*args, **kwargs):
        return {}
    
    def legacy_get_model_path(*args, **kwargs):
        return None
    
    def list_available_models():
        return {}


# Import artifact discipline if available (handled by new config system)
try:
    from src.core.artifact_guard import (
        PathGuard,
        get_canonical_artifact_path,
        safe_write,
        validate_artifact_path,
    )
    ARTIFACT_DISCIPLINE = True
except ImportError:
    ARTIFACT_DISCIPLINE = False
    logging.warning("Artifact discipline tools not available. Using fallback paths.")

# Configure logging
logger = logging.getLogger(__name__)

# Helper function to find the project root directory
def find_project_root(markers: tuple[str, ...] = ("pyproject.toml", ".git", "config.json", "setup.py", "setup.cfg", "README.md"),
                     fallback: bool = True) -> Path | None:
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
    settings from various sources, now powered by the new Pydantic-based
    configuration system for robust, type-safe configuration management.
    
    MIGRATION NOTE: This class now uses src.config as its backend while
    maintaining full backwards compatibility with existing CLI usage.
    """

    def __init__(self, config_file: str | None = None):
        """
        Initialize configuration using the new configuration system.
        
        Args:
            config_file: Legacy parameter for backwards compatibility
                         (the new system uses environment variables instead)
        """
        # Store legacy config file parameter for compatibility
        self.config_file = Path(config_file) if config_file else None
        
        if NEW_CONFIG_AVAILABLE:
            # Use the new configuration system as backend
            self._use_new_config_system()
        else:
            # Fallback to legacy configuration loading
            self._use_legacy_config_system()
    
    def _use_new_config_system(self):
        """
        Initialize using the new Pydantic-based configuration system.
        """
        logger.debug("Using new Pydantic-based configuration system")
        
        # The new system handles all configuration automatically
        # We just need to provide the legacy interface
        self.config = {}  # Legacy config dict (not used with new system)
        
        # Runtime information from new system
        self.runtime = {
            "project_root": str(settings.path.project_root),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "platform": platform.platform(),
            "artifact_discipline": True,  # Always available in new system
            "schemas_dir": str(settings.path.schemas_dir),
        }
        
        logger.info(f"Configuration initialized with project root: {self.runtime['project_root']}")
    
    def _use_legacy_config_system(self):
        """
        Fallback to legacy configuration system if new system not available.
        """
        logger.warning("Using legacy configuration system fallback")
        
        # Legacy config loading logic (preserved for compatibility)
        env_config_file = os.getenv('FA_CONFIG_FILE')
        
        # Priority: 1. Explicit config_file parameter, 2. FA_CONFIG_FILE env var, 3. Default config file
        if self.config_file:
            pass  # Already set
        elif env_config_file and Path(env_config_file).exists():
            logger.debug(f"Using config file from FA_CONFIG_FILE: {env_config_file}")
            self.config_file = Path(env_config_file)
        elif DEFAULT_CONFIG_FILE and Path(DEFAULT_CONFIG_FILE).exists():
            self.config_file = DEFAULT_CONFIG_FILE
        else:
            logger.warning("No valid configuration file found, using environment variables and defaults only")
            self.config_file = None
        
        # Load config with graceful fallback
        self.config = self._load_config()
        
        # Legacy schema directory detection
        schemas_dir = SCHEMA_DIR if SCHEMA_DIR and SCHEMA_DIR.exists() else None
        if not schemas_dir and PROJECT_ROOT:
            candidates = [
                PROJECT_ROOT / "schemas",
                PROJECT_ROOT / "src" / "schemas",
                Path.cwd() / "schemas"
            ]
            for candidate in candidates:
                if candidate.exists():
                    schemas_dir = candidate
                    break
        
        # Legacy runtime information
        self.runtime = {
            "project_root": str(PROJECT_ROOT) if PROJECT_ROOT else str(Path.cwd()),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "platform": platform.platform(),
            "artifact_discipline": ARTIFACT_DISCIPLINE,
            "schemas_dir": str(schemas_dir) if schemas_dir else "schemas",
        }

    def _load_config(self) -> dict[str, Any]:
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
            with open(self.config_file) as f:
                config = json.load(f)
            logger.debug(f"Loaded configuration from {self.config_file}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file {self.config_file}: {e}")
            logger.warning("Using default configuration instead")
            return {}
        except (OSError, PermissionError) as e:
            logger.error(f"Error accessing configuration file {self.config_file}: {e}")
            logger.warning("Using default configuration instead")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using the new configuration system.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if NEW_CONFIG_AVAILABLE:
            # Use the new configuration system
            return settings.get(key, default)
        else:
            # Legacy fallback
            env_key = f"FA_{key.upper()}"
            if env_key in os.environ:
                return os.environ[env_key]
            
            if key in self.config:
                return self.config[key]
            
            return default

    def get_model_path(self, model_type: str = DEFAULT_MODEL_TYPE,
                      model_size: str = DEFAULT_MODEL_SIZE) -> str | None:
        """
        Get path to model using the new configuration system.
        
        Args:
            model_type: Model type (e.g., "fastvlm")
            model_size: Model size (e.g., "0.5b", "1.5b", "7b")
            
        Returns:
            Path to model or None if not found
        """
        if NEW_CONFIG_AVAILABLE:
            # Use the new PathManager for model discovery
            model_path = paths.get_model_path(model_type, model_size)
            return str(model_path) if model_path else None
        else:
            # Legacy fallback
            return legacy_get_model_path(model_type, model_size)

    def list_available_models(self) -> dict[str, list[str]]:
        """
        List available models using the new configuration system.
        
        Returns:
            Dictionary mapping model types to available sizes
        """
        if NEW_CONFIG_AVAILABLE:
            # Use the new PathManager for model discovery
            return paths.list_models()
        else:
            # Legacy fallback
            return list_available_models()

    def get_model_info(self, model_type: str = DEFAULT_MODEL_TYPE,
                      model_size: str = DEFAULT_MODEL_SIZE) -> dict[str, Any]:
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
                      force: bool = False) -> tuple[bool, str]:
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

    def get_schema_path(self, schema_type: str, version: str = "v1.0") -> Path | None:
        """
        Get path to JSON schema file using the new configuration system.
        
        Args:
            schema_type: Schema type (e.g., "fastvlm", "analyzer", "validate")
            version: Schema version (e.g., "v1.0", "v1.1")
            
        Returns:
            Path to schema file or None if not found
        """
        if NEW_CONFIG_AVAILABLE:
            # Use the new PathManager for schema discovery
            return paths.get_schema_path(schema_type, version)
        else:
            # Legacy schema discovery logic
            schemas_dir_str = self.runtime.get("schemas_dir")
            if not schemas_dir_str:
                logger.warning("No schemas directory configured")
                return None
            
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
            
            # No schema file found
            logger.warning(f"No schema file found for {schema_type} version {version}")
            return None

    def get_artifact_path(self, artifact_type: str, context: str) -> str:
        """
        Get canonical artifact path using the new configuration system.
        
        Args:
            artifact_type: Artifact type (e.g., "analysis", "vision", "test")
            context: Context string for the artifact
            
        Returns:
            Canonical artifact path
        """
        if NEW_CONFIG_AVAILABLE:
            # Use the new PathManager for artifact path creation
            artifact_path = paths.get_artifact_path(artifact_type, context)
            return str(artifact_path)
        else:
            # Legacy artifact path creation
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
                # Ultimate fallback: temporary directory
                logger.error(f"Error creating artifact path: {e}")
                logger.warning("Using fallback temporary directory for artifacts")
                
                import tempfile
                temp_dir = tempfile.mkdtemp(prefix=f"file_analyzer_{artifact_type}_")
                return temp_dir
            except Exception as e:
                # Unexpected errors should be re-raised after logging
                logger.critical(f"Unexpected error creating artifact path: {e}")
                raise

# Create a global configuration instance
config = Config()

if __name__ == "__main__":
    # Simple test
    print(f"Project root: {config.runtime['project_root']}")
    print(f"Available models: {config.list_available_models()}")
    print(f"Tool options: {config.get('tool_options', {})}")
