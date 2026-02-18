import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, mock_open

# --- Path Setup --- #
TEST_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.dirname(TEST_UTILS_DIR)
CELL_COVER_DIR = os.path.dirname(TEST_DIR)
PROJECT_ROOT = os.path.dirname(CELL_COVER_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from image_gen_mcp.apps.cell_cover.utils.prompt import generate_prompt_text, save_text_prompt, copy_to_clipboard

# Sample config data for testing
SAMPLE_CONFIG = {
  "concepts": {
    "concept_a": {
      "name": "Test Concept A",
      "description": "A test concept for unit testing",
      "midjourney_prompt": "test prompt base",
      "variations": {
        "varA": "with variation A",
        "varB": "plus variation B",
        "detail": "detailed view"
      }
    },
    "no_prompt": {
        "name": "Concept without prompt"
    }
  },
  "global_styles": {
    "focus": "focused composition",
    "cinematic": "cinematic style"
  }
}

class TestPromptUtils(unittest.TestCase):

    def setUp(self):
        self.mock_logger = MagicMock()

    # --- Tests for generate_prompt_text --- #

    def test_generate_prompt_basic(self):
        """Test basic prompt generation without variations."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a")
        self.assertIsNotNone(result)
        # Verify default values used by the code (16:9, 1, 6.1)
        self.assertIn("test prompt base", result['prompt'])
        self.assertIn("--ar 16:9", result['prompt'])
        self.assertIn("--v 6.1", result['prompt'])
        self.assertIn("--quality 1", result['prompt'])
        self.assertEqual(result['concept'], "concept_a")
        self.assertEqual(result['variations'], [])

    def test_generate_prompt_single_variation(self):
        """Test prompt generation with a single valid variation."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["varA"])
        self.assertIsNotNone(result)
        self.assertIn("test prompt base, with variation A", result['prompt'])
        self.assertEqual(result['variations'], ["varA"])

    def test_generate_prompt_multiple_variations(self):
        """Test prompt generation with multiple valid variations."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["varA", "varB"])
        self.assertIsNotNone(result)
        self.assertIn("with variation A, plus variation B", result['prompt'])
        self.assertEqual(result['variations'], ["varA", "varB"])

    def test_generate_prompt_custom_params(self):
        """Test prompt generation with passed parameters."""
        result = generate_prompt_text(
            self.mock_logger, SAMPLE_CONFIG, "concept_a",
            variation_keys=["detail"],
            aspect_ratio="1:1",
            quality=".5",
            version="5.2"
        )
        self.assertIsNotNone(result)
        self.assertIn("--ar 1:1", result['prompt'])
        self.assertIn("--quality .5", result['prompt'])
        self.assertIn("--v 5.2", result['prompt'])

    def test_generate_prompt_invalid_concept(self):
        """Test prompt generation with an invalid concept key."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "invalid_concept")
        self.assertIsNone(result)

    def test_generate_prompt_missing_base_prompt(self):
        """Test concept missing the 'midjourney_prompt' key."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "no_prompt")
        self.assertIsNone(result)

    def test_generate_prompt_invalid_variation(self):
        """Test prompt generation with an invalid variation key."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["invalidVar"])
        self.assertIsNone(result)

    # --- Global Styles Tests --- #

    def test_generate_prompt_single_global_style(self):
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", global_style_keys=["focus"])
        self.assertIsNotNone(result)
        self.assertIn("focused composition", result['prompt'])
        self.assertEqual(result['global_styles'], ["focus"])

    def test_generate_prompt_multiple_global_styles(self):
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", global_style_keys=["focus", "cinematic"])
        self.assertIsNotNone(result)
        self.assertIn("focused composition, cinematic style", result['prompt'])

    # --- Tests for save_text_prompt --- #

    @patch('image_gen_mcp.apps.cell_cover.utils.prompt.os.makedirs')
    @patch('image_gen_mcp.apps.cell_cover.utils.prompt.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_prompt_no_variation(self, mock_file, mock_exists, mock_makedirs):
        """Test saving a prompt file without variations."""
        mock_exists.return_value = True 
        output_dir = "/fake/output"
        prompt_text = "test prompt content"
        concept = "concept_a"

        filepath = save_text_prompt(self.mock_logger, output_dir, prompt_text, concept)

        self.assertIsNotNone(filepath)
        self.assertTrue(filepath.startswith(os.path.join(output_dir, f"{concept}_prompt_")))
        mock_file.assert_called_once_with(filepath, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(prompt_text)

    # --- Tests for copy_to_clipboard --- #

    @patch('image_gen_mcp.apps.cell_cover.utils.prompt.pyperclip.copy')
    @patch('image_gen_mcp.apps.cell_cover.utils.prompt.PYPERCLIP_AVAILABLE', True)
    def test_copy_to_clipboard_success(self, mock_pyperclip_copy):
        """Test successful copy to clipboard when available."""
        text_to_copy = "copy me"
        result = copy_to_clipboard(self.mock_logger, text_to_copy)
        self.assertTrue(result)
        mock_pyperclip_copy.assert_called_once_with(text_to_copy)

if __name__ == '__main__':
    unittest.main(verbosity=2)
