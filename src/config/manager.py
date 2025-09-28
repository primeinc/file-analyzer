#!/usr/bin/env python3
"""
Configuration Manager - Compatibility Shim

This module provides a compatibility layer for existing code that expects
a ConfigManager class. It wraps the new settings system to provide the
same interface.
"""

import logging
from typing import Any

from .settings import settings


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration manager providing a familiar interface for accessing settings.
    
    This class acts as a thin wrapper around the new pydantic-based settings
    system, providing backwards compatibility for existing code.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._settings = settings
        logger.debug("Initialized ConfigManager compatibility shim")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with dot notation support.
        
        Args:
            key: Configuration key (supports dot notation like 'model.default_size')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Examples:
            config.get('vision.default_model', 'fastvlm')
            config.get('vision.model_size') 
            config.get('analysis.default_include_patterns', [])
        """
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value (limited support for backwards compatibility).
        
        Args:
            key: Configuration key 
            value: Value to set
            
        Note:
            This method provides limited backwards compatibility. The new
            settings system is primarily designed to be configured via
            environment variables or initialization.
        """
        logger.warning(f"ConfigManager.set() called for key '{key}' - "
                      f"consider using environment variables instead")
        
        # For backwards compatibility, try to set the value
        parts = key.split('.')
        if len(parts) == 2:
            section, setting = parts
            section_obj = getattr(self._settings, section, None)
            if section_obj and hasattr(section_obj, setting):
                setattr(section_obj, setting, value)
                logger.debug(f"Set {key} = {value}")
                return
                
        logger.warning(f"Could not set configuration key '{key}' = {value}")
    
    def load_config(self, config_path: str = None) -> None:
        """
        Load configuration from file (backwards compatibility method).
        
        Args:
            config_path: Path to configuration file (ignored in new system)
            
        Note:
            The new settings system loads configuration automatically.
            This method exists for backwards compatibility only.
        """
        logger.debug(f"ConfigManager.load_config() called with path '{config_path}' "
                    f"- configuration is loaded automatically in new system")
    
    def save_config(self, config_path: str = None) -> None:
        """
        Save configuration to file (backwards compatibility method).
        
        Args:
            config_path: Path to save configuration to
            
        Note:
            The new settings system uses environment variables and doesn't
            save back to files. This method exists for backwards compatibility.
        """
        logger.warning(f"ConfigManager.save_config() called with path '{config_path}' "
                      f"- new configuration system uses environment variables")