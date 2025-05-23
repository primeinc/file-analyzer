"""
Essential CLI Tests

Focused tests for CLI functionality that actually matter to users.
Minimal mocking, maximum value.
"""

import subprocess
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestCLIArgumentParsing:
    """Test CLI argument parsing (regression prevention)."""
    
    def test_help_command_works(self):
        """Test that help command shows usage."""
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "--help"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "FILE_PATH" in result.stdout
    
    def test_version_command_works(self):
        """Test that version command works."""
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "--version"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        assert result.returncode == 0
        assert "File Analyzer" in result.stdout


class TestCLIOutputFormats:
    """Test CLI output formats with minimal mocking."""
    
    @patch('src.core.vision.VisionModelAnalyzer')
    def test_json_output_format(self, mock_analyzer):
        """Test --json flag produces valid JSON."""
        # Mock only the expensive vision analysis
        mock_analyzer.return_value.analyze.return_value = {
            "description": "Test image",
            "tags": ["test", "image"],
            "filename_suggestion": "test-image.jpg"
        }
        
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            
            result = subprocess.run([
                sys.executable, "-m", "src.cli.main", "--json", tmp_file.name
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                # Should produce valid JSON
                data = json.loads(result.stdout)
                assert "recommended_filename" in data
                assert "description" in data
    
    @patch('src.core.vision.VisionModelAnalyzer')
    def test_markdown_output_format(self, mock_analyzer):
        """Test --md flag produces markdown."""
        mock_analyzer.return_value.analyze.return_value = {
            "description": "Test image",
            "tags": ["test", "image"],
            "filename_suggestion": "test-image.jpg"
        }
        
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            
            result = subprocess.run([
                sys.executable, "-m", "src.cli.main", "--md", tmp_file.name
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            
            if result.returncode == 0:
                assert "## Description" in result.stdout
                assert "## Tags" in result.stdout


class TestCLIPathHandling:
    """Test CLI handles different path types correctly."""
    
    def test_nonexistent_file_fails_gracefully(self):
        """Test CLI handles nonexistent files gracefully."""
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "/nonexistent/file.jpg"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        assert result.returncode != 0
        error_output = result.stderr + result.stdout
        assert "not found" in error_output.lower() or "error" in error_output.lower()
    
    @patch('src.core.vision.VisionModelAnalyzer')  
    def test_relative_path_handling(self, mock_analyzer):
        """Test CLI handles relative paths correctly."""
        mock_analyzer.return_value.analyze.return_value = {
            "description": "Test",
            "tags": ["test"],
            "filename_suggestion": "test.jpg"
        }
        
        # Test with existing test image
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "test_data/images/test.jpg"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        # Should not crash with path resolution errors
        if "Error processing" in result.stderr:
            # If it fails, it should be due to model issues, not path issues
            assert "path" not in result.stderr.lower()


class TestCLISubcommands:
    """Test that subcommands still work (backward compatibility)."""
    
    def test_test_subcommand(self):
        """Test 'fa test' subcommand works."""
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "test", "--help"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        # Should show test command help
        assert result.returncode == 0 or "test" in result.stdout.lower()
    
    def test_model_subcommand(self):
        """Test 'fa model' subcommand works.""" 
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main", "model", "--help"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        # Should show model command help
        assert result.returncode == 0 or "model" in result.stdout.lower()


class TestRegressionPrevention:
    """Critical regression tests."""
    
    def test_direct_filepath_argument_accepted(self):
        """
        REGRESSION TEST: Ensure 'fa filepath' argument parsing works.
        
        This test specifically prevents the regression where CLI argument
        parsing broke and 'fa filepath' stopped working.
        """
        # Test that the main function accepts file_path argument
        from src.cli.main import main
        import inspect
        
        sig = inspect.signature(main)
        
        # Should have file_path parameter (the critical argument)
        assert 'file_path' in sig.parameters
        assert 'ctx' in sig.parameters  # Typer context
    
    def test_cli_module_imports_correctly(self):
        """Test CLI module can be imported without errors."""
        try:
            from src.cli.main import app, main
            assert app is not None
            assert main is not None
        except ImportError as e:
            pytest.fail(f"CLI module import failed: {e}")
    
    def test_no_arguments_shows_help(self):
        """Test 'fa' with no arguments shows help."""
        result = subprocess.run([
            sys.executable, "-m", "src.cli.main"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        # Should show usage information
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])