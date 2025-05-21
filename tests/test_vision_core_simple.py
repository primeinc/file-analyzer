#!/usr/bin/env python3
"""
Simplified tests for the vision core module

This script provides basic tests for the core vision analyzer functionality
without requiring complex image processing or model execution.
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the vision analyzer
from src.core.vision import VisionAnalyzer, VISION_MODELS, DEFAULT_VISION_CONFIG

class TestVisionCoreSimple(unittest.TestCase):
    """Basic tests for the VisionAnalyzer class"""
    
    def setUp(self):
        """Set up the test environment"""
        # Create a test directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a dummy image file for testing
        self.test_image = os.path.join(self.temp_dir, "test_image.jpg")
        with open(self.test_image, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0')  # Simple JPEG header
    
    def tearDown(self):
        """Clean up after tests"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test basic initialization"""
        # Test with default config
        analyzer = VisionAnalyzer()
        self.assertEqual(analyzer.model_name, DEFAULT_VISION_CONFIG["model"])
        self.assertEqual(analyzer.model_info, VISION_MODELS[DEFAULT_VISION_CONFIG["model"]])
        
        # Test with custom config
        custom_config = {"model": "qwen2vl"}
        analyzer = VisionAnalyzer(custom_config)
        self.assertEqual(analyzer.model_name, "qwen2vl")
        self.assertEqual(analyzer.model_info, VISION_MODELS["qwen2vl"])
    
    def test_model_size_detection(self):
        """Test model size detection for FastVLM models"""
        # Test the _determine_model_size method with various paths
        
        # Test 0.5B model
        config = {"model": "fastvlm", "model_path": "/path/to/llava-fastvithd_0.5b_stage3"}
        analyzer = VisionAnalyzer(config)
        self.assertEqual(analyzer._determine_model_size(), "0.5B")
        
        # Test 1.5B model
        config = {"model": "fastvlm", "model_path": "/path/to/llava-fastvithd_1.5b_stage3"}
        analyzer = VisionAnalyzer(config)
        self.assertEqual(analyzer._determine_model_size(), "1.5B")
        
        # Test 7B model
        config = {"model": "fastvlm", "model_path": "/path/to/llava-fastvithd_7b_stage3"}
        analyzer = VisionAnalyzer(config)
        self.assertEqual(analyzer._determine_model_size(), "7B")
        
        # Test unknown model size
        config = {"model": "fastvlm", "model_path": "/path/to/unknown_model"}
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
        """Test prompt generation for analysis modes"""
        analyzer = VisionAnalyzer()
        
        # Test describe mode
        describe_prompt = analyzer._get_prompt_for_mode("describe")
        self.assertIsNotNone(describe_prompt)
        self.assertIn("describe", describe_prompt.lower())
        
        # Test detect mode
        detect_prompt = analyzer._get_prompt_for_mode("detect")
        self.assertIsNotNone(detect_prompt)
        self.assertIn("objects", detect_prompt.lower())
        
        # Test document mode
        document_prompt = analyzer._get_prompt_for_mode("document")
        self.assertIsNotNone(document_prompt)
        self.assertIn("document", document_prompt.lower())

if __name__ == "__main__":
    unittest.main()