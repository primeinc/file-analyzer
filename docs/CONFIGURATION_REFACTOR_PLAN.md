# Configuration Management Refactoring Plan

## Overview

Based on the codebase audit and FastAPI best practices research, this plan outlines how to centralize all path and configuration management in the file-analyzer project using modern Python configuration patterns.

## Current Problems

### Path Management Issues
- **Inconsistent PROJECT_ROOT resolution** across modules
- **Mixed path handling**: `os.path.join()`, `pathlib.Path()`, and custom utilities
- **Scattered hardcoded paths** throughout the codebase
- **Platform-specific logic** duplicated in multiple files
- **No centralized path registry** for static directories

### Configuration Issues
- **Multiple config modules** with overlapping responsibilities
- **Inconsistent environment variable naming** (some FA_*, some hardcoded)
- **No configuration validation** or schema enforcement
- **Missing fallback strategies** for missing configs
- **No unified settings management**

## Solution Architecture

### 1. Central Configuration Module (`src/config/settings.py`)

Create a single source of truth for all configuration using Pydantic BaseSettings pattern:

```python
# Following FastAPI best practices with pydantic-settings
class PathConfig(BaseSettings):
    """Path-related configuration with automatic environment variable binding"""
    
    # Project structure paths
    project_root: Path
    src_dir: Path
    libs_dir: Path 
    schemas_dir: Path
    
    # User data paths  
    user_data_dir: Path
    user_cache_dir: Path
    user_config_dir: Path
    
    # Model paths
    user_model_dir: Path
    project_model_dir: Path
    model_cache_dir: Path
    
    # Artifact paths
    artifacts_dir: Path
    tmp_dir: Path
    logs_dir: Path
    
    class Config:
        env_prefix = "FA_"  # All environment variables start with FA_
        case_sensitive = False

class ModelConfig(BaseSettings):
    """Model-specific configuration"""
    default_model_type: str = "fastvlm"
    default_model_size: str = "1.5b" 
    available_sizes: list[str] = ["0.5b", "1.5b", "7b"]
    download_timeout: int = 300
    max_model_size_gb: int = 16
    
    class Config:
        env_prefix = "FA_MODEL_"

class AppConfig(BaseSettings):
    """Application-wide configuration"""
    debug: bool = False
    log_level: str = "INFO"
    artifact_discipline: bool = True
    max_output_size_mb: int = 100
    
    class Config:
        env_prefix = "FA_"
```

### 2. Centralized Path Management (`src/config/paths.py`)

Consolidate all static path logic using the existing path_utils:

```python
from src.utils.path_utils import (
    normalize_to_local, 
    get_safe_path, 
    ensure_dir_exists,
    RUNTIME
)

class PathManager:
    """Centralized path management with cross-platform support"""
    
    def __init__(self, config: PathConfig):
        self.config = config
        self._ensure_base_directories()
    
    def get_model_path(self, model_type: str, model_size: str) -> Path | None:
        """Unified model path resolution"""
        
    def get_artifact_path(self, artifact_type: str, context: str) -> Path:
        """Unified artifact path creation with discipline support"""
        
    def get_schema_path(self, schema_type: str, version: str = "v1.0") -> Path | None:
        """Unified schema path resolution"""
        
    def get_user_data_path(self, *parts: str) -> Path:
        """Safe user data directory path creation"""
        
    def get_cache_path(self, *parts: str) -> Path:
        """Safe cache directory path creation"""
```

### 3. Environment Variable Strategy

Implement consistent naming convention:

```bash
# Core paths
FA_PROJECT_ROOT=/path/to/project
FA_USER_DATA_DIR=/path/to/user/data
FA_CACHE_DIR=/path/to/cache

# Model configuration  
FA_MODEL_DEFAULT_TYPE=fastvlm
FA_MODEL_DEFAULT_SIZE=1.5b
FA_MODEL_CACHE_DIR=/path/to/models
FA_MODEL_MAX_SIZE_GB=16

# Application settings
FA_DEBUG=false
FA_LOG_LEVEL=INFO
FA_ARTIFACT_DISCIPLINE=true

# Override paths if needed
FA_ARTIFACTS_DIR=/custom/artifacts
FA_SCHEMAS_DIR=/custom/schemas
```

### 4. Configuration Validation Schema

Add JSON schema validation for configuration files:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "File Analyzer Configuration",
  "type": "object", 
  "properties": {
    "models": {
      "type": "object",
      "properties": {
        "default_type": {"type": "string", "enum": ["fastvlm"]},
        "default_size": {"type": "string", "enum": ["0.5b", "1.5b", "7b"]},
        "max_size_gb": {"type": "integer", "minimum": 1, "maximum": 50}
      }
    },
    "paths": {
      "type": "object",
      "properties": {
        "artifacts_dir": {"type": "string"},
        "cache_dir": {"type": "string"},
        "models_dir": {"type": "string"}
      }
    }
  }
}
```

## Implementation Plan

### Phase 1: Foundation (Priority 1)
1. **Create new config structure** (`src/config/`)
2. **Implement PathConfig and AppConfig** with Pydantic BaseSettings
3. **Create PathManager** class using existing path_utils
4. **Add configuration validation** with JSON schema

### Phase 2: Migration (Priority 2) 
1. **Update models/config.py** to use new PathManager
2. **Refactor artifact_guard.py** to use centralized paths
3. **Update cli/common/config.py** to use new settings
4. **Migrate environment variables** to FA_* convention

### Phase 3: Cleanup (Priority 3)
1. **Replace hardcoded paths** throughout codebase
2. **Consolidate duplicate path logic** 
3. **Remove legacy configuration modules**
4. **Add configuration validation to CLI startup**

### Phase 4: Testing & Documentation (Priority 4)
1. **Test path resolution** across all platforms
2. **Validate environment variable handling**
3. **Update documentation** for new configuration system
4. **Add configuration troubleshooting guide**

## Benefits

### Immediate Benefits
- **Single source of truth** for all paths and configuration
- **Consistent environment variable naming** (FA_* prefix)
- **Automatic environment variable binding** via Pydantic
- **Cross-platform path handling** via existing path_utils
- **Configuration validation** with schemas

### Long-term Benefits  
- **Easier testing** with mockable configuration
- **Better error messages** when configuration is invalid
- **Simpler deployment** with environment variable overrides
- **Reduced maintenance** with centralized logic
- **Future extensibility** for new configuration needs

## Environment Variable Migration

### Before (inconsistent):
```bash
LOCALAPPDATA=...          # Windows-specific
USER_MODEL_DIR=...        # Not consistently used
DEBUG=...                 # Generic name
```

### After (consistent):
```bash
FA_USER_DATA_DIR=...      # Cross-platform
FA_MODEL_USER_DIR=...     # Clear purpose  
FA_DEBUG=...              # Namespaced
FA_LOG_LEVEL=...          # Explicit
```

## File Structure Changes

```
src/
├── config/
│   ├── __init__.py          # Export main config
│   ├── settings.py          # Pydantic settings classes
│   ├── paths.py            # PathManager class
│   └── validation.py       # Schema validation
├── models/
│   ├── config.py           # UPDATED: Use PathManager
│   └── ...
├── cli/
│   ├── common/
│   │   └── config.py       # UPDATED: Use new settings
│   └── ...
└── core/
    ├── artifact_guard.py   # UPDATED: Use PathManager
    └── ...
```

## Backwards Compatibility

- **Gradual migration** - old config still works during transition
- **Environment variable fallbacks** - old vars still read but deprecated
- **Configuration file compatibility** - existing config.json still works
- **Deprecation warnings** - inform users of changes without breaking

This plan ensures a smooth transition to modern, maintainable configuration management while preserving existing functionality.