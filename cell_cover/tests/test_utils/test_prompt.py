import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, mock_open

# --- Path Setup --- #
# Add the project root directory (paper) to the Python path
# This allows importing 'cell_cover' as a package
TEST_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.dirname(TEST_UTILS_DIR)
CELL_COVER_DIR = os.path.dirname(TEST_DIR)
PROJECT_ROOT = os.path.dirname(CELL_COVER_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ------------------ #

# Now import the module to be tested using package path
from cell_cover.utils.prompt import generate_prompt_text, save_text_prompt, copy_to_clipboard

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
  "aspect_ratios": {
    "cell_cover": "--ar 8:11",
    "square": "--ar 1:1"
  },
  "quality_settings": {
    "high": "--q 1",
    "standard": "--q 0.8"
  },
  "style_versions": {
    "v6": "--v 6",
    "v5": "--v 5"
  },
  "global_styles": {
    "focus": "focused composition, emphasizing the central interaction, clean background with reduced clutter, clear subject highlighting",
    "cinematic": "cinematic style"
  }
}

class TestPromptUtils(unittest.TestCase):

    def setUp(self):
        # Create a dummy logger for tests
        self.mock_logger = MagicMock()

    # --- Tests for generate_prompt_text --- #

    def test_generate_prompt_basic(self):
        """Test basic prompt generation without variations."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a")
        self.assertIsNotNone(result)
        self.assertEqual(result['prompt'], "test prompt base --ar 8:11 --q 1 --v 6")
        self.assertEqual(result['concept'], "concept_a")
        self.assertEqual(result['variations'], [])
        self.assertEqual(result['aspect_ratio'], "8:11")
        self.assertEqual(result['quality'], "1")
        self.assertEqual(result['version'], "6")

    def test_generate_prompt_single_variation(self):
        """Test prompt generation with a single valid variation."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["varA"])
        self.assertIsNotNone(result)
        self.assertEqual(result['prompt'], "test prompt base with variation A --ar 8:11 --q 1 --v 6")
        self.assertEqual(result['variations'], ["varA"])

    def test_generate_prompt_multiple_variations(self):
        """Test prompt generation with multiple valid variations."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["varA", "varB"])
        self.assertIsNotNone(result)
        self.assertEqual(result['prompt'], "test prompt base with variation A plus variation B --ar 8:11 --q 1 --v 6")
        self.assertEqual(result['variations'], ["varA", "varB"])

    def test_generate_prompt_custom_params(self):
        """Test prompt generation with non-default parameters."""
        result = generate_prompt_text(
            self.mock_logger, SAMPLE_CONFIG, "concept_a",
            variation_keys=["detail"],
            aspect_ratio="square",
            quality="standard",
            version="v5"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['prompt'], "test prompt base detailed view --ar 1:1 --q 0.8 --v 5")
        self.assertEqual(result['variations'], ["detail"])
        self.assertEqual(result['aspect_ratio'], "1:1")
        self.assertEqual(result['quality'], "0.8")
        self.assertEqual(result['version'], "5")

    def test_generate_prompt_invalid_concept(self):
        """Test prompt generation with an invalid concept key."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "invalid_concept")
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_with("错误：找不到创意概念 'invalid_concept'")

    def test_generate_prompt_missing_base_prompt(self):
        """Test concept missing the 'midjourney_prompt' key."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "no_prompt")
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_with("错误：概念 'no_prompt' 没有定义 'midjourney_prompt'。")

    def test_generate_prompt_invalid_variation(self):
        """Test prompt generation with an invalid variation key."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["invalidVar"])
        self.assertIsNone(result)
        expected_error_msg = "错误：在概念 'concept_a' 中找不到变体 'invalidVar'。"
        self.mock_logger.error.assert_called_with(expected_error_msg)

    def test_generate_prompt_mixed_variations_invalid(self):
        """Test prompt generation with mixed valid and invalid variation keys."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["varA", "invalidVar"])
        self.assertIsNone(result)
        expected_error_msg = "错误：在概念 'concept_a' 中找不到变体 'invalidVar'。"
        self.mock_logger.error.assert_called_with(expected_error_msg) # Should fail on first invalid

    def test_generate_prompt_invalid_aspect(self):
        """Test handling of invalid aspect ratio key (should warn and use default)."""
        with patch('builtins.print') as mock_print: # Capture print warnings
            result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", aspect_ratio="invalid_aspect")
            self.assertIsNotNone(result)
            self.assertNotIn("--ar invalid_aspect", result['prompt'])
            self.assertTrue(result['prompt'].endswith("--v 6")) # Ensure default params are still there
            self.mock_logger.warning.assert_called_with("警告：找不到宽高比设置 'invalid_aspect'，将使用默认。")
            mock_print.assert_any_call("警告：找不到宽高比设置 'invalid_aspect'，将使用默认。")

    # --- NEW Tests for Global Styles --- #

    def test_generate_prompt_single_global_style(self):
        """Test prompt generation with a single valid global style."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", global_style_keys=["focus"])
        self.assertIsNotNone(result)
        # Check if global style text is inserted before technical params
        expected_prompt = "test prompt base focused composition, emphasizing the central interaction, clean background with reduced clutter, clear subject highlighting --ar 8:11 --q 1 --v 6"
        self.assertEqual(result['prompt'], expected_prompt)
        self.assertEqual(result['global_styles'], ["focus"])
        self.assertEqual(result['variations'], []) # No concept variations used

    def test_generate_prompt_multiple_global_styles(self):
        """Test prompt generation with multiple valid global styles."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", global_style_keys=["focus", "cinematic"])
        self.assertIsNotNone(result)
        style1_text = SAMPLE_CONFIG["global_styles"]["focus"]
        style2_text = SAMPLE_CONFIG["global_styles"]["cinematic"]
        expected_prompt = f"test prompt base {style1_text} {style2_text} --ar 8:11 --q 1 --v 6"
        self.assertEqual(result['prompt'], expected_prompt)
        self.assertEqual(result['global_styles'], ["focus", "cinematic"])

    def test_generate_prompt_invalid_global_style(self):
        """Test prompt generation with an invalid global style key."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", global_style_keys=["nonexistent_style"])
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_with("错误：找不到全局风格 'nonexistent_style'。请检查 prompts_config.json 中的 global_styles 定义。")

    def test_generate_prompt_mixed_global_styles_invalid(self):
        """Test prompt generation with mixed valid and invalid global style keys."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", global_style_keys=["focus", "invalid_style"])
        self.assertIsNone(result)
        self.mock_logger.error.assert_called_with("错误：找不到全局风格 'invalid_style'。请检查 prompts_config.json 中的 global_styles 定义。")

    def test_generate_prompt_variation_and_global_style(self):
        """Test prompt generation using both concept variation and global style."""
        result = generate_prompt_text(self.mock_logger, SAMPLE_CONFIG, "concept_a", variation_keys=["varA"], global_style_keys=["cinematic"])
        self.assertIsNotNone(result)
        variation_text = SAMPLE_CONFIG["concepts"]["concept_a"]["variations"]["varA"]
        style_text = SAMPLE_CONFIG["global_styles"]["cinematic"]
        # Expect variation text then global style text before technical params
        expected_prompt = f"test prompt base {variation_text} {style_text} --ar 8:11 --q 1 --v 6"
        self.assertEqual(result['prompt'], expected_prompt)
        self.assertEqual(result['variations'], ["varA"])
        self.assertEqual(result['global_styles'], ["cinematic"])

    # --- Tests for save_text_prompt --- #

    @patch('cell_cover.utils.prompt.os.makedirs')
    @patch('cell_cover.utils.prompt.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_prompt_no_variation(self, mock_file, mock_exists, mock_makedirs):
        """Test saving a prompt file without variations."""
        mock_exists.return_value = True # Simulate directory exists
        output_dir = "/fake/output"
        prompt_text = "test prompt content"
        concept = "concept_a"

        filepath = save_text_prompt(self.mock_logger, output_dir, prompt_text, concept)

        self.assertIsNotNone(filepath)
        self.assertTrue(filepath.startswith(os.path.join(output_dir, f"{concept}_prompt_")))
        self.assertTrue(filepath.endswith(".txt"))
        mock_exists.assert_called_once_with(output_dir)
        mock_makedirs.assert_not_called() # Dir exists
        mock_file.assert_called_once_with(filepath, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(prompt_text)

    @patch('cell_cover.utils.prompt.os.makedirs')
    @patch('cell_cover.utils.prompt.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_prompt_multiple_variations(self, mock_file, mock_exists, mock_makedirs):
        """Test saving a prompt file with multiple variations."""
        mock_exists.return_value = False # Simulate directory does not exist
        output_dir = "/fake/output/prompts"
        prompt_text = "multi var prompt"
        concept = "concept_a"
        variations = ["varA", "varB"]

        filepath = save_text_prompt(self.mock_logger, output_dir, prompt_text, concept, variation_keys=variations)

        self.assertIsNotNone(filepath)
        expected_filename_part = f"{concept}_varA-varB_prompt_"
        self.assertTrue(os.path.basename(filepath).startswith(expected_filename_part))
        mock_exists.assert_called_once_with(output_dir)
        mock_makedirs.assert_called_once_with(output_dir)
        mock_file.assert_called_once_with(filepath, 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(prompt_text)

    @patch('cell_cover.utils.prompt.os.makedirs', side_effect=OSError("Permission denied"))
    @patch('cell_cover.utils.prompt.os.path.exists', return_value=False)
    def test_save_prompt_makedirs_fails(self, mock_exists, mock_makedirs):
        """Test save_prompt when creating directory fails."""
        filepath = save_text_prompt(self.mock_logger, "/cant/create", "text", "concept")
        self.assertIsNone(filepath)
        self.mock_logger.error.assert_called_once()

    @patch('cell_cover.utils.prompt.os.makedirs')
    @patch('cell_cover.utils.prompt.os.path.exists', return_value=True)
    @patch('builtins.open', side_effect=IOError("Disk full"))
    def test_save_prompt_write_fails(self, mock_file, mock_exists, mock_makedirs):
        """Test save_prompt when writing file fails."""
        filepath = save_text_prompt(self.mock_logger, "/fake/dir", "text", "concept")
        self.assertIsNone(filepath)
        self.mock_logger.error.assert_called_once()

    # --- Tests for copy_to_clipboard --- #

    @patch('cell_cover.utils.prompt.pyperclip.copy')
    @patch('cell_cover.utils.prompt.PYPERCLIP_AVAILABLE', True)
    def test_copy_to_clipboard_success(self, mock_pyperclip_copy):
        """Test successful copy to clipboard when available."""
        text_to_copy = "copy me"
        result = copy_to_clipboard(self.mock_logger, text_to_copy)
        self.assertTrue(result)
        mock_pyperclip_copy.assert_called_once_with(text_to_copy)

    @patch('cell_cover.utils.prompt.pyperclip.copy', side_effect=Exception("Clipboard error"))
    @patch('cell_cover.utils.prompt.PYPERCLIP_AVAILABLE', True)
    def test_copy_to_clipboard_failure(self, mock_pyperclip_copy):
        """Test copy failure when pyperclip raises an error."""
        result = copy_to_clipboard(self.mock_logger, "copy me")
        self.assertFalse(result)
        self.mock_logger.error.assert_called_once_with("无法复制到剪贴板: Clipboard error")

    @patch('cell_cover.utils.prompt.pyperclip.copy')
    @patch('cell_cover.utils.prompt.PYPERCLIP_AVAILABLE', False)
    def test_copy_to_clipboard_not_available(self, mock_pyperclip_copy):
        """Test copy behavior when pyperclip is not available."""
        with patch('builtins.print') as mock_print:
            result = copy_to_clipboard(self.mock_logger, "copy me")
            self.assertFalse(result)
            mock_pyperclip_copy.assert_not_called()
            self.mock_logger.warning.assert_called_once_with("警告: pyperclip 模块不可用，无法复制到剪贴板。")
            mock_print.assert_any_call("警告: pyperclip 模块不可用，无法复制到剪贴板。")

if __name__ == '__main__':
    unittest.main(verbosity=2) 