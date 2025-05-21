#!/usr/bin/env python3
"""
Tests for the analyze CLI module

This module tests the CLI interface for file analysis commands, ensuring:
1. Command options are correctly parsed and passed to the FileAnalyzer
2. Results are properly processed and displayed
3. Error handling works correctly
4. All analysis types (metadata, duplicates, etc.) function as expected
"""

import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

import pytest
from typer.testing import CliRunner

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from src.cli.analyze.main import app, create_options_dict, AnalyzeState
from src.core.analyzer import FileAnalyzer

# Create a CLI test runner
runner = CliRunner()

# Helper function to create a mock FileAnalyzer class
def create_mock_analyzer_class(success=True, results=None):
    """Create a mock FileAnalyzer for testing"""
    if results is None:
        results = {}
    
    class MockFileAnalyzer:
        def __init__(self, config=None):
            self.config = config or {}
            self.results = results
        
        def analyze(self, path, options):
            # Store the options for later inspection in tests
            self.last_path = path
            self.last_options = options
            
            # Return either success or failure results
            if success:
                return self._create_success_results()
            else:
                return {"error": "Analysis failed"}
        
        def _create_success_results(self):
            # Create a results dictionary based on the last_options
            analyses = {}
            
            # Add metadata results if requested
            if self.last_options.get('metadata'):
                analyses['metadata'] = {
                    "status": "success",
                    "file": "/test/path/metadata.json",
                    "count": 10
                }
            
            # Add duplicates results if requested
            if self.last_options.get('duplicates'):
                analyses['duplicates'] = {
                    "status": "success",
                    "file": "/test/path/duplicates.txt"
                }
            
            # Add OCR results if requested
            if self.last_options.get('ocr'):
                analyses['ocr'] = {
                    "status": "success",
                    "file": "/test/path/ocr_results.json",
                    "total": 5,
                    "successful": 4,
                    "failed": 1
                }
            
            # Add virus scan results if requested
            if self.last_options.get('virus'):
                analyses['virus'] = {
                    "status": "clean",
                    "file": "/test/path/malware_scan.txt",
                    "summary": {
                        "files_scanned": 100,
                        "threats_found": 0
                    }
                }
            
            # Add search results if requested
            if self.last_options.get('search'):
                analyses['search'] = {
                    "status": "success",
                    "file": "/test/path/search_results.txt",
                    "pattern": self.last_options.get('search_text', ''),
                    "matches": 5
                }
            
            # Add binary analysis results if requested
            if self.last_options.get('binary'):
                analyses['binary'] = {
                    "status": "success",
                    "file": "/test/path/binary_analysis.txt",
                    "interesting_data": True
                }
            
            # Add vision analysis results if requested
            if self.last_options.get('vision'):
                analyses['vision'] = {
                    "status": "success",
                    "output_dir": "/test/path/vision",
                    "files_processed": 5,
                    "successful": 5,
                    "failed": 0
                }
            
            return {"analyses": analyses}
    
    return MockFileAnalyzer

class TestOptionsGeneration:
    """Tests for the options dictionary generation functionality"""
    
    def test_create_options_dict_basic(self):
        """Test creating a basic options dictionary"""
        options = create_options_dict('metadata')
        
        # Check that only metadata is enabled
        assert options['metadata'] is True
        assert options['duplicates'] is False
        assert options['ocr'] is False
        assert options['virus'] is False
        assert options['search'] is False
        assert options['binary'] is False
        assert options['vision'] is False
    
    def test_create_options_with_results_dir(self):
        """Test creating options with results_dir"""
        results_dir = "/test/path"
        options = create_options_dict('metadata', results_dir=results_dir)
        
        assert options['results_dir'] == results_dir
    
    def test_create_options_with_search_text(self):
        """Test creating options with search text"""
        search_text = "test text"
        options = create_options_dict('search', search_text=search_text)
        
        assert options['search'] is True
        assert options['search_text'] == search_text
    
    def test_create_options_with_vision_settings(self):
        """Test creating options with vision settings"""
        options = create_options_dict('vision', model_name="fastvlm", 
                                     model_size="1.5b", model_mode="detect")
        
        assert options['vision'] is True
        assert options['model'] is True
        assert options['model_type'] == "vision"
        assert options['model_name'] == "fastvlm"
        assert options['model_size'] == "1.5b"
        assert options['model_mode'] == "detect"

class TestAnalyzeAllCommand:
    """Tests for the 'analyze all' command"""
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_all_command_basic(self, mock_analyzer_class):
        """Test basic all command functionality"""
        # Set up mock analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "analyses": {
                "metadata": {"status": "success", "file": "/test/path/metadata.json"},
                "duplicates": {"status": "success", "file": "/test/path/duplicates.txt"},
                "ocr": {"status": "success", "file": "/test/path/ocr_results.json"},
                "virus": {"status": "success", "file": "/test/path/malware_scan.txt"},
                "search": {"status": "success", "file": "/test/path/search_results.txt"},
                "binary": {"status": "success", "file": "/test/path/binary_analysis.txt"},
                "vision": {"status": "success", "output_dir": "/test/path/vision"}
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Run the command with the test directory
            result = runner.invoke(app, ["all", tmp_dir])
            
            # Check that the command was successful
            assert result.exit_code == 0
            
            # Check that FileAnalyzer was initialized correctly
            mock_analyzer_class.assert_called_once()
            
            # Check that analyze was called with the right args
            mock_analyzer.analyze.assert_called_once()
            
            # Check path argument
            args, kwargs = mock_analyzer.analyze.call_args
            assert args[0] == tmp_dir
            
            # Check that options enable all analysis types
            options = args[1]
            assert options['metadata'] is True
            assert options['duplicates'] is True
            assert options['ocr'] is True
            assert options['virus'] is True
            assert options['binary'] is True
            assert options['vision'] is True
            
            # Check output contains expected text
            assert "Analysis Complete" in result.stdout
            assert "Results path:" in result.stdout
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_all_command_with_options(self, mock_analyzer_class):
        """Test all command with various options"""
        # Setup mock analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "analyses": {
                "metadata": {"status": "success", "file": "/test/path/metadata.json"},
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Run command with options
            # Note: The typer application expects --include and --exclude to be repeated, not passed as multiple values
            result = runner.invoke(app, [
                "all", tmp_dir,
                "--results", "/custom/results",
                "--include", "*.jpg", "--include", "*.png",
                "--exclude", "*.tmp",
                "--max-files", "100",
                "--verbose"
            ])
            
            # Check success
            assert result.exit_code == 0
            
            # Verify options were passed correctly
            mock_analyzer_class.assert_called_once()
            args, kwargs = mock_analyzer_class.call_args
            
            # Check config was set correctly
            config = args[0]
            assert config["max_metadata_files"] == 100
            assert "*.jpg" in config["default_include_patterns"]
            assert "*.png" in config["default_include_patterns"]
            assert "*.tmp" in config["default_exclude_patterns"]
    
    @patch('src.cli.analyze.main.os.path.exists')
    def test_all_command_nonexistent_path(self, mock_exists):
        """Test all command with a non-existent path"""
        # Setup mock
        mock_exists.return_value = False
        
        # Try to run with a non-existent path
        result = runner.invoke(app, ["all", "/nonexistent/path"])
        
        # Check that the command failed
        assert result.exit_code == 1
        assert "Error: Path does not exist" in result.stdout

class TestMetadataCommand:
    """Tests for the 'analyze metadata' command"""
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_metadata_command_basic(self, mock_analyzer_class):
        """Test basic metadata command functionality"""
        # Setup mock
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "metadata": {
                "status": "success",
                "file": "/test/path/metadata.json",
                "count": 10
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Run the command
            result = runner.invoke(app, ["metadata", tmp_dir])
            
            # Check success
            assert result.exit_code == 0
            
            # Check output contains expected text
            assert "Metadata extraction complete" in result.stdout
            assert "Found 10 items" in result.stdout
            assert "/test/path/metadata.json" in result.stdout
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_metadata_command_failure(self, mock_analyzer_class):
        """Test metadata command failure handling"""
        # Setup mock for failure
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "metadata": {
                "status": "error",
                "message": "Failed to extract metadata"
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Run the command
            result = runner.invoke(app, ["metadata", tmp_dir])
            
            # Check failure
            assert result.exit_code == 1
            assert "Metadata extraction failed" in result.stdout
            assert "Failed to extract metadata" in result.stdout

class TestDuplicatesCommand:
    """Tests for the 'analyze duplicates' command"""
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_duplicates_command_basic(self, mock_analyzer_class):
        """Test basic duplicates command functionality"""
        # Setup mock
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "duplicates": {
                "status": "success",
                "file": "/test/path/duplicates.txt"
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Run the command
            result = runner.invoke(app, ["duplicates", tmp_dir])
            
            # Check success
            assert result.exit_code == 0
            
            # Check output contains expected text
            assert "Duplicate analysis complete" in result.stdout
            assert "/test/path/duplicates.txt" in result.stdout
    
    @patch('src.cli.analyze.main.os.path.isdir')
    def test_duplicates_command_file_path(self, mock_isdir):
        """Test duplicates command with a file path instead of directory"""
        # Setup mock to indicate it's not a directory
        mock_isdir.return_value = False
        
        # Run the command with a file path
        result = runner.invoke(app, ["duplicates", "/path/to/file.txt"])
        
        # Check failure
        assert result.exit_code == 1
        assert "Error: Path must be a directory" in result.stdout

class TestOCRCommand:
    """Tests for the 'analyze ocr' command"""
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_ocr_command_basic(self, mock_analyzer_class):
        """Test basic OCR command functionality"""
        # Setup mock
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "ocr": {
                "status": "success",
                "file": "/test/path/ocr_results.json",
                "total": 5,
                "successful": 4,
                "failed": 1
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Run the command
            result = runner.invoke(app, ["ocr", tmp_dir])
            
            # Check success
            assert result.exit_code == 0
            
            # Check output contains expected text
            assert "OCR processing complete" in result.stdout
            assert "Processed 5 images" in result.stdout
            assert "Successful: 4, Failed: 1" in result.stdout

class TestSearchCommand:
    """Tests for the 'analyze search' command"""
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_search_command_basic(self, mock_analyzer_class):
        """Test basic search command functionality"""
        # Setup mock
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "search": {
                "status": "success",
                "file": "/test/path/search_results.txt",
                "matches": 5
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Run the command
        result = runner.invoke(app, ["search", "test string", "/test/path"])
        
        # Check success
        assert result.exit_code == 0
        
        # Check output contains expected text
        assert "Search complete: Found 5 matches" in result.stdout
        
        # Verify search text was passed correctly
        mock_analyzer_class.assert_called_once()
        mock_analyzer.analyze.assert_called_once()
        args, kwargs = mock_analyzer.analyze.call_args
        assert args[1]["search_text"] == "test string"
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_search_command_no_matches(self, mock_analyzer_class):
        """Test search command with no matches"""
        # Setup mock with no matches
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "search": {
                "status": "success",
                "file": "/test/path/search_results.txt",
                "matches": 0
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Run the command
        result = runner.invoke(app, ["search", "nonexistent string", "/test/path"])
        
        # Check success (exit code 0 even with no matches)
        assert result.exit_code == 0
        
        # Check output indicates no matches
        assert "Search complete: No matches found" in result.stdout

class TestVisionCommand:
    """Tests for the 'analyze vision' command"""
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_vision_command_basic(self, mock_analyzer_class):
        """Test basic vision command functionality"""
        # Setup mock
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "vision": {
                "status": "success",
                "output_dir": "/test/path/vision",
                "files_processed": 5,
                "successful": 5,
                "failed": 0
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Create a test directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Run the command
            result = runner.invoke(app, ["vision", tmp_dir])
            
            # Check success
            assert result.exit_code == 0
            
            # Check output contains expected text
            assert "Vision analysis complete" in result.stdout
            assert "Processed 5 files" in result.stdout
            assert "Successful: 5, Failed: 0" in result.stdout
    
    @patch('src.cli.analyze.main.FileAnalyzer')
    def test_vision_command_custom_model(self, mock_analyzer_class):
        """Test vision command with custom model settings"""
        # Setup mock
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = {
            "vision": {
                "status": "success",
                "output_path": "/test/path/vision_result.json"
            }
        }
        mock_analyzer_class.return_value = mock_analyzer
        
        # Run the command with custom model settings
        result = runner.invoke(app, [
            "vision", "/test/image.jpg",
            "--model", "bakllava",
            "--size", "7b",
            "--mode", "detect"
        ])
        
        # Check success
        assert result.exit_code == 0
        
        # Verify model settings were passed correctly
        mock_analyzer_class.assert_called_once()
        args, kwargs = mock_analyzer_class.call_args
        
        # Check config contains correct model settings
        config = args[0]
        assert config["vision"]["model"] == "bakllava"
        assert config["vision"]["model_size"] == "7b"
        assert config["vision"]["mode"] == "detect"
        
        # Check analyze call options
        mock_analyzer.analyze.assert_called_once()
        args, kwargs = mock_analyzer.analyze.call_args
        options = args[1]
        assert options["model_name"] == "bakllava"
        assert options["model_size"] == "7b"
        assert options["model_mode"] == "detect"

class TestVerifyCommand:
    """Tests for the 'analyze verify' command"""
    
    @patch('src.cli.analyze.main.verify_installation')
    def test_verify_command(self, mock_verify):
        """Test the verify command"""
        # Setup mock verification results
        mock_verify.return_value = {
            "system": {
                "os": "Linux",
                "python": "3.9.5",
            },
            "core_dependencies": {
                "numpy": "Installed (1.20.3)",
                "requests": "Installed (2.25.1)",
            },
            "external_tools": {
                "exiftool": "Found (12.30)",
                "tesseract": "Found (4.1.1)",
                "missing_tool": "Not found",
            },
            "vision_models": {
                "fastvlm_0.5b": "Available",
                "fastvlm_1.5b": "Not installed",
            }
        }
        
        # Run the command
        result = runner.invoke(app, ["verify"])
        
        # Check success
        assert result.exit_code == 0
        
        # Check output contains expected sections
        assert "System Information" in result.stdout
        assert "Core Dependencies" in result.stdout
        assert "External Tools" in result.stdout
        assert "Vision Models" in result.stdout
        
        # Check specific values are shown
        assert "python: 3.9.5" in result.stdout
        assert "exiftool: Found (12.30)" in result.stdout
        assert "missing_tool: Not found" in result.stdout
        
        # Check warning is shown for missing tools
        assert "Warning: The following external tools are missing" in result.stdout
        assert "- missing_tool" in result.stdout

if __name__ == "__main__":
    pytest.main(["-v", __file__])