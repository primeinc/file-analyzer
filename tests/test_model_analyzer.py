#!/usr/bin/env python3
"""
Test Model Analyzer - Integration test for the model analysis system

This script tests the model analyzer system with the mock model adapter:
1. Tests single file analysis with different modes
2. Tests batch directory processing
3. Verifies expected output formats and structures
4. Checks proper error handling
5. Validates artifact discipline compliance
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import components to test
from src.model_analyzer import ModelAnalyzer
from src.model_manager import ModelManager, create_manager
from src.mock_model_adapter import create_adapter, MockModelAdapter
from src.artifact_guard import get_canonical_artifact_path, validate_artifact_path

class TestModelAnalyzer(unittest.TestCase):
    """Test cases for the model analyzer system."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test image files
        self.test_image = os.path.join(self.temp_dir, "test_image.jpg")
        with open(self.test_image, 'wb') as f:
            # Create an empty JPG file (content doesn't matter for mock adapter)
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00')
        
        # Create a batch directory with multiple images
        self.batch_dir = os.path.join(self.temp_dir, "batch")
        os.makedirs(self.batch_dir, exist_ok=True)
        
        # Create 5 test images in the batch directory
        for i in range(5):
            test_file = os.path.join(self.batch_dir, f"test_image_{i}.jpg")
            with open(test_file, 'wb') as f:
                f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00')
        
        # Create a custom model manager with mock adapter
        self.manager = ModelManager()
        self.manager.adapters["mock"] = create_adapter
        
        # Initialize analyzer with custom manager
        self.analyzer = ModelAnalyzer({"model_manager": self.manager})
        
        # Override the model manager in the analyzer
        self.analyzer.model_manager = self.manager
    
    def tearDown(self):
        """Clean up the test environment."""
        # Remove temporary directory and files
        shutil.rmtree(self.temp_dir)
    
    def test_mock_adapter_creation(self):
        """Test creating the mock adapter."""
        adapter = create_adapter(model_size="medium")
        self.assertEqual(adapter.model_type, "mock")
        self.assertEqual(adapter.model_size, "medium")
        
        # Test adapter info
        info = adapter.get_info()
        self.assertEqual(info["name"], "MockModelAdapter")
        self.assertEqual(info["type"], "mock")
        self.assertEqual(info["size"], "medium")
        self.assertTrue("capabilities" in info)
    
    def test_single_file_analysis_describe(self):
        """Test analyzing a single file in describe mode."""
        # Create a mock adapter directly
        adapter = create_adapter(model_size="small")
        
        # Use the adapter directly
        result = adapter.predict(
            self.test_image,
            mode="describe"
        )
        
        # Check response structure
        self.assertTrue("description" in result)
        self.assertTrue("tags" in result)
        self.assertTrue("metadata" in result)
        
        # Verify metadata
        self.assertEqual(result["metadata"]["model"], "mock_small")
        self.assertEqual(result["metadata"]["mode"], "describe")
        self.assertTrue("execution_time" in result["metadata"])
        self.assertTrue("timestamp" in result["metadata"])
        self.assertTrue(result["metadata"]["mock"])
    
    def test_single_file_analysis_detect(self):
        """Test analyzing a single file in detect mode."""
        # Create a mock adapter directly
        adapter = create_adapter(model_size="small")
        
        # Use the adapter directly
        result = adapter.predict(
            self.test_image,
            mode="detect"
        )
        
        # Check response structure
        self.assertTrue("objects" in result)
        self.assertTrue("description" in result)
        self.assertTrue("metadata" in result)
        
        # Verify objects structure
        self.assertTrue(isinstance(result["objects"], list))
        if result["objects"]:  # If any objects detected
            obj = result["objects"][0]
            self.assertTrue("name" in obj)
            self.assertTrue("location" in obj)
    
    def test_single_file_analysis_document(self):
        """Test analyzing a single file in document mode."""
        # Create a mock adapter directly
        adapter = create_adapter(model_size="small")
        
        # Use the adapter directly
        result = adapter.predict(
            self.test_image,
            mode="document"
        )
        
        # Check response structure
        self.assertTrue("text" in result)
        self.assertTrue("document_type" in result)
        self.assertTrue("metadata" in result)
        
        # Verify text is not empty
        self.assertTrue(len(result["text"]) > 0)
    
    def test_batch_processing(self):
        """Test batch processing simulated results."""
        # Process 5 files with mock adapter
        results = {}
        adapter = create_adapter(model_size="small")
        
        # Process each file
        for i in range(5):
            test_file = os.path.join(self.batch_dir, f"test_image_{i}.jpg")
            results[test_file] = adapter.predict(test_file, mode="describe")
        
        # Check we got results for all files
        self.assertEqual(len(results), 5)
        
        # Verify each result
        for file_path, result in results.items():
            self.assertTrue("description" in result)
            self.assertTrue("tags" in result)
            self.assertTrue("metadata" in result)
    
    def test_output_path_artifact_discipline(self):
        """Test output paths adhere to artifact discipline."""
        # Get a canonical output path
        output_dir = get_canonical_artifact_path("vision", "test_model_analyzer")
        output_file = os.path.join(output_dir, "test_result.json")
        
        # Create a mock adapter directly
        adapter = create_adapter(model_size="small")
        
        # Run prediction with output path
        result = adapter.predict(
            self.test_image,
            mode="describe",
            output_path=output_file
        )
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_file))
        
        # Check file content
        with open(output_file, 'r') as f:
            saved_result = json.load(f)
        
        # Verify content matches
        self.assertEqual(saved_result["description"], result["description"])
    
    def test_error_handling(self):
        """Test error handling for non-existent files."""
        # Create a mock adapter directly
        adapter = create_adapter(model_size="small")
        
        # Try to analyze a non-existent file
        non_existent_file = os.path.join(self.temp_dir, "does_not_exist.jpg")
        
        # This should handle the error gracefully
        result = self.analyzer.analyze_file(
            non_existent_file,
            model_type="vision",
            model_name="mock",
            model_size="small",
            mode="describe"
        )
        
        # Check error in result
        self.assertTrue("error" in result)


if __name__ == "__main__":
    unittest.main()