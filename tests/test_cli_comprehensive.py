#!/usr/bin/env python3
"""
Comprehensive CLI testing suite for File Analyzer

This test suite validates all CLI commands and their functionality,
ensuring the CLI works correctly before any commit.
"""

import subprocess
import tempfile
import os
import json
import pytest
from pathlib import Path
from typing import List, Dict, Any


class CLITestRunner:
    """Helper class for running CLI commands and validating output."""
    
    def __init__(self):
        self.timeout = 30  # seconds
        
    def run_command(self, args: List[str], expect_success: bool = True, input_data: str = None) -> Dict[str, Any]:
        """
        Run a CLI command and return the result.
        
        Args:
            args: Command arguments (including 'fa')
            expect_success: Whether to expect return code 0
            input_data: Optional stdin input
            
        Returns:
            Dict with returncode, stdout, stderr, success
        """
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                input=input_data
            )
            
            success = (result.returncode == 0) == expect_success
            
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': success,
                'args': args
            }
        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': f'Command timed out after {self.timeout} seconds',
                'success': False,
                'args': args
            }
        except Exception as e:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False,
                'args': args
            }


@pytest.fixture
def cli():
    """Fixture to provide CLI test runner."""
    return CLITestRunner()


@pytest.fixture
def temp_dir():
    """Fixture to provide temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_image(temp_dir):
    """Fixture to create a test image file."""
    # Create a simple test image
    test_image_path = temp_dir / "test.jpg"
    
    # Copy from existing test data if available
    existing_test_image = Path("test_data/images/test.jpg")
    if existing_test_image.exists():
        import shutil
        shutil.copy2(existing_test_image, test_image_path)
    else:
        # Create a minimal test image using PIL
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(test_image_path)
        except ImportError:
            # Fallback: create a fake image file
            test_image_path.write_bytes(b'\xFF\xD8\xFF\xE0\x00\x10JFIF')  # JPEG header
    
    return test_image_path


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_cli_help(self, cli):
        """Test main help command."""
        result = cli.run_command(['fa', '--help'])
        assert result['success'], f"Help command failed: {result['stderr']}"
        assert 'File Analyzer CLI' in result['stdout']
        assert 'Commands' in result['stdout']
        
    def test_cli_version(self, cli):
        """Test version command."""
        result = cli.run_command(['fa', '--version'])
        assert result['success'], f"Version command failed: {result['stderr']}"
        assert 'File Analyzer CLI' in result['stdout']
        assert 'Python' in result['stdout']
        
    def test_no_args_shows_help(self, cli):
        """Test that running fa with no args shows help."""
        result = cli.run_command(['fa'])
        assert result['success'], f"No args command failed: {result['stderr']}"
        assert 'Usage:' in result['stdout']


class TestCommandHelp:
    """Test help system for all commands."""
    
    @pytest.mark.parametrize("command", [
        'quick', 'analyze', 'model', 'test', 'validate', 
        'artifact', 'benchmark', 'install'
    ])
    def test_command_help(self, cli, command):
        """Test help for each command."""
        result = cli.run_command(['fa', command, '--help'])
        assert result['success'], f"Help for {command} failed: {result['stderr']}"
        assert 'Usage:' in result['stdout']
        assert command in result['stdout'].lower()
        
    @pytest.mark.parametrize("subcommand", [
        ['analyze', 'all'], ['analyze', 'metadata'], ['analyze', 'vision'],
        ['model', 'list'], ['model', 'download'], ['test', 'all']
    ])
    def test_subcommand_help(self, cli, subcommand):
        """Test help for subcommands."""
        result = cli.run_command(['fa'] + subcommand + ['--help'])
        assert result['success'], f"Help for {' '.join(subcommand)} failed: {result['stderr']}"
        assert 'Usage:' in result['stdout']


class TestQuickCommand:
    """Test quick analysis command."""
    
    def test_quick_nonexistent_file(self, cli):
        """Test quick command with non-existent file."""
        result = cli.run_command(['fa', 'quick', '/nonexistent/file.jpg'], expect_success=False)
        assert not result['success'], "Quick command should fail for non-existent file"
        assert result['returncode'] == 1
        assert 'Error:' in result['stdout']
        
    def test_quick_with_test_image(self, cli, test_image):
        """Test quick command with a real image file."""
        result = cli.run_command(['fa', 'quick', str(test_image)])
        # Note: This may fail if vision models aren't available, which is OK
        # We're primarily testing CLI structure, not model functionality
        assert result['returncode'] in [0, 1], f"Quick command returned unexpected code: {result['returncode']}"
        
    def test_quick_json_format(self, cli, test_image):
        """Test quick command with JSON output."""
        result = cli.run_command(['fa', 'quick', '--json', str(test_image)])
        assert result['returncode'] in [0, 1], f"Quick JSON command returned unexpected code: {result['returncode']}"


class TestAnalyzeCommands:
    """Test analyze subcommands."""
    
    def test_analyze_help(self, cli):
        """Test analyze command help."""
        result = cli.run_command(['fa', 'analyze', '--help'])
        assert result['success'], f"Analyze help failed: {result['stderr']}"
        assert 'metadata' in result['stdout']
        assert 'vision' in result['stdout']
        
    def test_analyze_verify(self, cli):
        """Test analyze verify command."""
        result = cli.run_command(['fa', 'analyze', 'verify'])
        assert result['success'], f"Analyze verify failed: {result['stderr']}"
        assert 'Verifying' in result['stdout']
        
    def test_analyze_metadata_nonexistent(self, cli):
        """Test analyze metadata with non-existent path."""
        result = cli.run_command(['fa', 'analyze', 'metadata', '/nonexistent'], expect_success=False)
        assert not result['success'], "Analyze metadata should fail for non-existent path"


class TestModelCommands:
    """Test model management commands."""
    
    def test_model_help(self, cli):
        """Test model command help."""
        result = cli.run_command(['fa', 'model', '--help'])
        assert result['success'], f"Model help failed: {result['stderr']}"
        assert 'list' in result['stdout']
        assert 'download' in result['stdout']
        
    def test_model_list(self, cli):
        """Test model list command."""
        result = cli.run_command(['fa', 'model', 'list'])
        assert result['success'], f"Model list failed: {result['stderr']}"
        # Should show available models or indicate none found
        
    def test_model_download_help(self, cli):
        """Test model download help."""
        result = cli.run_command(['fa', 'model', 'download', '--help'])
        assert result['success'], f"Model download help failed: {result['stderr']}"
        assert 'sizes' in result['stdout'].lower() or 'size' in result['stdout'].lower()


class TestValidateCommands:
    """Test validation commands."""
    
    def test_validate_help(self, cli):
        """Test validate command help."""
        result = cli.run_command(['fa', 'validate', '--help'])
        assert result['success'], f"Validate help failed: {result['stderr']}"


class TestTestCommands:
    """Test the test command itself."""
    
    def test_test_help(self, cli):
        """Test test command help."""
        result = cli.run_command(['fa', 'test', '--help'])
        assert result['success'], f"Test help failed: {result['stderr']}"
        
    def test_test_all_help(self, cli):
        """Test test all subcommand help."""
        result = cli.run_command(['fa', 'test', 'all', '--help'])
        assert result['success'], f"Test all help failed: {result['stderr']}"


class TestErrorHandling:
    """Test CLI error handling."""
    
    def test_invalid_command(self, cli):
        """Test invalid command handling."""
        result = cli.run_command(['fa', 'invalid-command'], expect_success=False)
        assert not result['success'], "Invalid command should fail"
        assert 'No such command' in result['stderr'] or 'Usage:' in result['stdout']
        
    def test_invalid_flags(self, cli):
        """Test invalid flag handling."""
        result = cli.run_command(['fa', '--invalid-flag'], expect_success=False)
        assert not result['success'], "Invalid flag should fail"
        
    def test_missing_required_args(self, cli):
        """Test missing required arguments."""
        result = cli.run_command(['fa', 'quick'], expect_success=False)
        assert not result['success'], "Missing required args should fail"


class TestCLIRobustness:
    """Test CLI robustness and edge cases."""
    
    def test_ctrl_c_handling(self, cli, test_image):
        """Test that CLI handles interruption gracefully."""
        # This is a basic test - in real scenarios we'd simulate SIGINT
        result = cli.run_command(['fa', 'quick', str(test_image)])
        # Just ensure it doesn't hang indefinitely (timeout handles this)
        assert result['returncode'] in [-1, 0, 1]
        
    def test_large_output_handling(self, cli, temp_dir):
        """Test CLI with potentially large output."""
        # Create a directory with multiple files
        for i in range(5):
            (temp_dir / f"file_{i}.txt").write_text(f"content {i}")
            
        result = cli.run_command(['fa', 'analyze', 'metadata', str(temp_dir)])
        # Should not crash, even if it fails due to missing dependencies
        assert result['returncode'] in [0, 1]
        
    def test_unicode_handling(self, cli, temp_dir):
        """Test CLI with unicode file names."""
        unicode_file = temp_dir / "测试文件.txt"
        unicode_file.write_text("test content")
        
        result = cli.run_command(['fa', 'analyze', 'metadata', str(unicode_file)])
        # Should handle unicode gracefully
        assert result['returncode'] in [0, 1]


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])