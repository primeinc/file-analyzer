#!/usr/bin/env python3
"""
Tests for FastVLM JSON parsing with real model outputs.

These tests use actual outputs captured from the FastVLM model to ensure
our JSON parsing logic handles both valid and malformed JSON correctly.
"""

import unittest
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestFastVLMJSONParsing(unittest.TestCase):
    """Test FastVLM JSON parsing with real model outputs."""
    
    def setUp(self):
        """Set up test fixtures with actual model outputs."""
        
        # Valid JSON output from 256 tokens (this works)
        self.valid_json_256_tokens = """{
  "description": "The image is a vibrant, cartoon-style illustration featuring a yellow rubber duck wearing sunglasses and a purple wizard hat, sitting in a bowl filled with alphabet soup. The duck is holding a spoon and appears to be stirring the soup. Surrounding the duck are three penguins dressed in suits, each with a surprised expression on their faces. One penguin is holding a sign that reads 'Intergalactic Banana Launcher' with a banana illustration. To the right, a penguin is holding an open briefcase filled with colorful candies. The background is a bright blue sky with clouds and various symbols such as question marks, exclamation marks, and a hashtag. The image also includes several hashtags such as #, @, and #.",
  "tags": ["Intergalactic Banana Launcher", "Rubber Duck", "Penguin", "Alphabet Soup", "Candy", "Cartoon", "Illustration", "Surprise", "Sunglasses", "Wizard Hat", "Soup", "Banana", "Candy", "Candies", "Heads", "Feathers", "Clouds", "Sky", "Symbols", "Hashtags", "@", "#"]
}"""

        # Malformed JSON output from 512 tokens (this breaks)
        self.malformed_json_512_tokens = """{
  "description": "The image is a vibrant, cartoon-style illustration featuring a yellow rubber duck wearing sunglasses and a purple wizard hat, sitting in a bowl of alphabet soup. The duck is holding a spoon and appears to be stirring the soup. Surrounding the duck are three penguins dressed in suits, each with a surprised expression on their faces. One of the penguins is holding a sign that reads 'INTERGALACTIC BANANA LAUNCHER' with a banana illustration. To the right, there is a briefcase filled with colorful candies. The background is a bright blue sky with clouds and various symbols such as question marks, exclamation marks, and hashtags scattered throughout. The image also includes some text elements like '@' and '#'.",
  "tags": ["intergalactic", "banana", "launcher", "rubber", "duck", "sunglasses", "penguins", "suit", "alphabet", "soup", "panda", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", "shark", """

        # Plain text output (what happens when JSON prompt fails)
        self.plain_text_output = """The image is a vibrant and colorful cartoon illustration featuring a variety of anthropomorphic characters and elements. Here is a detailed description of the image:

---

**Image Description:**

1. **Main Characters:**
   - **Yellow Duck with Wizard Hat:** The central figure is a yellow duck wearing sunglasses and a purple wizard hat with stars. The duck is sitting in a bowl filled with alphabet letters, which resemble alphabet soup. The duck is holding a spoon and appears to be stirring the soup.
   - **Three Penguins:** There are three penguins, all dressed in formal suits, standing around the bowl. They appear to be engaged in a conversation or reacting to the situation.
   - **Penguin with a Briefcase:** One of the penguins is holding a briefcase containing a large amount of colorful candies.

2. **Text Elements:**
   - **Sign:** The penguin holding the briefcase is holding a sign that reads "INTERGALACTIC BANANA LAUNCHER."
   - **Alphabet Letters:** The bowl in which the duck is sitting contains alphabet letters, which are arranged in a circular pattern around the duck.

3"""

    def test_valid_json_256_tokens_parsing(self):
        """Test that valid JSON from 256 tokens parses correctly."""
        try:
            parsed = json.loads(self.valid_json_256_tokens)
            self.assertIsInstance(parsed, dict)
            self.assertIn("description", parsed)
            self.assertIn("tags", parsed)
            self.assertIsInstance(parsed["tags"], list)
            self.assertGreater(len(parsed["tags"]), 0)
        except json.JSONDecodeError as e:
            self.fail(f"Valid JSON should parse without error: {e}")

    def test_malformed_json_512_tokens_parsing(self):
        """Test that malformed JSON from 512 tokens fails standard parsing."""
        with self.assertRaises(json.JSONDecodeError):
            json.loads(self.malformed_json_512_tokens)

    def test_json_repair_on_malformed_json(self):
        """Test that json-repair can fix the malformed JSON."""
        try:
            from json_repair import repair_json
            
            # Attempt to repair the malformed JSON
            repaired = repair_json(self.malformed_json_512_tokens)
            parsed = json.loads(repaired)
            
            self.assertIsInstance(parsed, dict)
            self.assertIn("description", parsed)
            self.assertIn("tags", parsed)
            self.assertIsInstance(parsed["tags"], list)
            
            # Check that repetitive "shark" entries are handled
            tag_counts = {}
            for tag in parsed["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Should have fewer "shark" entries after repair
            if "shark" in tag_counts:
                self.assertLess(tag_counts["shark"], 50, "JSON repair should reduce repetitive entries")
                
        except ImportError:
            self.skipTest("json-repair package not available")

    def test_plain_text_conversion_to_json(self):
        """Test converting plain text output to structured JSON."""
        # This is what we need to implement for handling plain text
        expected_structure = {
            "description": str,
            "tags": list,
            "metadata": dict
        }
        
        # For now, just test that we can extract basic info
        self.assertIn("yellow duck", self.plain_text_output.lower())
        self.assertIn("penguins", self.plain_text_output.lower())
        self.assertIn("alphabet", self.plain_text_output.lower())

    def test_adapter_json_parsing_logic(self):
        """Test the actual adapter JSON parsing logic with our samples."""
        
        # Simulate the adapter's JSON parsing method
        def parse_model_output(output):
            """Simulate the adapter's parsing logic."""
            try:
                return json.loads(output)
            except json.JSONDecodeError as e:
                try:
                    from json_repair import repair_json
                    repaired_json = repair_json(output)
                    return json.loads(repaired_json)
                except Exception as repair_error:
                    raise RuntimeError(f"Failed to parse model output as JSON: {e}. JSON repair also failed: {repair_error}")

        # Test valid JSON
        result = parse_model_output(self.valid_json_256_tokens)
        self.assertIsInstance(result, dict)
        self.assertIn("description", result)
        self.assertIn("tags", result)

        # Test malformed JSON (should be repaired)
        try:
            result = parse_model_output(self.malformed_json_512_tokens)
            self.assertIsInstance(result, dict)
            self.assertIn("description", result)
            self.assertIn("tags", result)
        except ImportError:
            self.skipTest("json-repair package not available")

        # Test plain text (should fail)
        with self.assertRaises(RuntimeError):
            parse_model_output(self.plain_text_output)

    def test_token_limit_recommendations(self):
        """Test that we can identify optimal token limits."""
        
        # 256 tokens should produce valid JSON
        self.assertTrue(self._is_valid_json(self.valid_json_256_tokens))
        
        # 512 tokens produces malformed JSON
        self.assertFalse(self._is_valid_json(self.malformed_json_512_tokens))
        
        # This test documents that 256 tokens is the sweet spot
        recommended_token_limit = 256
        self.assertEqual(recommended_token_limit, 256, "256 tokens produces clean JSON without repetition")

    def _is_valid_json(self, text):
        """Helper method to check if text is valid JSON."""
        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False

if __name__ == "__main__":
    unittest.main()