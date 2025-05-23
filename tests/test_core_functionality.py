"""
Core Functionality Tests

High-value tests that actually test real functionality with minimal mocking.
Focuses on the core business logic that users depend on.
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.core.artifact_guard import get_canonical_artifact_path, PathGuard
from src.utils.json_utils import JSONValidator
from src.cli.utils.render import generate_intelligent_filename, clean_tags


class TestJSONProcessing:
    """Test actual JSON processing functionality."""
    
    def test_json_extraction_from_malformed_text(self):
        """Test extracting JSON from model output with extra text."""
        malformed_text = '''
        Here's my analysis:
        {
            "description": "A red apple",
            "tags": ["fruit", "red", "apple"]
        }
        I hope this helps!
        '''
        
        result = JSONValidator.extract_json_from_text(malformed_text)
        assert result["description"] == "A red apple"
        assert "apple" in result["tags"]
    
    def test_json_validator_with_real_structure(self):
        """Test JSON validation with real expected structure."""
        validator = JSONValidator()
        
        valid_data = {
            "description": "Test image",
            "tags": ["test", "image"],
            "metadata": {"model": "test"}
        }
        
        result = validator.validate_json_structure(valid_data, ["description", "tags"])
        assert result is True
        
        # Test missing required field
        invalid_data = {"tags": ["test"]}
        result = validator.validate_json_structure(invalid_data, ["description", "tags"])
        assert result is False


class TestFilenameGeneration:
    """Test intelligent filename generation."""
    
    def test_content_specific_patterns(self):
        """Test filename generation for specific content types."""
        test_cases = [
            ("The letter T in red font", "letter-t"),
            ("The number 5 written in blue", "number-5"),
            ("A star icon", "star"),
            ("A duck wearing a wizard hat", "duck"),
        ]
        
        for description, expected_pattern in test_cases:
            result = generate_intelligent_filename(description, "test.jpg", ".jpg")
            assert expected_pattern in result.lower()
            assert result.endswith(".jpg")
    
    def test_tag_cleaning_removes_generic_terms(self):
        """Test that generic tags are filtered out."""
        raw_tags = ["image", "photo", "shooting", "duck", "wizard", "sh"]
        result = clean_tags(raw_tags)
        
        # Should remove generic terms
        assert "image" not in result
        assert "photo" not in result
        assert "shooting" not in result
        assert "sh" not in result
        
        # Should keep meaningful content
        assert "duck" in result
        assert "wizard" in result
    
    def test_tag_deduplication(self):
        """Test that duplicate tags are removed."""
        raw_tags = ["duck", "Duck", "DUCK", "wizard", "wizard"]
        result = clean_tags(raw_tags)
        
        # Should deduplicate case-insensitively
        duck_count = sum(1 for tag in result if tag.lower() == "duck")
        wizard_count = sum(1 for tag in result if tag.lower() == "wizard")
        
        assert duck_count == 1
        assert wizard_count == 1


class TestArtifactDiscipline:
    """Test artifact path management."""
    
    def test_canonical_path_generation(self):
        """Test canonical artifact path creation."""
        path = get_canonical_artifact_path("test", "my_test")
        
        assert "artifacts/test" in str(path)
        assert "my_test" in str(path)
        assert path.is_absolute()
    
    def test_path_guard_context_manager(self):
        """Test PathGuard context manager."""
        test_dir = get_canonical_artifact_path("test", "path_guard_test")
        
        with PathGuard(test_dir) as guard:
            assert guard.artifact_dir == test_dir
            # Should create directory
            assert test_dir.exists()
    
    def test_safe_file_operations(self):
        """Test safe file operations within artifact directory."""
        test_dir = get_canonical_artifact_path("test", "safe_ops_test")
        
        with PathGuard(test_dir):
            # Test writing within allowed directory
            test_file = test_dir / "test.txt"
            test_file.write_text("test content")
            
            assert test_file.exists()
            assert test_file.read_text() == "test content"



class TestRealIntegration:
    """Integration tests that actually test integration."""
    
    def test_end_to_end_json_processing(self):
        """Test complete JSON processing pipeline."""
        # Simulate real model output with issues
        messy_output = '''
        Looking at this image, I can see:
        {
            "description": "A beautiful sunset over mountains",
            "tags": ["sunset", "mountains", "landscape", "image", "photo", "shooting"]
        }
        The colors are amazing!
        '''
        
        # Extract JSON
        extracted = JSONValidator.extract_json_from_text(messy_output)
        assert extracted["description"] == "A beautiful sunset over mountains"
        
        # Clean tags
        clean_tag_list = clean_tags(extracted["tags"])
        assert "sunset" in clean_tag_list
        assert "mountains" in clean_tag_list
        assert "image" not in clean_tag_list  # Should be filtered
        
        # Generate filename
        filename = generate_intelligent_filename(
            extracted["description"], 
            "original.jpg", 
            ".jpg"
        )
        assert filename.endswith(".jpg")
        assert "sunset" in filename.lower() or "mountain" in filename.lower()
    
    @patch('src.models.fastvlm.adapter.create_adapter')
    def test_cli_to_analysis_pipeline(self, mock_adapter):
        """Test minimal CLI to analysis pipeline."""
        # Mock only the expensive model call, test everything else
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {
            "description": "A test image showing a duck",
            "tags": ["duck", "test", "image"],
            "metadata": {"model": "fastvlm_1.5b", "execution_time": 1.0}
        }
        mock_adapter.return_value = mock_instance
        
        # Import and test the render function
        from src.cli.utils.render import render_output
        
        analysis_data = {
            "description": "A test image showing a duck",
            "tags": ["duck", "test", "image"],
            "metadata": {"model": "fastvlm_1.5b", "execution_time": 1.0}
        }
        
        # Test text output
        result = render_output(analysis_data, "pretty", "test.jpg")
        assert "Recommended Filename:" in result
        assert "duck" in result.lower()
        
        # Test JSON output
        json_result = render_output(analysis_data, "json", "test.jpg")
        parsed = json.loads(json_result)
        assert "recommended_filename" in parsed
        assert "duck" in parsed["description"].lower()


class TestErrorHandling:
    """Test error handling without excessive mocking."""
    
    def test_json_extraction_graceful_failure(self):
        """Test JSON extraction handles complete garbage gracefully."""
        garbage_text = "This is not JSON at all! 12345 @#$%"
        
        result = JSONValidator.extract_json_from_text(garbage_text)
        
        # Should return fallback structure
        assert isinstance(result, dict)
        assert "error" in result or "description" in result
    
    def test_filename_generation_with_empty_description(self):
        """Test filename generation handles edge cases."""
        result = generate_intelligent_filename("", "test.jpg", ".jpg")
        
        assert result.endswith(".jpg")
        assert len(result) > 4  # Should not be just ".jpg"
    
    def test_path_guard_with_invalid_path(self):
        """Test PathGuard handles invalid paths gracefully."""
        with pytest.raises((ValueError, OSError)):
            with PathGuard("/invalid/path/that/cannot/be/created"):
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])