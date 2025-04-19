import unittest
import os
import sys
import shutil
import json
import importlib
import glob
import tempfile
from unittest.mock import patch, MagicMock, call

# --- Path Setup --- #
# Add the project root directory (paper) to the Python path
# This allows importing 'cell_cover' as a package
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
INTEGRATION_DIR = os.path.dirname(TEST_DIR)
CELL_COVER_DIR = os.path.dirname(INTEGRATION_DIR)
PROJECT_ROOT = os.path.dirname(CELL_COVER_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ------------------ #

# Now we can import using the package structure
from cell_cover.tests.helpers.mock_responses import (
    MockResponse, mock_imagine_success, mock_fetch_success_sync,
    mock_fetch_pending, mock_download_success
)
# Import the main script module directly
import cell_cover.generate_cover as generate_cover

# Paths used by the script being tested (relative to CELL_COVER_DIR)
# These are determined relative to the main generate_cover module location
MODULE_DIR = os.path.dirname(generate_cover.__file__)
IMAGE_DIR = os.path.join(MODULE_DIR, "images")
META_DIR = os.path.join(MODULE_DIR, "metadata")
META_FILE = os.path.join(META_DIR, "images_metadata.json")
LOG_DIR = os.path.join(MODULE_DIR, "logs")
OUTPUT_DIR = os.path.join(MODULE_DIR, "outputs")
CONFIG_FILENAME = "prompts_config.json"

# Path to the sample config in fixtures (relative to this test file)
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
SAMPLE_CONFIG_PATH = os.path.join(FIXTURES_DIR, "sample_config.json")
# Path where the script expects the config (relative to the script's dir)
SCRIPT_CONFIG_PATH = os.path.join(MODULE_DIR, CONFIG_FILENAME)

# Load the sample config data ONCE for use in patching
try:
    with open(SAMPLE_CONFIG_PATH, 'r', encoding='utf-8') as f:
        SAMPLE_CONFIG_DATA = json.load(f)
except FileNotFoundError:
    print(f"ERROR: Sample config fixture not found at {SAMPLE_CONFIG_PATH}")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"ERROR: Sample config fixture at {SAMPLE_CONFIG_PATH} is not valid JSON.")
    sys.exit(1)

DUMMY_API_KEY = "dummy_test_key"

# Use patch.dict for environment variables
# Patch load_config WHERE IT IS USED (in generate_cover module)
@patch.dict(os.environ, {"TTAPI_API_KEY": DUMMY_API_KEY}, clear=True)
@patch('cell_cover.generate_cover.load_config', return_value=SAMPLE_CONFIG_DATA) # Correct patch target
class TestGenerateCommand(unittest.TestCase):

    def setUp(self):
        """Set up before each test method."""
        # Create a temporary directory for this test run
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir_obj.name
        # Create subdirs within the temp dir if needed (though script should handle it)
        os.makedirs(os.path.join(self.temp_dir_path, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir_path, "metadata"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir_path, "logs"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir_path, "outputs"), exist_ok=True)
        # NO longer touching real directories

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up the temporary directory and all its contents
        self.temp_dir_obj.cleanup()
        # NO longer touching real directories

    @patch('cell_cover.utils.api.requests.post')
    @patch('cell_cover.utils.file_handler.requests.get')
    @patch('cell_cover.utils.api.time.sleep', return_value=None) # Mock sleep in polling
    @patch('cell_cover.utils.prompt.pyperclip.copy', return_value=None) # Mock clipboard
    @patch('cell_cover.utils.file_handler.IMAGE_DIR')
    @patch('cell_cover.utils.file_handler.META_DIR')
    @patch('cell_cover.utils.file_handler.META_FILE')
    @patch('cell_cover.utils.file_handler.OUTPUT_DIR')
    @patch('cell_cover.generate_cover.OUTPUT_DIR') # Patched where imported in main
    @patch('cell_cover.generate_cover.SCRIPT_DIR') # Patch script dir used for logging base
    def test_generate_single_variation_sync(self,
                                            mock_script_dir, mock_gen_output_dir,
                                            mock_fh_output_dir, mock_fh_meta_file,
                                            mock_fh_meta_dir, mock_fh_image_dir,
                                            mock_pyperclip, mock_sleep,
                                            mock_requests_get, mock_requests_post,
                                            mock_load_config): # mock_load_config from class patch
        """Test generating an image with a single variation in sync mode."""
        # --- Configure Patched Paths --- #
        temp_image_dir = os.path.join(self.temp_dir_path, "images")
        temp_meta_dir = os.path.join(self.temp_dir_path, "metadata")
        temp_meta_file = os.path.join(temp_meta_dir, "images_metadata.json")
        temp_output_dir = os.path.join(self.temp_dir_path, "outputs")
        # Assign the correct temp paths to the mocked constants
        mock_fh_image_dir.return_value = temp_image_dir
        mock_fh_meta_dir.return_value = temp_meta_dir
        mock_fh_meta_file.return_value = temp_meta_file
        mock_fh_output_dir.return_value = temp_output_dir
        mock_gen_output_dir.return_value = temp_output_dir
        mock_script_dir.return_value = self.temp_dir_path # Log dir will be based on this temp dir

        print("\n--- test_generate_single_variation_sync (using temp dir) ---")
        # Configure mock API responses
        mock_requests_post.side_effect = [
            mock_imagine_success, mock_fetch_pending, mock_fetch_success_sync
        ]
        mock_requests_get.return_value = mock_download_success

        # --- Execute script's main function --- #
        original_argv = sys.argv
        sys.argv = [
            'generate_cover.py', 'create', '-c', 'concept_a', '-var', 'varA', '--save-prompt'
        ]
        try:
            generate_cover.main()
        except SystemExit as e:
            self.assertIsNone(e.code, f"Script exited unexpectedly with code {e.code}")
        except Exception as e:
            self.fail(f"Script failed with exception: {e}")
        finally:
            sys.argv = original_argv

        # --- Assertions --- #
        # Verify API calls
        self.assertEqual(mock_requests_post.call_count, 3, "Expected 3 POST calls (imagine + 2 fetch)")
        imagine_call = mock_requests_post.call_args_list[0]
        fetch_call_1 = mock_requests_post.call_args_list[1]
        fetch_call_2 = mock_requests_post.call_args_list[2]

        self.assertTrue(imagine_call.args[0].endswith('/imagine'))
        self.assertEqual(imagine_call.kwargs['json']['prompt'], "test prompt base with variation A --ar 8:11 --q 1 --v 6")
        self.assertEqual(imagine_call.kwargs['json']['mode'], "fast") # Default mode

        self.assertTrue(fetch_call_1.args[0].endswith('/fetch'))
        self.assertEqual(fetch_call_1.kwargs['json']['jobId'], "mock_job_123")

        self.assertTrue(fetch_call_2.args[0].endswith('/fetch'))
        self.assertEqual(fetch_call_2.kwargs['json']['jobId'], "mock_job_123")

        # Verify download call
        mock_requests_get.assert_called_once_with("http://mock.url/image_sync.png", stream=True, timeout=60)

        # Verify files were created in the TEMP directory
        image_files = glob.glob(os.path.join(temp_image_dir, "concept_a_varA_image_*.png"))
        self.assertEqual(len(image_files), 1, f"Expected one image file in temp dir {temp_image_dir}")
        self.assertTrue(os.path.exists(temp_meta_file), f"Metadata file should be created in temp dir {temp_meta_dir}")
        with open(temp_meta_file, 'r', encoding='utf-8') as f:
             metadata = json.load(f)
        self.assertEqual(len(metadata['images']), 1)
        # Check filepath in metadata points to the temp directory
        self.assertTrue(metadata['images'][0]['filepath'].startswith(temp_image_dir))

        prompt_files = glob.glob(os.path.join(temp_output_dir, "concept_a_varA_prompt_*.txt"))
        self.assertEqual(len(prompt_files), 1, f"Expected one prompt file in temp dir {temp_output_dir}")
        with open(prompt_files[0], 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        self.assertEqual(prompt_content, "test prompt base with variation A --ar 8:11 --q 1 --v 6")

    @patch('cell_cover.utils.api.requests.post')
    @patch('cell_cover.utils.file_handler.requests.get')
    @patch('cell_cover.utils.api.time.sleep', return_value=None)
    @patch('cell_cover.utils.prompt.pyperclip.copy', return_value=None)
    @patch('cell_cover.utils.file_handler.IMAGE_DIR')
    @patch('cell_cover.utils.file_handler.META_DIR')
    @patch('cell_cover.utils.file_handler.META_FILE')
    @patch('cell_cover.utils.file_handler.OUTPUT_DIR')
    @patch('cell_cover.generate_cover.OUTPUT_DIR') # Patched where imported in main
    @patch('cell_cover.generate_cover.SCRIPT_DIR') # Patch script dir used for logging base
    def test_generate_multiple_variations_async(self,
                                             mock_script_dir, mock_gen_output_dir,
                                             mock_fh_output_dir, mock_fh_meta_file,
                                             mock_fh_meta_dir, mock_fh_image_dir,
                                             mock_pyperclip, mock_sleep,
                                             mock_requests_get, mock_requests_post,
                                             mock_load_config):
        """Test generating an image with multiple variations in async mode."""
         # --- Configure Patched Paths --- #
        temp_image_dir = os.path.join(self.temp_dir_path, "images")
        temp_meta_dir = os.path.join(self.temp_dir_path, "metadata")
        temp_meta_file = os.path.join(temp_meta_dir, "images_metadata.json")
        temp_output_dir = os.path.join(self.temp_dir_path, "outputs")
        # Assign the correct temp paths to the mocked constants
        mock_fh_image_dir.return_value = temp_image_dir
        mock_fh_meta_dir.return_value = temp_meta_dir
        mock_fh_meta_file.return_value = temp_meta_file
        mock_fh_output_dir.return_value = temp_output_dir
        mock_gen_output_dir.return_value = temp_output_dir
        mock_script_dir.return_value = self.temp_dir_path # Log dir will be based on this temp dir

        print("\n--- test_generate_multiple_variations_async (using temp dir) ---")
        # Configure mock API responses
        mock_requests_post.return_value = mock_imagine_success

        # --- Execute script's main function --- #
        original_argv = sys.argv
        sys.argv = [
            'generate_cover.py', 'create', '-c', 'concept_a', '-var', 'varA', 'varB', '--hook-url', 'http://mock-webhook.com/notify'
        ]
        try:
            generate_cover.main()
        except SystemExit as e:
            self.assertIsNone(e.code, f"Async script exited with unexpected code {e.code}")
        except Exception as e:
            self.fail(f"Script failed with exception: {e}")
        finally:
            sys.argv = original_argv

        # --- Assertions --- #
        # Verify API call (only imagine)
        self.assertEqual(mock_requests_post.call_count, 1, "Expected 1 POST call (imagine)")
        imagine_call = mock_requests_post.call_args_list[0]

        self.assertTrue(imagine_call.args[0].endswith('/imagine'))
        # Check prompt includes both variations
        self.assertEqual(imagine_call.kwargs['json']['prompt'], "test prompt base with variation A plus variation B --ar 8:11 --q 1 --v 6")
        self.assertEqual(imagine_call.kwargs['json']['mode'], "fast")
        # Check hook URL is passed
        self.assertEqual(imagine_call.kwargs['json']['hookUrl'], "http://mock-webhook.com/notify")

        # Verify no download was attempted
        mock_requests_get.assert_not_called()

        # Verify NO files were created in the TEMP directory
        image_files = glob.glob(os.path.join(temp_image_dir, "*.png"))
        self.assertEqual(len(image_files), 0, f"No image file should be created in temp dir {temp_image_dir} in async mode")
        self.assertFalse(os.path.exists(temp_meta_file), f"Metadata file should not be created in temp dir {temp_meta_dir} in async mode")

if __name__ == '__main__':
    # Running with unittest discovery is preferred
    # This allows running individual tests via CLI
    unittest.main(verbosity=2) 