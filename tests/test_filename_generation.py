"""
Comprehensive tests for intelligent filename generation.

Tests all aspects of the filename generation logic including:
- Content-specific pattern recognition
- Tag cleaning and deduplication
- Fallback mechanisms
- Edge cases and error handling
- Integration with FastVLM adapter
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from src.cli.utils.render import (
    generate_intelligent_filename,
    clean_tags,
    _extract_filename_from_description
)


class TestTagCleaning:
    """Test tag cleaning and deduplication functionality."""
    
    def test_removes_generic_tags(self):
        """Test that generic tags are filtered out."""
        raw_tags = ["image", "photo", "shooting", "duck", "wizard", "picture"]
        result = clean_tags(raw_tags)
        
        # Should remove generic terms
        assert "image" not in result
        assert "photo" not in result
        assert "shooting" not in result
        assert "picture" not in result
        
        # Should keep meaningful content
        assert "duck" in result
        assert "wizard" in result
    
    def test_deduplicates_tags(self):
        """Test that duplicate tags are removed."""
        raw_tags = ["duck", "Duck", "DUCK", "wizard", "wizard", "penguin"]
        result = clean_tags(raw_tags)
        
        # Should deduplicate case-insensitively
        duck_count = sum(1 for tag in result if tag.lower() == "duck")
        wizard_count = sum(1 for tag in result if tag.lower() == "wizard")
        penguin_count = sum(1 for tag in result if tag.lower() == "penguin")
        
        assert duck_count == 1
        assert wizard_count == 1
        assert penguin_count == 1
    
    def test_sorts_by_frequency(self):
        """Test that tags are sorted by frequency."""
        raw_tags = ["rare", "common", "common", "common", "medium", "medium"]
        result = clean_tags(raw_tags)
        
        # Most common should come first
        assert result.index("common") < result.index("medium")
        assert result.index("medium") < result.index("rare")
    
    def test_limits_tag_count(self):
        """Test that tag count is limited to reasonable number."""
        raw_tags = [f"tag_{i}" for i in range(20)]  # 20 unique tags
        result = clean_tags(raw_tags)
        
        # Should not exceed limit (10 tags)
        assert len(result) <= 10
    
    def test_filters_short_tags(self):
        """Test that very short tags are filtered out."""
        raw_tags = ["a", "ab", "cat", "dog", "elephant"]
        result = clean_tags(raw_tags)
        
        # Should remove tags with 2 or fewer characters
        assert "a" not in result
        assert "ab" not in result
        assert "cat" in result
        assert "dog" in result
        assert "elephant" in result
    
    def test_handles_empty_input(self):
        """Test handling of empty or None input."""
        assert clean_tags([]) == []
        assert clean_tags(None) == []
        assert clean_tags(["", "  ", "   "]) == []


class TestFilenameExtractionFallback:
    """Test the fallback filename extraction from descriptions."""
    
    def test_letter_pattern_extraction(self):
        """Test extraction of letter patterns."""
        test_cases = [
            ("The image shows the letter 'T' in red", ".jpg", "letter-t.jpg"),
            ("A stylized letter A in blue font", ".png", "letter-a.png"),
            ("Letter 'Z' symbol on white background", ".gif", "letter-z.gif"),
        ]
        
        for description, ext, expected in test_cases:
            result = _extract_filename_from_description(description, ext)
            assert result == expected
    
    def test_number_pattern_extraction(self):
        """Test extraction of number patterns."""
        test_cases = [
            ("The number 5 written in bold", ".jpg", "number-5.jpg"),
            ("A large number '42' displayed", ".png", "number-42.png"),
            ("Number 0 in geometric style", ".svg", "number-0.svg"),
        ]
        
        for description, ext, expected in test_cases:
            result = _extract_filename_from_description(description, ext)
            assert result == expected
    
    def test_icon_pattern_extraction(self):
        """Test extraction of icon patterns."""
        test_cases = [
            ("An icon of a star", ".png", "icon-star.png"),
            ("Icon of heart symbol", ".svg", "icon-heart.svg"),
            ("A symbol T in the center", ".jpg", "symbol-t.jpg"),
        ]
        
        for description, ext, expected in test_cases:
            result = _extract_filename_from_description(description, ext)
            assert result == expected
    
    def test_key_object_extraction(self):
        """Test extraction of key objects from description."""
        test_cases = [
            ("A duck swimming in a pond", ".jpg", "duck.jpg"),
            ("A red car parked outside", ".png", "car.png"),
            ("A cat and dog playing together", ".gif", "cat-dog.gif"),
        ]
        
        for description, ext, expected in test_cases:
            result = _extract_filename_from_description(description, ext)
            assert result == expected
    
    def test_proper_noun_extraction(self):
        """Test extraction of proper nouns (capitalized words)."""
        description = "The Statue of Liberty in New York"
        result = _extract_filename_from_description(description, ".jpg")
        
        # Should extract significant capitalized words
        assert "statue" in result.lower()
        assert "liberty" in result.lower()
        assert result.endswith(".jpg")
        # Should be something like "statue-liberty-new.jpg"
        assert result in ["statue-liberty-new.jpg", "statue-liberty.jpg"]
    
    def test_fallback_to_unknown(self):
        """Test fallback when no patterns match."""
        description = "abstract composition with various elements"
        result = _extract_filename_from_description(description, ".jpg")
        
        assert result == "unknown-content.jpg"


class TestIntelligentFilenameGeneration:
    """Test the full intelligent filename generation with adapter integration."""
    
    @patch('src.models.fastvlm.adapter.create_adapter')
    def test_successful_model_filename_generation(self, mock_create_adapter):
        """Test successful filename generation using model."""
        # Mock the adapter and its predict method
        mock_adapter = MagicMock()
        mock_adapter.predict.return_value = {
            "description": "red-sports-car",
            "text": "red-sports-car"
        }
        mock_create_adapter.return_value = mock_adapter
        
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            
            result = generate_intelligent_filename(
                "A red sports car", 
                tmp_file.name, 
                ".jpg"
            )
            
            assert result == "red-sports-car.jpg"
            
            # Verify adapter was called correctly
            mock_create_adapter.assert_called_once()
            mock_adapter.predict.assert_called_once()
    
    @patch('src.models.fastvlm.adapter.create_adapter')
    def test_model_failure_fallback(self, mock_create_adapter):
        """Test fallback when model fails."""
        # Mock adapter to raise exception
        mock_adapter = MagicMock()
        mock_adapter.predict.side_effect = Exception("Model failed")
        mock_create_adapter.return_value = mock_adapter
        
        result = generate_intelligent_filename(
            "The letter T in red font", 
            "/fake/path.jpg", 
            ".jpg"
        )
        
        # Should fall back to pattern extraction
        assert result == "letter-t.jpg"
    
    @patch('src.models.fastvlm.adapter.create_adapter')
    def test_invalid_model_response_fallback(self, mock_create_adapter):
        """Test fallback when model returns invalid response."""
        # Mock adapter to return invalid response
        mock_adapter = MagicMock()
        mock_adapter.predict.return_value = {
            "error": "Invalid response"
        }
        mock_create_adapter.return_value = mock_adapter
        
        result = generate_intelligent_filename(
            "A duck wearing a wizard hat", 
            "/fake/path.jpg", 
            ".jpg"
        )
        
        # Should fall back to pattern extraction
        assert result == "duck.jpg"
    
    @patch('src.models.fastvlm.adapter.create_adapter')
    def test_filename_cleaning_and_validation(self, mock_create_adapter):
        """Test that generated filenames are properly cleaned."""
        # Mock adapter to return messy filename
        mock_adapter = MagicMock()
        mock_adapter.predict.return_value = {
            "description": "My! Awesome@ File-Name  With  Spaces!!!"
        }
        mock_create_adapter.return_value = mock_adapter
        
        result = generate_intelligent_filename(
            "Test description", 
            "/fake/path.jpg", 
            ".jpg"
        )
        
        # Should clean up the filename
        assert result == "my-awesome-file-name-with-spaces.jpg"
        assert result.count("-") >= 1  # Should have hyphens
        assert "!" not in result  # Should remove special chars
        assert "  " not in result  # Should collapse spaces
    
    @patch('src.models.fastvlm.adapter.create_adapter')
    def test_short_filename_rejection(self, mock_create_adapter):
        """Test that very short filenames are rejected."""
        # Mock adapter to return very short filename
        mock_adapter = MagicMock()
        mock_adapter.predict.return_value = {
            "description": "ab"
        }
        mock_create_adapter.return_value = mock_adapter
        
        result = generate_intelligent_filename(
            "The number 5 in blue", 
            "/fake/path.jpg", 
            ".jpg"
        )
        
        # Should fall back to pattern extraction since "ab" is too short
        assert result == "number-5.jpg"
    
    def test_different_file_extensions(self):
        """Test filename generation with different file extensions."""
        test_cases = [
            (".jpg", "JPEG image"),
            (".png", "PNG image"),
            (".gif", "GIF animation"),
            (".svg", "SVG vector"),
            (".webp", "WebP image"),
        ]
        
        for ext, description in test_cases:
            result = generate_intelligent_filename(
                f"The letter T in red font - {description}", 
                f"/fake/path{ext}", 
                ext
            )
            
            assert result.endswith(ext)
            assert "letter-t" in result
    
    @patch('src.models.fastvlm.adapter.create_adapter')
    def test_adapter_creation_parameters(self, mock_create_adapter):
        """Test that adapter is created with correct parameters."""
        mock_adapter = MagicMock()
        mock_adapter.predict.return_value = {"description": "test-filename"}
        mock_create_adapter.return_value = mock_adapter
        
        generate_intelligent_filename(
            "Test description", 
            "/fake/path.jpg", 
            ".jpg"
        )
        
        # Verify adapter creation with correct parameters
        mock_create_adapter.assert_called_once_with(
            "fastvlm", 
            "1.5b", 
            auto_download=False
        )
        
        # Verify predict call parameters
        call_args = mock_adapter.predict.call_args
        assert call_args[1]["mode"] == "describe"
        assert call_args[1]["max_new_tokens"] == 50
        assert "filename" in call_args[1]["prompt"].lower()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_description(self):
        """Test handling of empty description."""
        result = generate_intelligent_filename("", "/fake/path.jpg", ".jpg")
        assert result == "unknown-content.jpg"
    
    def test_whitespace_only_description(self):
        """Test handling of whitespace-only description."""
        result = generate_intelligent_filename("   \n\t   ", "/fake/path.jpg", ".jpg")
        assert result == "unknown-content.jpg"
    
    def test_very_long_description(self):
        """Test handling of very long descriptions."""
        long_description = "A " + "very " * 100 + "long description with many words"
        result = generate_intelligent_filename(long_description, "/fake/path.jpg", ".jpg")
        
        # Should handle gracefully and not crash
        assert result.endswith(".jpg")
        assert len(result) < 100  # Should not be excessively long
    
    def test_special_characters_in_description(self):
        """Test handling of special characters in description."""
        description = "Image with / \\ : * ? \" < > | special characters"
        result = generate_intelligent_filename(description, "/fake/path.jpg", ".jpg")
        
        # Should handle gracefully and produce valid filename
        assert result.endswith(".jpg")
        # Should not contain filesystem-unsafe characters
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in unsafe_chars:
            assert char not in result
    
    def test_unicode_description(self):
        """Test handling of unicode characters in description."""
        description = "Image with émojis 🦆 and ñoñó characters"
        result = generate_intelligent_filename(description, "/fake/path.jpg", ".jpg")
        
        # Should handle gracefully
        assert result.endswith(".jpg")
        assert len(result) > 4  # Should produce some filename
    
    def test_missing_file_extension(self):
        """Test handling when file extension is missing."""
        result = generate_intelligent_filename("Test description", "/fake/path", "")
        
        # Should still work with empty extension
        assert isinstance(result, str)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])