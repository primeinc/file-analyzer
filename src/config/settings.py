#!/usr/bin/env python3
"""
Pydantic Settings Classes

Following FastAPI best practices for configuration management using
pydantic-settings with automatic environment variable binding.

Environment Variable Conventions:
- FA_*: General application settings
- FA_MODEL_*: Model-specific settings
- FA_PATH_*: Path-related settings (though most are auto-computed)
- FA_DEBUG: Debug mode
- FA_LOG_LEVEL: Logging level

Examples:
    FA_DEBUG=true
    FA_MODEL_DEFAULT_SIZE=0.5b
    FA_MODEL_MAX_SIZE_GB=8
    FA_USER_DATA_DIR=/custom/path
"""

import logging
import os
from pathlib import Path
from typing import Any


try:
    from pydantic import Field
    from pydantic_settings import BaseSettings as BaseSettingsNew
    # Try new pydantic-settings first, fall back to pydantic v1
    BaseSettingsClass = BaseSettingsNew
    PYDANTIC_AVAILABLE = True
except ImportError:
    try:
        from pydantic import BaseSettings, Field
        BaseSettingsClass = BaseSettings
        PYDANTIC_AVAILABLE = True
    except ImportError:
        # Fallback if pydantic is not available
        BaseSettingsClass = object
        PYDANTIC_AVAILABLE = False
        logging.warning("Pydantic not available, using basic configuration fallback")

        # Mock Field for fallback
        def field(**kwargs):
            return kwargs.get('default')

        Field = field

from src.utils.path_utils import RUNTIME


logger = logging.getLogger(__name__)

def find_project_root(current_path: Path | None = None) -> Path:
    """
    Find project root by looking for marker files.

    Args:
        current_path: Starting path for search (defaults to this file's path)

    Returns:
        Path to project root
    """
    if current_path is None:
        current_path = Path(__file__).resolve()

    markers = ("pyproject.toml", ".git", "config.json", "README.md")

    for parent in [current_path, *list(current_path.parents)]:
        for marker in markers:
            if (parent / marker).exists():
                logger.debug(f"Found project root at {parent} (marker: {marker})")
                return parent

    # Fallback to current working directory
    logger.warning("No project root markers found, using current working directory")
    return Path.cwd()

def get_user_data_dir() -> Path:
    """Get platform-appropriate user data directory."""
    if RUNTIME["windows"]:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif RUNTIME["macos"]:
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux, WSL, etc.
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base / "file-analyzer"

def get_user_cache_dir() -> Path:
    """Get platform-appropriate user cache directory."""
    if RUNTIME["windows"]:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "file-analyzer" / "cache"
    elif RUNTIME["macos"]:
        return Path.home() / "Library" / "Caches" / "file-analyzer"
    else:  # Linux, WSL, etc.
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / "file-analyzer"

class PathSettings(BaseSettingsClass):
    """Path-related configuration with automatic environment variable binding."""

    # Project structure paths - computed automatically but overrideable
    project_root: Path = Field(default_factory=find_project_root)

    # User data paths - platform-specific but overrideable
    user_data_dir: Path = Field(default_factory=get_user_data_dir)
    user_cache_dir: Path = Field(default_factory=get_user_cache_dir)

    # Computed paths based on project_root
    src_dir: Path | None = None
    libs_dir: Path | None = None
    schemas_dir: Path | None = None
    artifacts_dir: Path | None = None
    tmp_dir: Path | None = None

    # Model paths - user models go in user data, project models in libs
    user_model_dir: Path | None = None
    project_model_dir: Path | None = None

    if PYDANTIC_AVAILABLE:
        class Config:
            env_prefix = "FA_PATH_"
            case_sensitive = False
            # Allow arbitrary types for Path objects
            arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._compute_derived_paths()

    def _compute_derived_paths(self):
        """Compute derived paths from base paths."""
        # Project structure paths
        if not self.src_dir:
            self.src_dir = self.project_root / "src"
        if not self.libs_dir:
            self.libs_dir = self.project_root / "libs"
        if not self.schemas_dir:
            self.schemas_dir = self.project_root / "schemas"
        if not self.artifacts_dir:
            self.artifacts_dir = self.project_root / "artifacts"
        if not self.tmp_dir:
            self.tmp_dir = self.project_root / "tmp"

        # Model paths
        if not self.user_model_dir:
            self.user_model_dir = self.user_data_dir / "models"
        if not self.project_model_dir:
            self.project_model_dir = self.libs_dir / "ml-fastvlm" / "checkpoints"

class ModelSettings(BaseSettingsClass):
    """Model-specific configuration."""

    default_type: str = "fastvlm"
    default_size: str = "1.5b"
    available_sizes: list[str] = Field(default=["0.5b", "1.5b", "7b"])
    download_timeout: int = 300
    max_size_gb: int = 16

    # Model checkpoints configuration
    checkpoints: dict[str, Any] = Field(default={
        "fastvlm": {
            "0.5b": {
                "path": "llava-fastvithd_0.5b_stage3",
                "description": "FastVLM 0.5B model (small)",
                "download_url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_0.5b_stage3.zip",
                "file_size_bytes": 1075577344,  # ~1.0 GB
                "version": "v1.0.2",
            },
            "1.5b": {
                "path": "llava-fastvithd_1.5b_stage3",
                "description": "FastVLM 1.5B model (medium)",
                "download_url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_1.5b_stage3.zip",
                "file_size_bytes": 2969567232,  # ~2.8 GB
                "version": "v1.0.2",
            },
            "7b": {
                "path": "llava-fastvithd_7b_stage3",
                "description": "FastVLM 7B model (large)",
                "download_url": "https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_7b_stage3.zip",
                "file_size_bytes": 13959213056,  # ~13.0 GB
                "version": "v1.0.2",
            }
        }
    })

    if PYDANTIC_AVAILABLE:
        class Config:
            env_prefix = "FA_MODEL_"
            case_sensitive = False

class AppSettings(BaseSettingsClass):
    """Application-wide configuration."""

    debug: bool = False
    log_level: str = "INFO"
    artifact_discipline: bool = True
    max_output_size_mb: int = 100

    # Tool options
    tool_options: dict[str, Any] = Field(default={})

    if PYDANTIC_AVAILABLE:
        class Config:
            env_prefix = "FA_"
            case_sensitive = False

class Settings:
    """
    Main settings container providing access to all configuration sections.

    This class combines all setting categories into a single interface and
    provides backwards compatibility with existing configuration access patterns.
    """

    def __init__(self):
        # Initialize all settings sections
        self.app = AppSettings()
        self.model = ModelSettings()
        self.path = PathSettings()

        # Set up logging based on configuration
        self._setup_logging()

        # Log configuration summary
        logger.info(f"Initialized configuration (project_root: {self.path.project_root})")
        if self.app.debug:
            logger.debug(f"Runtime environment: {RUNTIME}")

    def _setup_logging(self):
        """Configure logging based on settings."""
        level = getattr(logging, self.app.log_level.upper(), logging.INFO)

        # Configure root logger
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        if self.app.debug:
            # Enable debug logging for our modules
            for module in ['src.config', 'src.models', 'src.core', 'src.cli']:
                logging.getLogger(module).setLevel(logging.DEBUG)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with backwards compatibility.

        Args:
            key: Configuration key (supports dot notation like 'model.default_size')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Handle dot notation (e.g., 'model.default_size')
        parts = key.split('.')

        if len(parts) == 1:
            # Simple key - check app settings first for backwards compatibility
            return getattr(self.app, key, default)
        elif len(parts) == 2:
            section, setting = parts
            section_obj = getattr(self, section, None)
            if section_obj:
                return getattr(section_obj, setting, default)

        return default

# Create global settings instance
settings = Settings()
