#!/usr/bin/env python3
"""
Centralized Path Management

Provides unified path resolution and management for all File Analyzer operations,
leveraging the existing cross-platform path utilities and artifact discipline.

Key features:
- Centralized path resolution for models, artifacts, schemas, etc.
- Cross-platform compatibility using path_utils
- Integration with artifact discipline when available
- Safe path creation with proper sanitization
- Backwards compatibility with existing path patterns

Usage:
    from src.config import paths

    # Get model path
    model_path = paths.get_model_path("fastvlm", "1.5b")

    # Create artifact path
    output_dir = paths.get_artifact_path("analysis", "filename_generation")

    # Get schema path
    schema_path = paths.get_schema_path("analyzer", "v1.0")
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.path_utils import (
    ensure_dir_exists,
    get_safe_path,
    sanitize_filename_safe,
)


logger = logging.getLogger(__name__)

# Import artifact discipline if available
try:
    from src.core.artifact_guard import (
        get_canonical_artifact_path,
    )
    ARTIFACT_DISCIPLINE_AVAILABLE = True
except ImportError:
    ARTIFACT_DISCIPLINE_AVAILABLE = False
    logger.debug("Artifact discipline not available, using fallback paths")

class PathManager:
    """
    Centralized path management with cross-platform support.

    This class provides a unified interface for all path operations in the
    File Analyzer application, ensuring consistent path handling across
    different operating systems and maintaining backwards compatibility.
    """

    def __init__(self, path_settings):
        """
        Initialize PathManager with configuration settings.

        Args:
            path_settings: PathSettings instance from settings.py
        """
        self.settings = path_settings
        self._ensure_base_directories()

    def _ensure_base_directories(self):
        """Ensure all base directories exist."""
        base_dirs = [
            self.settings.user_data_dir,
            self.settings.user_cache_dir,
            self.settings.artifacts_dir,
            self.settings.tmp_dir,
            self.settings.user_model_dir,
        ]

        for directory in base_dirs:
            if directory:
                try:
                    ensure_dir_exists(directory)
                    logger.debug(f"Ensured directory exists: {directory}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not create directory {directory}: {e}")

    def get_model_path(self, model_type: str, model_size: str) -> Path | None:
        """
        Find the path to a model by type and size.

        Searches in priority order:
        1. User model directory
        2. Project model directory
        3. Alternative locations

        Args:
            model_type: Model type (e.g., "fastvlm")
            model_size: Model size (e.g., "0.5b", "1.5b", "7b")

        Returns:
            Path to model directory or None if not found
        """
        from .settings import settings

        # Get model configuration
        if model_type not in settings.model.checkpoints:
            logger.error(f"Unknown model type: {model_type}")
            return None

        if model_size not in settings.model.checkpoints[model_type]:
            logger.error(f"Unknown model size: {model_size} for {model_type}")
            return None

        # Get the model path suffix from configuration
        model_config = settings.model.checkpoints[model_type][model_size]
        model_path_suffix = model_config["path"]

        # Search locations in priority order
        search_paths = [
            self.settings.user_model_dir,
            self.settings.project_model_dir,
            self.settings.project_root / "checkpoints",  # Legacy location
        ]

        for base_path in search_paths:
            if not base_path or not base_path.exists():
                continue

            # Try with exact path from config
            full_path = base_path / model_path_suffix
            if full_path.exists():
                # Check for model files
                if self._validate_model_directory(full_path):
                    logger.debug(f"Found model at: {full_path}")
                    return full_path

                # Check for nested structure
                nested_path = full_path / model_path_suffix
                if nested_path.exists() and self._validate_model_directory(nested_path):
                    logger.debug(f"Found model at nested path: {nested_path}")
                    return nested_path

            # Try with model size as directory name
            alt_path = base_path / model_size
            if alt_path.exists() and self._validate_model_directory(alt_path):
                logger.debug(f"Found model at alternative path: {alt_path}")
                return alt_path

        logger.warning(f"Model {model_type} {model_size} not found in any search location")
        return None

    def _validate_model_directory(self, model_path: Path) -> bool:
        """
        Validate that a directory contains a valid model.

        Args:
            model_path: Path to potential model directory

        Returns:
            True if directory appears to contain a valid model
        """
        if not model_path.is_dir():
            return False

        # Look for common model files
        model_files = [
            "model.safetensors",
            "config.json",
            "tokenizer_config.json",
            # MLX format files
            "model.mlx",
            "config.yml",
        ]

        for model_file in model_files:
            if (model_path / model_file).exists():
                return True

        # If no specific model files, check if directory has any files
        # (might be a partially downloaded model)
        try:
            files = list(model_path.iterdir())
            return len(files) > 0
        except (OSError, PermissionError):
            return False

    def get_artifact_path(self, artifact_type: str, context: str) -> Path:
        """
        Get canonical path for artifacts with discipline support.

        Args:
            artifact_type: Type of artifact (e.g., "analysis", "vision", "test")
            context: Context string for the artifact

        Returns:
            Path to artifact directory
        """
        try:
            # Use artifact discipline if available
            if ARTIFACT_DISCIPLINE_AVAILABLE and self.settings.project_root:
                try:
                    path = get_canonical_artifact_path(artifact_type, context)
                    logger.debug(f"Using artifact discipline path: {path}")
                    return Path(path)
                except Exception as e:
                    logger.warning(f"Artifact discipline failed: {e}, using fallback")

            # Fallback: create timestamped path in artifacts directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_context = sanitize_filename_safe(context)
            safe_artifact_type = sanitize_filename_safe(artifact_type)

            # Use artifacts directory from settings
            artifacts_base = self.settings.artifacts_dir
            if not artifacts_base:
                artifacts_base = self.settings.project_root / "artifacts"

            # Create artifact path
            artifact_name = f"{safe_context}_{timestamp}"
            artifact_path = get_safe_path(artifacts_base, safe_artifact_type, artifact_name)

            logger.debug(f"Created artifact path: {artifact_path}")
            return artifact_path

        except (OSError, PermissionError) as e:
            # Ultimate fallback: temporary directory
            logger.error(f"Could not create artifact path: {e}")
            import tempfile
            temp_dir = Path(tempfile.mkdtemp(prefix=f"fa_{artifact_type}_"))
            logger.warning(f"Using temporary directory: {temp_dir}")
            return temp_dir

    def get_schema_path(self, schema_type: str, version: str = "v1.0") -> Path | None:
        """
        Get path to JSON schema file.

        Args:
            schema_type: Schema type (e.g., "analyzer", "fastvlm", "validate")
            version: Schema version (default: "v1.0")

        Returns:
            Path to schema file or None if not found
        """
        if not self.settings.schemas_dir or not self.settings.schemas_dir.exists():
            logger.warning("Schemas directory not found")
            return None

        # Try different schema organization patterns
        search_patterns = [
            # Standard: schemas/type/version/schema.json
            self.settings.schemas_dir / schema_type / version / "schema.json",

            # Alternative: schemas/version/type/schema.json
            self.settings.schemas_dir / version / schema_type / "schema.json",

            # Type-specific: schemas/type/type.json
            self.settings.schemas_dir / schema_type / f"{schema_type}.json",

            # Direct: schemas/type_version.json
            self.settings.schemas_dir / f"{schema_type}_{version}.json",

            # Simple: schemas/schema.json (for single schema projects)
            self.settings.schemas_dir / "schema.json",
        ]

        for schema_path in search_patterns:
            if schema_path.exists() and schema_path.is_file():
                logger.debug(f"Found schema: {schema_path}")
                return schema_path

        logger.warning(f"Schema {schema_type} v{version} not found")
        return None

    def get_user_data_path(self, *parts: str) -> Path:
        """
        Get safe path within user data directory.

        Args:
            *parts: Path components to join

        Returns:
            Safe path under user data directory
        """
        return get_safe_path(self.settings.user_data_dir, *parts)

    def get_cache_path(self, *parts: str) -> Path:
        """
        Get safe path within cache directory.

        Args:
            *parts: Path components to join

        Returns:
            Safe path under cache directory
        """
        return get_safe_path(self.settings.user_cache_dir, *parts)

    def get_tmp_path(self, *parts: str) -> Path:
        """
        Get safe path within temporary directory.

        Args:
            *parts: Path components to join

        Returns:
            Safe path under temporary directory
        """
        tmp_dir = self.settings.tmp_dir
        if not tmp_dir:
            tmp_dir = self.settings.project_root / "tmp"

        return get_safe_path(tmp_dir, *parts)

    def get_logs_path(self, *parts: str) -> Path:
        """
        Get safe path within logs directory.

        Args:
            *parts: Path components to join

        Returns:
            Safe path under logs directory
        """
        logs_dir = self.settings.artifacts_dir / "logs" if self.settings.artifacts_dir else self.settings.project_root / "logs"
        return get_safe_path(logs_dir, *parts)

    def list_models(self, model_type: str | None = None) -> dict[str, list[str]]:
        """
        List available models on the system.

        Args:
            model_type: Optional model type filter

        Returns:
            Dictionary mapping model types to available sizes
        """
        from .settings import settings

        available_models = {}
        model_types = [model_type] if model_type else settings.model.checkpoints.keys()

        for mtype in model_types:
            available_models[mtype] = []
            if mtype in settings.model.checkpoints:
                for size in settings.model.checkpoints[mtype]:
                    if self.get_model_path(mtype, size):
                        available_models[mtype].append(size)

        return available_models

    def get_project_info(self) -> dict[str, Any]:
        """
        Get information about the current project paths.

        Returns:
            Dictionary with project path information
        """
        return {
            "project_root": str(self.settings.project_root),
            "src_dir": str(self.settings.src_dir),
            "libs_dir": str(self.settings.libs_dir),
            "schemas_dir": str(self.settings.schemas_dir),
            "artifacts_dir": str(self.settings.artifacts_dir),
            "user_data_dir": str(self.settings.user_data_dir),
            "user_cache_dir": str(self.settings.user_cache_dir),
            "user_model_dir": str(self.settings.user_model_dir),
            "artifact_discipline": ARTIFACT_DISCIPLINE_AVAILABLE,
        }

# Create global path manager instance
# Note: This will be initialized when the module is imported
def _create_path_manager():
    """Create the global path manager instance."""
    try:
        from .settings import settings
        return PathManager(settings.path)
    except ImportError as e:
        logger.error(f"Could not initialize path manager: {e}")
        return None

paths = _create_path_manager()
