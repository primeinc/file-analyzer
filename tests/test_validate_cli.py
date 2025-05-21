#!/usr/bin/env python3
"""
Tests for the validate CLI module

This module tests the CLI interface for validation commands, ensuring:
1. Command options are correctly parsed
2. JSON schema validation works properly
3. Image comparison functionality works correctly
4. Validation results are properly formatted
5. Error handling works as expected
"""

import os
import sys
import json
import tempfile
import time
import platform
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
import jsonschema
from typer.testing import CliRunner

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the validate CLI app
from src.cli.validate.main import app

# Create CLI test runner
runner = CliRunner(mix_stderr=False)

class TestSchemaValidation:
    """Tests for the schema validation command"""
    
    def test_file_not_exists(self):
        """Test validation with a non-existent file"""
        # Run the command with a non-existent file
        result = runner.invoke(app, ["schema", "/nonexistent/file.json"])
        
        # Check that the command failed with appropriate error message
        assert result.exit_code == 1
        assert "Error: File does not exist" in result.stdout
    
    def test_invalid_json_file(self):
        """Test validation with an invalid JSON file"""
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_file.write('{"invalid": "json"')  # Missing closing brace
            tmp_path = tmp_file.name
        
        try:
            # Run the command
            result = runner.invoke(app, ["schema", tmp_path])
            
            # Check that the command failed with appropriate error message
            assert result.exit_code == 1
            assert "Error: Invalid JSON file" in result.stdout
        finally:
            # Clean up
            os.unlink(tmp_path)
    
    @patch('src.cli.validate.main.config.get_schema_path')
    def test_schema_not_found(self, mock_get_schema_path):
        """Test validation when the schema cannot be found"""
        # Mock get_schema_path to return a non-existent file
        mock_get_schema_path.return_value = "/nonexistent/schema.json"
        
        # Create a temporary file with valid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_file.write('{"test": "value"}')
            tmp_path = tmp_file.name
        
        try:
            # Run the command
            result = runner.invoke(app, ["schema", tmp_path])
            
            # Check that the command failed with appropriate error message
            assert result.exit_code == 1
            assert "Error: Schema file not found" in result.stdout
        finally:
            # Clean up
            os.unlink(tmp_path)
    
    @patch('src.cli.validate.main.config.get_schema_path')
    @patch('jsonschema.validate')
    def test_successful_validation(self, mock_validate, mock_get_schema_path):
        """Test successful schema validation"""
        # Create a valid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as test_file:
            json.dump({"test": "value"}, test_file)
            test_file_path = test_file.name

        # Create a schema file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump({"type": "object", "properties": {"test": {"type": "string"}}}, schema_file)
            schema_file_path = schema_file.name

        try:
            # Setup mock
            mock_get_schema_path.return_value = schema_file_path
            
            # Run the command
            result = runner.invoke(app, ["schema", test_file_path])
            
            # Check that the command succeeded
            assert result.exit_code == 0
            assert "✓ JSON file validates against schema" in result.stdout
        finally:
            # Clean up
            os.unlink(test_file_path)
            os.unlink(schema_file_path)
    
    @patch('src.cli.validate.main.config.get_schema_path')
    @patch('jsonschema.validate')
    def test_validation_with_warnings(self, mock_validate, mock_get_schema_path):
        """Test validation with warnings"""
        # Create a JSON file with empty values
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as test_file:
            json.dump({"test": "", "tags": []}, test_file)
            test_file_path = test_file.name

        # Create a schema file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump({
                "type": "object",
                "properties": {
                    "test": {"type": "string"},
                    "tags": {"type": "array"}
                }
            }, schema_file)
            schema_file_path = schema_file.name

        try:
            # Setup mock
            mock_get_schema_path.return_value = schema_file_path
            
            # Run the command
            result = runner.invoke(app, ["schema", test_file_path])
            
            # Check that the command succeeded with warnings
            assert result.exit_code == 0
            assert "⚠" in result.stdout  # Warning symbol
            assert "empty" in result.stdout.lower()
        finally:
            # Clean up
            os.unlink(test_file_path)
            os.unlink(schema_file_path)
    
    @patch('src.cli.validate.main.config.get_schema_path')
    @patch('jsonschema.validate')
    def test_validation_with_errors(self, mock_validate, mock_get_schema_path):
        """Test validation with errors"""
        # Create a JSON file with invalid data type
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as test_file:
            json.dump({"test": 123}, test_file)  # Integer instead of string
            test_file_path = test_file.name

        # Create a schema file that requires strings
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump({
                "type": "object",
                "properties": {
                    "test": {"type": "string"}
                }
            }, schema_file)
            schema_file_path = schema_file.name

        try:
            # Setup mock
            mock_get_schema_path.return_value = schema_file_path
            
            # Create an error to be raised by jsonschema.validate
            validation_error = jsonschema.exceptions.ValidationError("Validation error")
            validation_error.path = ["test"]
            validation_error.schema_path = ["properties", "test", "type"]
            mock_validate.side_effect = validation_error
            
            # Run the command
            result = runner.invoke(app, ["schema", test_file_path])
            
            # Check that the command failed with validation error
            assert result.exit_code == 1
            assert "✗ JSON file does not validate against schema" in result.stdout
            assert "Validation error" in result.stdout
        finally:
            # Clean up
            os.unlink(test_file_path)
            os.unlink(schema_file_path)
    
    @patch('src.cli.validate.main.config.get_schema_path')
    def test_strict_validation(self, mock_get_schema_path):
        """Test strict validation that fails on warnings"""
        # Create a JSON file with empty values
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as test_file:
            json.dump({"test": "", "tags": []}, test_file)
            test_file_path = test_file.name

        # Create a schema file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump({
                "type": "object",
                "properties": {
                    "test": {"type": "string"},
                    "tags": {"type": "array"}
                }
            }, schema_file)
            schema_file_path = schema_file.name

        try:
            # Setup mock
            mock_get_schema_path.return_value = schema_file_path
            
            # Run the command with strict mode enabled
            with patch('jsonschema.validate'):  # Mock validate to prevent actual validation
                result = runner.invoke(app, ["schema", test_file_path, "--strict"])
                
                # Check that the command failed due to strict mode
                assert result.exit_code == 1
                assert "strict mode" in result.stdout.lower()
        finally:
            # Clean up
            os.unlink(test_file_path)
            os.unlink(schema_file_path)

class TestImageValidation:
    """Tests for the image validation command"""
    
    def test_images_not_exist(self):
        """Test validation with non-existent images"""
        # Run the command with non-existent images
        result = runner.invoke(app, ["images", "/nonexistent/image1.jpg", "/nonexistent/image2.jpg"])
        
        # Check that the command failed with appropriate error message
        assert result.exit_code == 1
        assert "Error: Image does not exist" in result.stdout
    
    def test_pixel_comparison_identical(self):
        """Test pixel comparison with identical images"""
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            pytest.skip("PIL or numpy not available")
            
        # Create an output directory that will persist during the test
        output_dir = tempfile.mkdtemp(prefix="test_image_diff_")
        
        try:
            # Create two identical test images
            test_img1 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            test_img2 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            
            # Create a simple array for a 2x2 image
            img_array = np.zeros((2, 2, 3), dtype=np.uint8)
            img_array[:, :] = [255, 0, 0]  # Red image
            
            # Convert to PIL image and save
            img1 = Image.fromarray(img_array)
            img2 = Image.fromarray(img_array)
            img1.save(test_img1.name)
            img2.save(test_img2.name)
            
            # Mock only pixelmatch to control the comparison result
            with patch('pixelmatch.contrib.PIL.pixelmatch', return_value=0):
                # Run the command with output dir
                result = runner.invoke(app, ["images", test_img1.name, test_img2.name, "--output", output_dir])
                
                # Check that the command succeeded
                assert result.exit_code == 0, f"Command failed with output: {result.stdout}"
                assert "pixel-perfect matches" in result.stdout
                
                # Verify the diff image exists in the output directory
                diff_path = os.path.join(output_dir, "pixel_diff.png")
                assert os.path.exists(diff_path), "Diff image was not created"
        finally:
            # Clean up temporary files and directory
            os.unlink(test_img1.name)
            os.unlink(test_img2.name)
            shutil.rmtree(output_dir, ignore_errors=True)
    
    def test_pixel_comparison_similar(self):
        """Test pixel comparison with similar but not identical images"""
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            pytest.skip("PIL or numpy not available")
        
        # Create an output directory that will persist during the test
        output_dir = tempfile.mkdtemp(prefix="test_image_diff_")
        
        try:
            # Create two similar but not identical real images
            test_img1 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            test_img2 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            
            # Create arrays for 10x10 images
            img1_array = np.zeros((10, 10, 3), dtype=np.uint8)
            img2_array = np.zeros((10, 10, 3), dtype=np.uint8)
            
            # Make first image red
            img1_array[:, :] = [255, 0, 0]  
            
            # Make second image red with a blue stripe (3% difference)
            img2_array[:, :] = [255, 0, 0]
            img2_array[0:3, :] = [0, 0, 255]  # Blue stripe at top
            
            # Create and save real PIL images
            img1 = Image.fromarray(img1_array)
            img2 = Image.fromarray(img2_array)
            img1.save(test_img1.name)
            img2.save(test_img2.name)
            
            # Mock only pixelmatch to control the comparison result
            with patch('pixelmatch.contrib.PIL.pixelmatch', return_value=3):
                # Run the command with max difference of 5%
                result = runner.invoke(app, [
                    "images", test_img1.name, test_img2.name,
                    "--max-difference", "5.0",
                    "--output", output_dir
                ])
                
                # Verify success and output messages
                assert result.exit_code == 0, f"Command failed with output: {result.stdout}"
                assert "similar" in result.stdout
                assert "below maximum allowed difference" in result.stdout
                
                # Verify the diff image exists in the output directory
                diff_path = os.path.join(output_dir, "pixel_diff.png")
                assert os.path.exists(diff_path), "Diff image was not created"
        finally:
            # Clean up temporary files and directory
            os.unlink(test_img1.name)
            os.unlink(test_img2.name)
            shutil.rmtree(output_dir, ignore_errors=True)
    
    def test_pixel_comparison_different(self):
        """Test pixel comparison with significantly different images"""
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            pytest.skip("PIL or numpy not available")
            
        # Create an output directory that will persist during the test
        output_dir = tempfile.mkdtemp(prefix="test_image_diff_")
        
        try:
            # Create two very different 10x10 pixel images
            test_img1 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            test_img2 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            
            # Create arrays for 10x10 images
            img1_array = np.zeros((10, 10, 3), dtype=np.uint8)
            img2_array = np.zeros((10, 10, 3), dtype=np.uint8)
            
            # Make first image red
            img1_array[:, :] = [255, 0, 0]  
            
            # Make second image blue (completely different)
            img2_array[:, :] = [0, 0, 255]
            
            # Convert to PIL images and save
            img1 = Image.fromarray(img1_array)
            img2 = Image.fromarray(img2_array)
            img1.save(test_img1.name)
            img2.save(test_img2.name)
            
            # Mock only pixelmatch to control the comparison result - 100% different (100 out of 100 pixels)
            with patch('pixelmatch.contrib.PIL.pixelmatch', return_value=100):
                # Run the command with max difference of 5% and output dir
                result = runner.invoke(app, [
                    "images", test_img1.name, test_img2.name,
                    "--max-difference", "5.0",
                    "--output", output_dir
                ])
                
                # Check that the command failed (above threshold)
                assert result.exit_code == 1
                assert "differ by" in result.stdout
                assert "exceeds maximum allowed difference" in result.stdout
                
                # Verify the diff image exists in the output directory
                diff_path = os.path.join(output_dir, "pixel_diff.png")
                assert os.path.exists(diff_path), "Diff image was not created"
        finally:
            # Clean up temporary files and directory
            os.unlink(test_img1.name)
            os.unlink(test_img2.name)
            shutil.rmtree(output_dir, ignore_errors=True)
    
    def test_hash_comparison(self):
        """Test perceptual hash comparison"""
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            pytest.skip("PIL or numpy not available")
            
        # Create an output directory that will persist during the test
        output_dir = tempfile.mkdtemp(prefix="test_image_diff_")
        
        try:
            # Create two similar images for hash comparison
            test_img1 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            test_img2 = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            
            # Create arrays for 10x10 images
            img1_array = np.zeros((10, 10, 3), dtype=np.uint8)
            img2_array = np.zeros((10, 10, 3), dtype=np.uint8)
            
            # Make first image a red square
            img1_array[:, :] = [255, 0, 0]  
            
            # Make second image a red square with a small blue spot
            img2_array[:, :] = [255, 0, 0]
            img2_array[8:10, 8:10] = [0, 0, 255]  # Blue spot in corner
            
            # Convert to PIL images and save
            img1 = Image.fromarray(img1_array)
            img2 = Image.fromarray(img2_array)
            img1.save(test_img1.name)
            img2.save(test_img2.name)
            
            # Create mock hashes with controlled similarity
            hash1 = MagicMock()
            hash2 = MagicMock()
            hash1.hash = [[0, 1], [1, 0]]
            hash2.hash = [[0, 1], [0, 0]]
            
            # Configure distance to be 1 out of 4 bits (75% similar)
            hash1.__sub__.return_value = 1
            
            # Mock imagehash.phash to return our controlled hash objects
            with patch('imagehash.phash', side_effect=[hash1, hash2]):
                # Run the command using hash comparison with 50% threshold (should pass)
                result = runner.invoke(app, [
                    "images", test_img1.name, test_img2.name,
                    "--method", "hash",
                    "--threshold", "0.5",  # Allow up to 50% difference
                    "--output", output_dir
                ])
                
                # Check that the command succeeded (75% similar, above 50% threshold)
                assert result.exit_code == 0, f"Command failed with output: {result.stdout}"
                assert "perceptually similar" in result.stdout
                
                # Verify results were saved to the output directory
                result_file = os.path.join(output_dir, "comparison_result.json")
                assert os.path.exists(result_file), "Result file was not created"
        finally:
            # Clean up temporary files and directory
            os.unlink(test_img1.name)
            os.unlink(test_img2.name)
            shutil.rmtree(output_dir, ignore_errors=True)

class TestRunValidation:
    """Tests for the run command that performs validation on artifact directories"""
    
    def test_artifact_dir_not_exists(self):
        """Test validation with a non-existent artifact directory"""
        # Run the command with a non-existent directory
        result = runner.invoke(app, ["run", "/nonexistent/dir"])
        
        # Check that the command failed with appropriate error message
        assert result.exit_code == 1
        assert "Error: Artifact directory does not exist" in result.stdout
    
    def test_no_json_files(self):
        """Test validation with no JSON files in the directory"""
        # Create a temporary directory with a non-JSON file
        with tempfile.TemporaryDirectory() as artifact_dir, \
             tempfile.TemporaryDirectory() as output_dir, \
             patch('src.cli.validate.main.config.get_schema_path', return_value=None), \
             patch('time.time', return_value=1234567890.0), \
             patch('platform.platform', return_value="Linux-test"), \
             patch('platform.python_version', return_value="3.10.0"):
             
            # Create a text file (not JSON)
            with open(os.path.join(artifact_dir, "file.txt"), 'w') as f:
                f.write("This is not a JSON file")
                
            # There should be no JSON files in the directory
            
            # Run the validation command
            result = runner.invoke(app, ["run", artifact_dir, "--output", output_dir])
            
            # Check for warning about no JSON files
            assert result.exit_code == 0  # Should succeed but show warning
            assert "Warning: No JSON files found" in result.stdout
            
            # Verify that environment info was written
            env_file = os.path.join(output_dir, "validation_environment.json")
            assert os.path.exists(env_file), "Environment file was not created"
            
            # Verify that the summary was written
            summary_file = os.path.join(output_dir, "validation_summary.json")
            assert os.path.exists(summary_file), "Summary file was not created"
    
    def test_successful_validation(self):
        """Test successful validation of multiple JSON files"""
        # Create temporary directories
        with tempfile.TemporaryDirectory() as artifact_dir, \
             tempfile.TemporaryDirectory() as output_dir, \
             tempfile.TemporaryDirectory() as schema_dir, \
             patch('src.cli.validate.main.config.get_schema_path') as mock_get_schema_path, \
             patch('time.time', return_value=1234567890.0), \
             patch('platform.platform', return_value="Linux-test"), \
             patch('platform.python_version', return_value="3.10.0"):
             
            # Create a schema file
            schema_file = os.path.join(schema_dir, "schema.json")
            with open(schema_file, 'w') as f:
                json.dump({"type": "object", "properties": {"test": {"type": "string"}}}, f)
                
            # Point the schema path to our schema file
            mock_get_schema_path.return_value = schema_file
            
            # Create two JSON files in the artifact directory
            file1_path = os.path.join(artifact_dir, "file1.json")
            file2_path = os.path.join(artifact_dir, "file2.json")
            
            with open(file1_path, 'w') as f:
                json.dump({"test": "value1"}, f)
                
            with open(file2_path, 'w') as f:
                json.dump({"test": "value2"}, f)
            
            # Run the validation command with jsonschema.validate mocked to avoid external dependency
            with patch('jsonschema.validate'):
                result = runner.invoke(app, ["run", artifact_dir, "--output", output_dir])
                
                # Check that the command succeeded
                assert result.exit_code == 0, f"Command failed with output: {result.stdout}"
                assert "Validation Results: 2 passed, 0 failed" in result.stdout
                
                # Verify that summary was written
                summary_file = os.path.join(output_dir, "validation_summary.json")
                assert os.path.exists(summary_file), "Summary file was not created"
                
                # Verify the summary content
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                    assert summary["total_files"] == 2
                    assert summary["passed"] == 2
                    assert summary["failed"] == 0

class TestManifestValidation:
    """Tests for the manifest validation command"""
    
    def test_manifest_file_not_exists(self):
        """Test validation with a non-existent manifest file"""
        # Run the command with a non-existent file
        result = runner.invoke(app, ["manifest", "/nonexistent/manifest.json"])
        
        # Check that the command failed with appropriate error message
        assert result.exit_code == 1
        assert "Error: Manifest file does not exist" in result.stdout
    
    def test_invalid_manifest_structure(self):
        """Test validation with an invalid manifest structure"""
        # Create a temporary file with an invalid manifest (a list not a dict)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as manifest_file:
            json.dump(["not", "a", "dict"], manifest_file)  # Invalid structure (list not dict)
            manifest_path = manifest_file.name
        
        try:
            # Run the command with the invalid manifest
            result = runner.invoke(app, ["manifest", manifest_path])
            
            # Check that the command failed with appropriate error message
            assert result.exit_code == 1, f"Command should fail but got: {result.stdout}"
            assert "Error: Manifest must be a JSON object" in result.stdout
        finally:
            # Clean up
            os.unlink(manifest_path)
    
    def test_missing_required_fields(self):
        """Test validation with a manifest missing required fields"""
        # Create a temporary file with a manifest missing required fields
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as manifest_file:
            json.dump({"incomplete": "manifest"}, manifest_file)  # Missing timestamp, version, artifacts
            manifest_path = manifest_file.name
        
        try:
            # Run the command with the incomplete manifest
            result = runner.invoke(app, ["manifest", manifest_path])
            
            # Check that the command failed with appropriate error message
            assert result.exit_code == 1, f"Command should fail but got: {result.stdout}"
            assert "Error: Missing required fields" in result.stdout
        finally:
            # Clean up
            os.unlink(manifest_path)
    
    def test_successful_validation(self):
        """Test successful validation of a manifest file"""
        # Create a temporary directory for artifacts and the manifest
        with tempfile.TemporaryDirectory() as artifact_dir:
            # Create test artifacts referenced by the manifest
            json_artifact = os.path.join(artifact_dir, "artifact1.json")
            image_artifact = os.path.join(artifact_dir, "artifact2.jpg")
            
            # Create a JSON artifact
            with open(json_artifact, 'w') as f:
                json.dump({"test": "value"}, f)
                
            # Create a simple image artifact
            try:
                from PIL import Image
                import numpy as np
                
                # Create a 2x2 red image
                img_array = np.zeros((2, 2, 3), dtype=np.uint8)
                img_array[:, :] = [255, 0, 0]  # Red
                
                img = Image.fromarray(img_array)
                img.save(image_artifact)
            except ImportError:
                # If PIL/numpy aren't available, create a dummy image file
                with open(image_artifact, 'wb') as f:
                    f.write(b'DUMMY IMAGE')
            
            # Create a valid manifest file
            manifest_path = os.path.join(artifact_dir, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump({
                    "timestamp": "2023-01-01T12:00:00Z",
                    "version": "1.0",
                    "artifacts": [
                        {"path": json_artifact, "type": "json"},
                        {"path": image_artifact, "type": "image"}
                    ]
                }, f)
            
            # Run the command with the valid manifest
            result = runner.invoke(app, ["manifest", manifest_path])
            
            # Check that the command succeeded
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"
            assert "All artifacts validated successfully" in result.stdout
            assert "Artifacts: 2 found, 0 missing" in result.stdout

if __name__ == "__main__":
    pytest.main(["-v", __file__])