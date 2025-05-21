#!/usr/bin/env python3
"""
Tests for model adapters and management

This script tests the model adapter system, including mock adapters,
FastVLM adapters, and the model manager.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the models components
from src.models.mock_adapter import MockModelAdapter, create_adapter as create_mock_adapter
from src.models.manager import ModelManager, create_manager
from src.models.config import get_model_info, get_model_path

# Import artifact discipline components for mocking
from src.core.artifact_guard import get_canonical_artifact_path, validate_artifact_path

class TestMockAdapter(unittest.TestCase):
    """Test the mock adapter used for testing when real models aren't available"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temp directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test image
        self.test_image = os.path.join(self.temp_dir, "test.jpg")
        with open(self.test_image, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0')  # JPEG header
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_mock_adapter_creation(self):
        """Test creating a mock adapter"""
        # Create with default options
        adapter = MockModelAdapter()
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.model_type, "mock")
        
        # Create with custom options
        adapter = MockModelAdapter(model_type="vision", model_size="medium")
        self.assertEqual(adapter.model_type, "vision")
        self.assertEqual(adapter.model_size, "medium")
        
        # Test the factory function
        adapter = create_mock_adapter()
        self.assertIsNotNone(adapter)
        self.assertIsInstance(adapter, MockModelAdapter)
    
    def test_mock_adapter_predict(self):
        """Test the predict method of mock adapter"""
        adapter = MockModelAdapter()
        
        # Test with image path
        result = adapter.predict(self.test_image, prompt="Describe this image")
        self.assertIsNotNone(result)
        self.assertIn("description", result)
        
        # Test with different prompts/modes
        result = adapter.predict(self.test_image, prompt="Detect objects", mode="detect")
        self.assertIsNotNone(result)
        self.assertIn("objects", result)
        
        # Test with non-existent path
        invalid_image = os.path.join(self.temp_dir, "nonexistent.jpg")
        # The mock adapter doesn't actually check if the file exists,
        # it just generates a response based on the file name and extension
        result = adapter.predict(invalid_image)
        self.assertIsNotNone(result)
        # Even with a non-existent file, it should still return a result with description
        self.assertIn("description", result)
    
    def test_mock_adapter_get_info(self):
        """Test getting adapter info"""
        adapter = MockModelAdapter()
        info = adapter.get_info()
        
        self.assertIsNotNone(info)
        self.assertIn("name", info)
        self.assertEqual(info["name"], "MockModelAdapter")
        self.assertIn("type", info)
        self.assertEqual(info["type"], "mock")
        self.assertIn("capabilities", info)
        self.assertIn("describe", info["capabilities"])
        self.assertIn("detect", info["capabilities"])
        self.assertIn("document", info["capabilities"])

class TestModelManager(unittest.TestCase):
    """Test the model manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temp directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a test image
        self.test_image = os.path.join(self.temp_dir, "test.jpg")
        with open(self.test_image, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0')  # JPEG header
        
        # Patch canonical artifact paths
        self.patch_canonical_path = patch('src.models.manager.get_canonical_artifact_path')
        self.mock_canonical_path = self.patch_canonical_path.start()
        self.mock_canonical_path.return_value = os.path.join(self.temp_dir, "artifacts", "output")
        
        # Create the directory
        os.makedirs(self.mock_canonical_path.return_value, exist_ok=True)
        
        # Add mock adapter to manager for testing
        self.patch_register = patch('src.models.manager.ModelManager._register_adapters')
        self.mock_register = self.patch_register.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.patch_canonical_path.stop()
        self.patch_register.stop()
        shutil.rmtree(self.temp_dir)
    
    def test_create_manager(self):
        """Test creating a model manager"""
        # Create manager
        manager = create_manager()
        self.assertIsNotNone(manager)
        self.assertIsInstance(manager, ModelManager)
    
    def test_manager_get_adapter(self):
        """Test getting adapters from the manager"""
        # Create manager
        manager = create_manager()
        
        # Mock the adapters
        manager.adapters = {"mock": MockModelAdapter}
        
        # Get the mock adapter
        adapter = manager.get_adapter("vision", "mock")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter, MockModelAdapter)
        
        # Test with nonexistent adapter
        adapter = manager.get_adapter("vision", "nonexistent_adapter")
        self.assertIsNone(adapter)
    
    def test_manager_analyze_file(self):
        """Test model manager analyze_file functionality"""
        # Create manager for testing
        manager = create_manager()
        
        # Mock create_model to return a mock adapter
        mock_adapter = MockModelAdapter()
        with patch.object(manager, 'create_model', return_value=mock_adapter):
            # Test analyzing an image
            result = manager.analyze_file(
                self.test_image,
                model_type="vision",
                model_name="mock",
                prompt="Describe this image"
            )
            
            # Verify the result
            self.assertIsNotNone(result)
            self.assertNotIn("error", result)
            
            # Test with output path
            output_path = os.path.join(self.temp_dir, "output.json")
            
            # Mock file operations
            with patch('builtins.open', mock_open()):
                # Mock validate_artifact_path to allow any path
                with patch('src.models.manager.validate_artifact_path', return_value=True):
                    # Also mock PathGuard
                    with patch('src.models.manager.PathGuard'):
                        result = manager.analyze_file(
                            self.test_image,
                            model_type="vision",
                            model_name="mock",
                            prompt="Describe this",
                            output_path=output_path
                        )
                        
                        # Verify we still get results
                        self.assertIsNotNone(result)
    
    def test_batch_analyze(self):
        """Test batch analysis functionality"""
        # Create test directory with multiple images
        test_dir = os.path.join(self.temp_dir, "test_images")
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a few test images
        for i in range(3):
            image_path = os.path.join(test_dir, f"test_{i}.jpg")
            with open(image_path, 'wb') as f:
                f.write(b'\xFF\xD8\xFF\xE0')  # JPEG header
        
        # Create output directory
        output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create manager for testing
        manager = create_manager()
        
        # Create a mock adapter
        mock_adapter = MockModelAdapter()
        
        # Mock create_model to return our mock adapter
        with patch.object(manager, 'create_model', return_value=mock_adapter):
            # Mock _get_files to return our test images
            with patch.object(manager, '_get_files', return_value=[
                os.path.join(test_dir, f"test_{i}.jpg") for i in range(3)
            ]):
                # Also patch validation for artifact paths
                with patch('src.models.manager.validate_artifact_path', return_value=True):
                    # And PathGuard
                    with patch('src.models.manager.PathGuard'):
                        # Mock file operations
                        with patch('builtins.open', mock_open()):
                            # Batch analyze
                            results = manager.batch_analyze(
                                test_dir,
                                model_type="vision",
                                model_name="mock",
                                prompt="Test prompt",
                                output_dir=output_dir
                            )
                            
                            # Verify results
                            self.assertIsNotNone(results)
                            self.assertIsInstance(results, dict)
                            self.assertEqual(len(results), 3)

@patch('src.models.config.os.path.exists')
class TestModelConfig(unittest.TestCase):
    """Test model configuration functionality"""
    
    def test_get_model_info(self, mock_exists):
        """Test getting model information"""
        # Setup the mock to indicate the paths exist
        mock_exists.return_value = True
        
        # Get info for a standard model
        model_info = get_model_info("fastvlm", "0.5b")
        self.assertIsNotNone(model_info)
        self.assertIn("description", model_info)
        self.assertEqual(model_info["description"], "FastVLM 0.5B model (small)")
        
        # Get info for nonexistent model
        model_info = get_model_info("nonexistent_model", "0.5b")
        self.assertIsNotNone(model_info)
        self.assertIn("error", model_info)
    
    def test_get_model_path(self, mock_exists):
        """Test getting model paths"""
        # Configure mock to simulate existing paths
        mock_exists.return_value = True
        
        # Test finding a model path for valid model
        model_path = get_model_path("fastvlm", "0.5b")
        self.assertIsNotNone(model_path)
        
        # Reset the mock and make it return False
        mock_exists.return_value = False
        
        # Test with nonexistent model
        model_path = get_model_path("fastvlm", "0.5b")
        self.assertIsNone(model_path)

if __name__ == "__main__":
    unittest.main()