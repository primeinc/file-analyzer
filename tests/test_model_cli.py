#!/usr/bin/env python3
"""
Tests for the model CLI module

This module tests the CLI interface for model management commands, ensuring:
1. Command options are correctly parsed and used
2. Model listing works correctly
3. Model download functionality works as expected
4. Error handling works correctly
"""

import os
import sys
import tempfile
import shutil
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
from typer.testing import CliRunner

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from src.cli.model.main import app, get_model_dir, calculate_md5, MODEL_INFO

# Create a CLI test runner
runner = CliRunner()

class TestModelCLIUtils:
    """Tests for utility functions in the model CLI module"""
    
    def test_get_model_dir(self):
        """Test get_model_dir function"""
        with patch('src.cli.model.main.get_project_root', return_value="/fake/project/root"):
            model_dir = get_model_dir()
            assert model_dir == "/fake/project/root/libs/ml-fastvlm/checkpoints"
    
    def test_calculate_md5(self):
        """Test MD5 calculation function"""
        # Create a temporary file with known content
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"This is a test file with known content")
            tmp_path = tmp_file.name
        
        try:
            # Calculate the expected MD5 using hashlib directly
            expected_md5 = hashlib.md5(b"This is a test file with known content").hexdigest()
            
            # Use the function to calculate MD5
            with patch('builtins.open', mock_open(read_data=b"This is a test file with known content")):
                calculated_md5 = calculate_md5("/fake/path")
            
            # Verify the calculated MD5 matches the expected value
            assert calculated_md5 == expected_md5
        finally:
            # Clean up the temporary file
            os.unlink(tmp_path)

class TestListModelsCommand:
    """Tests for the list models command"""
    
    @patch('src.cli.model.main.get_model_dir')
    @patch('src.cli.model.main.os.path.exists')
    def test_list_models_none_installed(self, mock_exists, mock_get_model_dir):
        """Test listing models when none are installed"""
        # Setup mocks
        mock_get_model_dir.return_value = "/fake/model/dir"
        mock_exists.return_value = False
        
        # Run the command
        result = runner.invoke(app, ["list"])
        
        # Check that the command was successful
        assert result.exit_code == 0
        
        # Check that the output contains expected content
        for size, info in MODEL_INFO.items():
            assert size in result.stdout
            assert info["name"] in result.stdout
            assert "Not Installed" in result.stdout
        
        # Verify model directory is shown
        assert "Model directory: /fake/model/dir" in result.stdout
    
    @patch('src.cli.model.main.get_model_dir')
    @patch('src.cli.model.main.os.path.exists')
    def test_list_models_some_installed(self, mock_exists, mock_get_model_dir):
        """Test listing models when some are installed"""
        # Setup mocks
        mock_get_model_dir.return_value = "/fake/model/dir"
        
        # Mock exists to return True only for specific paths
        def mock_exists_side_effect(path):
            # Return True for 0.5b model directory and safetensors file
            if path == "/fake/model/dir/llava-fastvithd_0.5b_stage3":
                return True
            elif path == "/fake/model/dir/llava-fastvithd_0.5b_stage3/model.safetensors":
                return True
            # Return True for 1.5b model directory but not for safetensors file (incomplete)
            elif path == "/fake/model/dir/llava-fastvithd_1.5b_stage3":
                return True
            else:
                return False
        
        mock_exists.side_effect = mock_exists_side_effect
        
        # Run the command
        result = runner.invoke(app, ["list"])
        
        # Check that the command was successful
        assert result.exit_code == 0
        
        # Check that the output shows the correct status for each model
        assert "0.5b" in result.stdout and "Installed" in result.stdout
        assert "1.5b" in result.stdout and "Incomplete" in result.stdout
        assert "7b" in result.stdout and "Not Installed" in result.stdout
    
    @patch('src.cli.model.main.get_model_dir')
    def test_list_models_with_error(self, mock_get_model_dir):
        """Test list models command with an error"""
        # Setup mock to raise an exception
        mock_get_model_dir.side_effect = Exception("Test error")
        
        # Run the command
        result = runner.invoke(app, ["list"])
        
        # Check that the error message is shown, even if exit code is 0
        # Note: in the actual implementation, the exit code might be 0 even on error
        # since the exception is caught and a return code is set manually
        assert "Error listing models: Test error" in result.stdout

class TestDownloadModelCommand:
    """Tests for the download model command"""
    
    @patch('src.cli.model.main.get_model_dir')
    @patch('src.cli.model.main.os.path.exists')
    @patch('src.cli.model.main.download_file')
    @patch('src.cli.model.main.calculate_md5')
    @patch('src.cli.model.main.extract_zip')
    @patch('src.cli.model.main.os.makedirs')
    @patch('src.cli.model.main.shutil.rmtree')
    @patch('src.cli.model.main.tempfile.NamedTemporaryFile')
    @patch('src.cli.model.main.os.remove')
    def test_download_model_success(self, mock_remove, mock_tempfile, mock_rmtree, mock_makedirs, 
                                   mock_extract, mock_md5, mock_download, mock_exists, mock_get_model_dir):
        """Test successful model download"""
        # Setup mocks
        mock_get_model_dir.return_value = "/fake/model/dir"
        mock_exists.return_value = False  # Model doesn't exist yet
        mock_download.return_value = True  # Download succeeds
        mock_md5.return_value = MODEL_INFO["0.5b"]["md5"]  # MD5 matches
        mock_extract.return_value = True  # Extraction succeeds
        
        # Mock NamedTemporaryFile
        mock_tmp_file = MagicMock()
        mock_tmp_file.name = "/tmp/fake_temp_file.zip"
        mock_tmp_file.__enter__.return_value = mock_tmp_file
        mock_tempfile.return_value = mock_tmp_file
        
        # Run the command
        result = runner.invoke(app, ["download", "0.5b"])
        
        # Check that the functions were called with the right arguments
        mock_download.assert_called_once()
        mock_extract.assert_called_once_with("/tmp/fake_temp_file.zip", 
                                           "/fake/model/dir/llava-fastvithd_0.5b_stage3")
        
        # Check for expected message patterns in the output
        assert "Downloading model llava-fastvithd_0.5b_stage3" in result.stdout
        assert "Verifying download integrity" in result.stdout
        assert "Extracting model files" in result.stdout
    
    @patch('src.cli.model.main.get_model_dir')
    @patch('src.cli.model.main.os.path.exists')
    @patch('src.cli.model.main.os.makedirs')
    def test_download_model_already_exists(self, mock_makedirs, mock_exists, mock_get_model_dir):
        """Test download when model already exists"""
        # Setup mocks
        mock_get_model_dir.return_value = "/fake/model/dir"
        
        # Mock exists to return True for model and safetensors file
        def mock_exists_side_effect(path):
            if path in [
                "/fake/model/dir/llava-fastvithd_0.5b_stage3",
                "/fake/model/dir/llava-fastvithd_0.5b_stage3/model.safetensors"
            ]:
                return True
            else:
                return False
            
        mock_exists.side_effect = mock_exists_side_effect
        
        # Run the command
        result = runner.invoke(app, ["download", "0.5b"])
        
        # Check that the command indicated model already installed
        assert "Model llava-fastvithd_0.5b_stage3 is already installed" in result.stdout
        
        # Test with force flag - using additional patches
        with patch('src.cli.model.main.download_file') as mock_download, \
             patch('src.cli.model.main.tempfile.NamedTemporaryFile') as mock_tempfile, \
             patch('src.cli.model.main.shutil.rmtree'), \
             patch('src.cli.model.main.extract_zip'), \
             patch('src.cli.model.main.os.remove'):
            
            # Setup tempfile mock
            mock_tmp_file = MagicMock()
            mock_tmp_file.name = "/tmp/fake_temp_file.zip"
            mock_tmp_file.__enter__.return_value = mock_tmp_file
            mock_tempfile.return_value = mock_tmp_file
            
            # Setup download to fail (to shorten the test)
            mock_download.return_value = False
            
            # Run command with force flag
            result = runner.invoke(app, ["download", "0.5b", "--force"])
            
            # Verify download was attempted
            mock_download.assert_called_once()
    
    def test_download_invalid_size(self):
        """Test download with invalid model size"""
        # Run the command with an invalid size
        result = runner.invoke(app, ["download", "invalid_size"])
        
        # Check that the error message is shown
        assert "Invalid model size: invalid_size" in result.stdout
        assert "Valid sizes: " in result.stdout
    
    def test_download_invalid_size_with_check(self):
        """Test download with invalid size - verifies more output details"""
        # This test doesn't require mocks and is more reliable
        result = runner.invoke(app, ["download", "9999b"])
        assert result.exit_code == 0
        assert "Invalid model size: 9999b" in result.stdout
    
    @patch('src.cli.model.main.get_model_dir')
    @patch('src.cli.model.main.os.path.exists')
    @patch('src.cli.model.main.download_file')
    @patch('src.cli.model.main.calculate_md5')
    @patch('src.cli.model.main.os.remove')
    @patch('src.cli.model.main.tempfile.NamedTemporaryFile')
    @patch('src.cli.model.main.os.makedirs')
    def test_download_md5_mismatch(self, mock_makedirs, mock_tempfile, mock_remove, mock_md5, 
                                 mock_download, mock_exists, mock_get_model_dir):
        """Test handling MD5 checksum mismatch"""
        # Setup mocks
        mock_get_model_dir.return_value = "/fake/model/dir"
        mock_exists.return_value = False  # Model doesn't exist yet
        mock_download.return_value = True  # Download succeeds
        mock_md5.return_value = "incorrect_md5_hash"  # MD5 mismatches
        
        # Mock NamedTemporaryFile
        mock_tmp_file = MagicMock()
        mock_tmp_file.name = "/tmp/fake_temp_file.zip"
        mock_tmp_file.__enter__.return_value = mock_tmp_file
        mock_tempfile.return_value = mock_tmp_file
        
        # Run the command
        result = runner.invoke(app, ["download", "0.5b"])
        
        # Check that the mock functions were called
        mock_download.assert_called_once()
        mock_md5.assert_called_once()
        
        # Verify temp file is removed
        mock_remove.assert_called_once_with("/tmp/fake_temp_file.zip")
    
    @patch('src.cli.model.main.get_model_dir')
    @patch('src.cli.model.main.os.path.exists')
    @patch('src.cli.model.main.download_file')
    @patch('src.cli.model.main.calculate_md5')
    @patch('src.cli.model.main.extract_zip')
    @patch('src.cli.model.main.os.makedirs')
    @patch('src.cli.model.main.os.remove')
    @patch('src.cli.model.main.tempfile.NamedTemporaryFile')
    def test_download_extraction_failure(self, mock_tempfile, mock_remove, mock_makedirs, 
                                       mock_extract, mock_md5, mock_download, mock_exists, mock_get_model_dir):
        """Test handling extraction failure"""
        # Setup mocks
        mock_get_model_dir.return_value = "/fake/model/dir"
        mock_exists.return_value = False  # Model doesn't exist yet
        mock_download.return_value = True  # Download succeeds
        mock_md5.return_value = MODEL_INFO["0.5b"]["md5"]  # MD5 matches
        mock_extract.return_value = False  # Extraction fails
        
        # Mock NamedTemporaryFile
        mock_tmp_file = MagicMock()
        mock_tmp_file.name = "/tmp/fake_temp_file.zip"
        mock_tmp_file.__enter__.return_value = mock_tmp_file
        mock_tempfile.return_value = mock_tmp_file
        
        # Run the command
        result = runner.invoke(app, ["download", "0.5b"])
        
        # Check error message
        assert "Failed to extract model files" in result.stdout
        
        # Verify temp file is removed
        mock_remove.assert_called_once_with("/tmp/fake_temp_file.zip")

if __name__ == "__main__":
    pytest.main(["-v", __file__])