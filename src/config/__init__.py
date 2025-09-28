#!/usr/bin/env python3
"""
Configuration Management Module

This module provides centralized, type-safe configuration management for the
File Analyzer CLI application using modern Python patterns.

Key features:
- Pydantic BaseSettings for automatic environment variable binding
- Cross-platform path management using existing path utilities
- Configuration validation with JSON schemas
- Backwards compatibility with existing configuration files
- Consistent FA_* environment variable naming convention

Usage:
    from src.config import settings, paths

    # Access configuration
    model_path = paths.get_model_path("fastvlm", "1.5b")
    debug_mode = settings.app.debug

    # Environment variables automatically mapped:
    # FA_DEBUG=true -> settings.app.debug = True
    # FA_MODEL_DEFAULT_SIZE=0.5b -> settings.model.default_size = "0.5b"
"""

from .paths import PathManager, paths
from .settings import AppSettings, ModelSettings, PathSettings, settings


__all__ = [
    "AppSettings",
    "ModelSettings",
    "PathManager",
    "PathSettings",
    "paths",
    "settings"
]
