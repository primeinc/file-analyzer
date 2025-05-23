#!/usr/bin/env python3
"""
CLI Cleanliness Enforcement Test

This test ensures the CLI produces ZERO error output on normal operations.
This is a CRITICAL requirement - any error spam is unacceptable.

🚨 ZERO TOLERANCE for error spam 🚨
"""

import subprocess
import pytest


def run_cli_command(args, timeout=10):
    """Run a CLI command and capture all output."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        pytest.fail(f"Command {args} timed out after {timeout} seconds")
    except Exception as e:
        pytest.fail(f"Failed to run command {args}: {e}")


class TestCLICleanliness:
    """Test that CLI produces zero error output on normal operations."""
    
    def test_fa_help_is_clean(self):
        """Test that 'fa --help' produces zero error output."""
        result = run_cli_command(['fa', '--help'])
        
        # Must succeed
        assert result['success'], f"fa --help failed: {result['stderr']}"
        
        # Must have no error output
        assert result['stderr'] == '', f"fa --help produced error output: {result['stderr']}"
        
        # Must have help content
        assert 'Usage:' in result['stdout'], "fa --help missing Usage information"
        assert 'Commands' in result['stdout'] or 'Options' in result['stdout'], "fa --help missing Commands/Options"
        
    def test_fa_version_is_clean(self):
        """Test that 'fa --version' produces zero error output."""
        result = run_cli_command(['fa', '--version'])
        
        # Must succeed
        assert result['success'], f"fa --version failed: {result['stderr']}"
        
        # Must have no error output
        assert result['stderr'] == '', f"fa --version produced error output: {result['stderr']}"
        
        # Must have version content
        assert 'File Analyzer CLI' in result['stdout'], "fa --version missing version info"
        
    def test_no_args_is_clean(self):
        """Test that 'fa' with no args produces zero error output."""
        result = run_cli_command(['fa'])
        
        # Must succeed (should show help)
        assert result['success'], f"fa with no args failed: {result['stderr']}"
        
        # Must have no error output
        assert result['stderr'] == '', f"fa with no args produced error output: {result['stderr']}"
        
        # Must show help or usage
        assert 'Usage:' in result['stdout'], "fa with no args should show usage"
        
    @pytest.mark.parametrize("command", [
        ['fa', 'quick', '--help'],
        ['fa', 'analyze', '--help'],
        ['fa', 'model', '--help'],
        ['fa', 'test', '--help'],
        ['fa', 'validate', '--help'],
    ])
    def test_command_help_is_clean(self, command):
        """Test that all command help outputs are clean."""
        result = run_cli_command(command)
        
        # Must succeed
        assert result['success'], f"{' '.join(command)} failed: {result['stderr']}"
        
        # Must have no error output
        assert result['stderr'] == '', f"{' '.join(command)} produced error output: {result['stderr']}"
        
        # Must have help content
        assert 'Usage:' in result['stdout'], f"{' '.join(command)} missing Usage information"
        
    def test_invalid_command_proper_error(self):
        """Test that invalid commands produce proper error handling."""
        result = run_cli_command(['fa', 'nonexistent-command'])
        
        # Must fail with proper exit code
        assert not result['success'], "Invalid command should fail"
        
        # Error message can be in stdout OR stderr (typer varies)
        error_output = result['stdout'] + result['stderr']
        assert ('No such command' in error_output or 
                'Usage:' in error_output or 
                'nonexistent-command' in error_output), "Should provide helpful error message"
        
    def test_cli_no_import_errors(self):
        """Test that CLI import doesn't produce error output."""
        # This tests the module loading itself
        result = run_cli_command(['python', '-c', 'import src.cli.main; print("OK")'])
        
        # Must succeed
        assert result['success'], f"CLI import failed: {result['stderr']}"
        
        # Must have no error output during import
        assert result['stderr'] == '', f"CLI import produced error output: {result['stderr']}"
        
        # Must complete successfully
        assert 'OK' in result['stdout'], "CLI import did not complete"


class TestCLIErrorHandling:
    """Test proper error handling for genuine error conditions."""
    
    def test_nonexistent_file_proper_error(self):
        """Test that nonexistent files produce proper error handling."""
        result = run_cli_command(['fa', 'quick', '/nonexistent/file.jpg'])
        
        # Must fail
        assert not result['success'], "Nonexistent file should cause failure"
        assert result['returncode'] == 1, "Should exit with code 1"
        
        # Error should be in stderr (proper error handling)
        error_output = result['stdout'] + result['stderr']
        assert ('Error:' in error_output or 
                'does not exist' in error_output or
                'File does not exist' in error_output), \
            f"Should provide clear error message about missing file. Got stdout: '{result['stdout']}', stderr: '{result['stderr']}'"


if __name__ == "__main__":
    # Allow running this test file directly for quick validation
    pytest.main([__file__, "-v", "--tb=short"])