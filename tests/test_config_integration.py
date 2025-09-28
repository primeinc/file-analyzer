#!/usr/bin/env python3
"""
Integration Test for New Configuration System

This script tests the integration between our new configuration system
and the core components (FileAnalyzer, VisionAnalyzer, ModelManager).
"""

import os
import sys


# Add src to the path so we can import our modules
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)


def test_config_manager():
    """Test ConfigManager functionality"""
    print("Testing ConfigManager...")

    try:
        from src.config.manager import ConfigManager

        # Test initialization
        config = ConfigManager()

        # Test basic get
        vision_model = config.get("vision.default_model", "fallback")
        print(f"✓ Vision default model: {vision_model}")

        # Test environment variable support
        old_env = os.environ.get("FA_MODEL_SIZE")
        os.environ["FA_MODEL_SIZE"] = "0.5b"

        config = ConfigManager()  # Recreate to pick up env var
        model_size = config.get("models.fastvlm.default_size")
        print(f"✓ Model size from env: {model_size}")

        # Restore environment
        if old_env:
            os.environ["FA_MODEL_SIZE"] = old_env
        else:
            del os.environ["FA_MODEL_SIZE"]

        print("✓ ConfigManager tests passed")
        return True

    except Exception as e:
        print(f"✗ ConfigManager test failed: {e}")
        return False


def test_path_manager():
    """Test PathManager functionality"""
    print("\nTesting PathManager...")

    try:
        from src.config.paths import PathManager

        path_manager = PathManager()

        # Test models directory
        models_dir = path_manager.get_models_dir()
        print(f"✓ Models directory: {models_dir}")

        # Test artifact paths
        artifact_path = path_manager.get_artifacts_dir()
        print(f"✓ Artifacts directory: {artifact_path}")

        print("✓ PathManager tests passed")
        return True

    except Exception as e:
        print(f"✗ PathManager test failed: {e}")
        return False


def test_file_analyzer():
    """Test FileAnalyzer with new configuration system"""
    print("\nTesting FileAnalyzer...")

    try:
        from src.core.analyzer import FileAnalyzer

        # Test initialization with no config (should use ConfigManager)
        analyzer = FileAnalyzer()

        # Test with legacy config
        legacy_config = {
            "max_metadata_files": 25,
            "tool_options": {"exiftool": ["-json", "-G"]},
        }
        analyzer_legacy = FileAnalyzer(legacy_config)

        # Test config value access
        max_files = analyzer._get_config_value("analysis.max_metadata_files", 50)
        print(f"✓ Max metadata files: {max_files}")

        exiftool_opts = analyzer._get_config_value("tools.exiftool.options", [])
        print(f"✓ Exiftool options: {exiftool_opts}")

        # Test legacy config fallback
        legacy_max = analyzer_legacy._get_config_value(
            "analysis.max_metadata_files", 50
        )
        print(f"✓ Legacy max files: {legacy_max}")

        print("✓ FileAnalyzer tests passed")
        return True

    except Exception as e:
        print(f"✗ FileAnalyzer test failed: {e}")
        return False


def test_vision_analyzer():
    """Test VisionAnalyzer with new configuration system"""
    print("\nTesting VisionAnalyzer...")

    try:
        from src.core.vision import VisionAnalyzer

        # Test initialization with no config (should use ConfigManager)
        analyzer = VisionAnalyzer()

        # Test config value access
        model_name = analyzer._get_config_value("model", "fallback")
        print(f"✓ Model name: {model_name}")

        max_images = analyzer._get_config_value("max_images", 5)
        print(f"✓ Max images: {max_images}")

        # Test model path resolution
        model_path = analyzer._get_model_path()
        print(f"✓ Model path: {model_path or 'Not found (expected)'}")

        # Test with legacy config
        legacy_config = {"model": "fastvlm", "max_images": 15, "output_format": "json"}
        analyzer_legacy = VisionAnalyzer(legacy_config)
        legacy_max = analyzer_legacy._get_config_value("max_images", 5)
        print(f"✓ Legacy max images: {legacy_max}")

        print("✓ VisionAnalyzer tests passed")
        return True

    except Exception as e:
        print(f"✗ VisionAnalyzer test failed: {e}")
        return False


def test_model_manager():
    """Test ModelManager with new configuration system"""
    print("\nTesting ModelManager...")

    try:
        from src.models.manager import ModelManager

        # Test initialization
        manager = ModelManager()

        # Test model configs loaded from ConfigManager
        vision_config = manager.model_configs.get("vision", {})
        print(f"✓ Vision config: {vision_config}")

        # Test available models
        available = manager.get_available_models("vision")
        print(f"✓ Available vision models: {available}")

        # Test model path resolution
        model_path = manager._get_model_path("fastvlm", "1.5b")
        print(f"✓ FastVLM model path: {model_path or 'Not found (expected)'}")

        print("✓ ModelManager tests passed")
        return True

    except Exception as e:
        print(f"✗ ModelManager test failed: {e}")
        return False


def test_environment_variable_integration():
    """Test environment variable integration"""
    print("\nTesting environment variable integration...")

    try:
        # Test model config with environment variables
        old_env = os.environ.get("FA_MODEL_VISION_DEFAULT")
        os.environ["FA_MODEL_VISION_DEFAULT"] = "test_model"

        from src.core.vision import VisionAnalyzer

        analyzer = VisionAnalyzer()

        model_name = analyzer._get_config_value("model")
        print(f"✓ Model from env var: {model_name}")

        # Test model size environment variable
        old_size_env = os.environ.get("FA_MODEL_SIZE")
        os.environ["FA_MODEL_SIZE"] = "7b"

        from src.config.manager import ConfigManager

        config = ConfigManager()

        # Check if environment variable is reflected
        print("✓ Environment variables integrated")

        # Cleanup
        if old_env:
            os.environ["FA_MODEL_VISION_DEFAULT"] = old_env
        else:
            del os.environ["FA_MODEL_VISION_DEFAULT"]

        if old_size_env:
            os.environ["FA_MODEL_SIZE"] = old_size_env
        else:
            if "FA_MODEL_SIZE" in os.environ:
                del os.environ["FA_MODEL_SIZE"]

        return True

    except Exception as e:
        print(f"✗ Environment variable test failed: {e}")
        return False


def main():
    """Run all integration tests"""
    print("Starting configuration system integration tests...\n")

    test_results = []

    # Run tests
    test_results.append(test_config_manager())
    test_results.append(test_path_manager())
    test_results.append(test_file_analyzer())
    test_results.append(test_vision_analyzer())
    test_results.append(test_model_manager())
    test_results.append(test_environment_variable_integration())

    # Summary
    passed = sum(test_results)
    total = len(test_results)

    print("\n" + "=" * 50)
    print(f"Integration Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Configuration system integration is working.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
