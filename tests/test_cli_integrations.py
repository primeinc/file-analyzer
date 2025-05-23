#!/usr/bin/env python3
"""
CLI INTEGRATION TESTS - THE SINGLE FORTRESS

This is the ONLY file for CLI functional testing. All CLI tests go here.
These tests verify actual contracts and real functionality, not cosmetic startup behavior.

CONTRACT ASSERTIONS REQUIRED:
- Exit code = 0 for normal commands
- Known output strings or files are created  
- No stderr on clean operations
- Expected stderr on broken operations
"""

import os
import subprocess
import tempfile
import pytest
from pathlib import Path


def run_cmd(cmd_list, expect_success=True):
    """Run command and return result with contract validation."""
    result = subprocess.run(
        cmd_list, 
        capture_output=True, 
        text=True, 
        timeout=30,
        cwd=Path(__file__).parent.parent
    )
    
    return {
        'returncode': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'success': result.returncode == 0,
        'cmd': ' '.join(cmd_list)
    }


class TestCLIContracts:
    """Test CLI command contracts with real operations."""
    
    def test_fa_help_contract(self):
        """CLI help must work and show commands."""
        result = run_cmd(['fa', '--help'])
        
        assert result['success'], f"fa --help failed: {result['stderr']}"
        assert result['stderr'] == '', f"fa --help produced stderr: {result['stderr']}"
        assert 'analyze' in result['stdout'], "Missing analyze command in help"
        assert 'artifact' in result['stdout'], "Missing artifact command in help"
        assert 'test' in result['stdout'], "Missing test command in help"
    
    def test_fa_artifact_setup_creates_structure(self):
        """Artifact setup must create directory structure."""
        result = run_cmd(['fa', 'artifact', 'setup'])
        
        assert result['success'], f"fa artifact setup failed: {result['stderr']}"
        
        # Verify actual artifact directories exist
        artifacts_root = Path("artifacts")
        required_dirs = ["analysis", "vision", "test", "benchmark", "json", "tmp"]
        
        for dir_name in required_dirs:
            dir_path = artifacts_root / dir_name
            assert dir_path.exists(), f"Required directory {dir_name} missing after setup"
            assert dir_path.is_dir(), f"Path {dir_name} exists but is not a directory"
    
    def test_fa_artifact_path_generates_canonical_paths(self):
        """Artifact path generation must create valid canonical paths."""
        result = run_cmd(['fa', 'artifact', 'path', 'test', 'integration_test'])
        
        assert result['success'], f"fa artifact path failed: {result['stderr']}"
        assert result['stderr'] == '', f"Path generation produced stderr: {result['stderr']}"
        
        generated_path = result['stdout'].strip()
        assert generated_path, "No path output generated"
        
        path_obj = Path(generated_path)
        assert path_obj.exists(), f"Generated path {generated_path} does not exist"
        assert 'test' in str(path_obj), "Generated path missing type component"
        assert 'integration_test' in str(path_obj), "Generated path missing context component"
    
    def test_fa_artifact_clean_tmp_empties_directory(self):
        """Tmp cleanup must empty tmp directory without removing it."""
        # Create test content in tmp
        tmp_result = run_cmd(['fa', 'artifact', 'path', 'tmp', 'cleanup_test'])
        assert tmp_result['success'], "Failed to create tmp test path"
        
        tmp_path = Path(tmp_result['stdout'].strip())
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test content")
        assert test_file.exists(), "Test file not created"
        
        # Clean tmp
        clean_result = run_cmd(['fa', 'artifact', 'clean-tmp'])
        assert clean_result['success'], f"fa artifact clean-tmp failed: {clean_result['stderr']}"
        assert clean_result['stderr'] == '', f"Clean tmp produced stderr: {clean_result['stderr']}"
        
        # Verify tmp directory exists but is empty
        tmp_root = Path("artifacts/tmp")
        assert tmp_root.exists(), "Tmp directory removed (should be emptied, not removed)"
        assert len(list(tmp_root.iterdir())) == 0, f"Tmp directory not empty: {list(tmp_root.iterdir())}"


class TestCLIErrorHandling:
    """Test CLI error handling contracts."""
    
    def test_nonexistent_file_produces_helpful_error(self):
        """CLI must handle nonexistent files gracefully with informative errors."""
        fake_file = "/tmp/nonexistent_file_12345.jpg"
        result = run_cmd(['fa', 'analyze', 'metadata', fake_file], expect_success=False)
        
        assert not result['success'], "Should fail for nonexistent file"
        assert result['returncode'] > 0, "Should have non-zero exit code"
        
        error_text = (result['stderr'] + result['stdout']).lower()
        assert any(phrase in error_text for phrase in ['not found', 'does not exist', 'no such file']), \
            f"Error message not informative: {error_text}"
    
    def test_invalid_command_shows_helpful_error(self):
        """Invalid commands must show helpful error message."""
        result = run_cmd(['fa', 'invalid-command-xyz'], expect_success=False)
        
        assert not result['success'], "Invalid command should fail"
        assert result['returncode'] > 0, "Should have non-zero exit code"
        
        error_text = result['stderr'] + result['stdout']
        assert 'invalid-command-xyz' in error_text, "Error should mention the invalid command"


class TestCLIRealWorldUsage:
    """Test CLI in realistic usage scenarios."""
    
    def test_artifact_workflow_end_to_end(self):
        """Complete artifact workflow must work end-to-end."""
        # Setup
        setup_result = run_cmd(['fa', 'artifact', 'setup'])
        assert setup_result['success'], f"Setup failed: {setup_result['stderr']}"
        
        # Generate path
        path_result = run_cmd(['fa', 'artifact', 'path', 'test', 'e2e_workflow'])
        assert path_result['success'], f"Path generation failed: {path_result['stderr']}"
        
        # Verify path exists and is usable
        test_path = Path(path_result['stdout'].strip())
        assert test_path.exists(), "Generated path should exist"
        
        # Create content
        test_file = test_path / "workflow_output.json"
        test_content = '{"workflow": "test", "status": "success"}'
        test_file.write_text(test_content)
        assert test_file.exists(), "Should be able to write to generated path"
        
        # Verify content
        assert test_file.read_text() == test_content, "File content should be preserved"
        
        # Clean tmp should not affect non-tmp files
        clean_result = run_cmd(['fa', 'artifact', 'clean-tmp'])
        assert clean_result['success'], f"Clean failed: {clean_result['stderr']}"
        assert test_file.exists(), "Clean tmp should not remove non-tmp files"
    
    @pytest.mark.skipif(not Path("test_data/images/test.jpg").exists(), reason="Test image not available")
    def test_analyze_with_real_file(self):
        """Analysis commands must work with real files (when tools available)."""
        test_image = Path("test_data/images/test.jpg")
        
        # Try metadata analysis (may fail if exiftool not installed, but shouldn't crash)
        result = run_cmd(['fa', 'analyze', 'metadata', str(test_image)])
        
        # Command should execute without crashing
        assert result['returncode'] != -9, "Command was killed (likely crash)"
        assert 'Traceback' not in result['stderr'], f"Command crashed with traceback: {result['stderr']}"
        
        # If it succeeds, should create output
        if result['success']:
            artifacts_dir = Path("artifacts/analysis")
            analysis_outputs = list(artifacts_dir.glob("*")) if artifacts_dir.exists() else []
            assert len(analysis_outputs) > 0, "Successful analysis should create output files"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])