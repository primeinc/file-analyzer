#!/usr/bin/env python3
"""
Tests for the vision core module

This script tests the core vision processing capabilities, including:
1. Vision model configuration and initialization
2. Image processing and analysis
3. Prompt generation and handling
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

# Import the vision components
from src.core.vision import (
    VisionAnalyzer,
    PIL_AVAILABLE,
    DEFAULT_VISION_CONFIG,
    VISION_MODELS
)

# Import artifact guard for mocking
from src.core.artifact_guard import PathGuard, validate_artifact_path

class TestVisionAnalyzer(unittest.TestCase):
    """Test the VisionAnalyzer class"""
    
    def setUp(self):
        """Set up the test environment"""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a sample image
        self.test_image_path = os.path.join(self.temp_dir, "test_image.jpg")
        with open(self.test_image_path, 'wb') as f:
            f.write(b'\xFF\xD8\xFF')  # JPEG header
        
        # Patch canonical artifact path creation
        self.patch_canonical_path = patch('src.core.vision.get_canonical_artifact_path')
        self.mock_canonical_path = self.patch_canonical_path.start()
        self.mock_canonical_path.return_value = os.path.join(self.temp_dir, "artifacts", "vision", "test_output")
        
        # Create the artifact path
        os.makedirs(self.mock_canonical_path.return_value, exist_ok=True)
    
    def tearDown(self):
        """Clean up the test environment"""
        # Stop all patches
        self.patch_canonical_path.stop()
        
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test that the VisionAnalyzer initializes correctly with default and custom configs"""
        # Test with default config
        analyzer = VisionAnalyzer()
        self.assertEqual(analyzer.model_name, DEFAULT_VISION_CONFIG["model"])
        self.assertEqual(analyzer.model_info, VISION_MODELS[DEFAULT_VISION_CONFIG["model"]])
        
        # Test with custom config
        custom_config = {
            "model": "qwen2vl",
            "resolution": "1024x1024",
            "max_images": 5
        }
        analyzer = VisionAnalyzer(custom_config)
        self.assertEqual(analyzer.model_name, "qwen2vl")
        self.assertEqual(analyzer.model_info, VISION_MODELS["qwen2vl"])
        self.assertEqual(analyzer.resolution, "1024x1024")
    
    def test_model_size_detection(self):
        """Test detection of model sizes"""
        # Test FastVLM 0.5B detection
        config = {
            "model": "fastvlm", 
            "model_path": "some/path/llava-fastvithd_0.5b_stage3"
        }
        analyzer = VisionAnalyzer(config)
        self.assertEqual(analyzer._determine_model_size(), "0.5B")
        
        # Test FastVLM 1.5B detection
        config = {
            "model": "fastvlm", 
            "model_path": "some/path/llava-fastvithd_1.5b_stage3"
        }
        analyzer = VisionAnalyzer(config)
        self.assertEqual(analyzer._determine_model_size(), "1.5B")
        
        # Test FastVLM 7B detection
        config = {
            "model": "fastvlm", 
            "model_path": "some/path/llava-fastvithd_7b_stage3"
        }
        analyzer = VisionAnalyzer(config)
        self.assertEqual(analyzer._determine_model_size(), "7B")
        
        # Test unknown model size
        config = {
            "model": "fastvlm", 
            "model_path": "some/path/unknown_model"
        }
        analyzer = VisionAnalyzer(config)
        self.assertEqual(analyzer._determine_model_size(), "")
    
    def test_get_model_display_name(self):
        """Test the get_model_display_name method"""
        # Test with default model
        analyzer = VisionAnalyzer()
        display_name = analyzer.get_model_display_name()
        self.assertIsNotNone(display_name)
        self.assertIn("FastVLM", display_name)
        
        # Test with specific model
        config = {"model": "qwen2vl"}
        analyzer = VisionAnalyzer(config)
        display_name = analyzer.get_model_display_name()
        self.assertIsNotNone(display_name)
        self.assertIn("Qwen2-VL", display_name)
    
    def test_get_prompt_for_mode(self):
        """Test prompt generation for different analysis modes"""
        # Create a VisionAnalyzer instance
        analyzer = VisionAnalyzer()
        
        # Test describe mode prompt
        prompt = analyzer._get_prompt_for_mode("describe")
        self.assertIsNotNone(prompt)
        self.assertIn("describe", prompt.lower())
        
        # Test detect mode prompt (uses "objects" keyword)
        prompt = analyzer._get_prompt_for_mode("detect")
        self.assertIsNotNone(prompt)
        self.assertIn("objects", prompt.lower())
        
        # Test document mode prompt
        prompt = analyzer._get_prompt_for_mode("document")
        self.assertIsNotNone(prompt)
        self.assertIn("document", prompt.lower())
    
    @unittest.skipIf(not PIL_AVAILABLE, "PIL not available for image preprocessing test")
    def test_preprocess_image_with_mocks(self):
        """Test image preprocessing with mocked dependencies"""
        # Create a VisionAnalyzer instance
        analyzer = VisionAnalyzer()
        
        # Need to patch several methods and functions to avoid actual processing
        with patch('subprocess.run') as mock_subprocess_run:
            # Configure subprocess.run to return success
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "Image processed"
            mock_subprocess_run.return_value = mock_process
            
            # Patch PathGuard to allow file operations
            with patch('src.core.vision.PathGuard') as mock_path_guard:
                # Configure the context manager
                mock_context = MagicMock()
                mock_path_guard.return_value.__enter__.return_value = mock_context
                mock_path_guard.return_value.__exit__.return_value = None
                
                # Also patch validate_artifact_path to allow any path
                with patch('src.core.vision.validate_artifact_path', return_value=True):
                    try:
                        # Call the method
                        analyzer.preprocess_image(self.test_image_path)
                        # If we get here without exceptions, the test passes
                        self.assertTrue(True)
                    except Exception as e:
                        self.fail(f"preprocess_image raised unexpected exception: {e}")
    
    def test_check_dependencies(self):
        """Test the check_dependencies method"""
        # Create a VisionAnalyzer instance
        analyzer = VisionAnalyzer()
        
        # Patch subprocess.run to control behavior
        with patch('subprocess.run') as mock_subprocess_run:
            # Configure subprocess.run to return success
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_subprocess_run.return_value = mock_process
            
            # Call the method
            result = analyzer.check_dependencies()
            
            # Verify that the method runs without errors
            self.assertIsNotNone(result)
            
            # Reset the mock and make it return an error
            mock_subprocess_run.reset_mock()
            mock_process.returncode = 1
            mock_subprocess_run.return_value = mock_process
            
            # Call the method again
            result = analyzer.check_dependencies()
            
            # Should still run without errors but with different result
            self.assertIsNotNone(result)
    
    def test_analyze_image_with_mocks(self):
        """Test the analyze_image method with all dependencies mocked"""
        # Create a VisionAnalyzer instance
        analyzer = VisionAnalyzer()
        
        # We need to mock several components to isolate the analyze_image method
        
        # First, patch preprocess_image to return our test image path
        with patch.object(analyzer, 'preprocess_image', return_value=self.test_image_path):
            # Next, patch subprocess.run to return a sample response
            with patch('subprocess.run') as mock_subprocess_run:
                # Configure subprocess to return a sample json output
                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.stdout = '{"description": "A test image", "tags": ["test"]}'
                mock_subprocess_run.return_value = mock_process
                
                # Also patch PathGuard and validation
                with patch('src.core.vision.PathGuard'):
                    with patch('src.core.vision.validate_artifact_path', return_value=True):
                        with patch('builtins.open', mock_open()):
                            try:
                                # Call the method
                                result = analyzer.analyze_image(
                                    self.test_image_path, 
                                    prompt="Test prompt",
                                    mode="describe"
                                )
                                
                                # If we get here, the method executed without errors
                                self.assertIsNotNone(result)
                            except Exception as e:
                                self.fail(f"analyze_image raised unexpected exception: {e}")
    
    def test_batch_analyze_with_mocks(self):
        """Test the batch_analyze method with dependencies mocked"""
        # Create a directory with multiple test images
        test_dir = os.path.join(self.temp_dir, "test_images")
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a few test images
        image_paths = []
        for i in range(3):
            image_path = os.path.join(test_dir, f"test_image_{i}.jpg")
            with open(image_path, 'wb') as f:
                f.write(b'\xFF\xD8\xFF')  # JPEG header
            image_paths.append(image_path)
        
        # Create output directory
        output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a VisionAnalyzer instance
        analyzer = VisionAnalyzer()
        
        # Mock all the dependencies
        
        # Mock glob to return our test images
        with patch('glob.glob', return_value=image_paths):
            # Mock analyze_image to return a dummy result
            with patch.object(analyzer, 'analyze_image', return_value={"description": "Test image"}):
                # Mock Path.glob to find our test images
                with patch('pathlib.Path.glob', return_value=image_paths):
                    # Mock PathGuard and validation
                    with patch('src.core.vision.PathGuard'):
                        with patch('src.core.vision.validate_artifact_path', return_value=True):
                            try:
                                # Call the method
                                results = analyzer.batch_analyze(test_dir, output_dir, mode="describe")
                                
                                # If we get here, the method executed without errors
                                self.assertIsNotNone(results)
                            except Exception as e:
                                self.fail(f"batch_analyze raised unexpected exception: {e}")

if __name__ == "__main__":
    unittest.main()