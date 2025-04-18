import unittest
import os
import sys
import shutil
import json
import importlib
import glob
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

# Use patch.dict to simulate setting environment variables for the duration of the test class
@patch.dict(os.environ, {"TTAPI_API_KEY": DUMMY_API_KEY}, clear=True)
@patch('cell_cover.utils.config.load_config', return_value=SAMPLE_CONFIG_DATA) # Patch config loading
class TestGenerateCommand(unittest.TestCase):

    def setUp(self):
        """Set up before each test method."""
        # Clean and create necessary directories used by the script
        for dir_path in [IMAGE_DIR, META_DIR, LOG_DIR, OUTPUT_DIR]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)

    def tearDown(self):
        """Clean up after each test method."""
        # Clean directories again to ensure isolation
        for dir_path in [IMAGE_DIR, META_DIR, LOG_DIR, OUTPUT_DIR]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)

    @patch('cell_cover.utils.api.requests.post')
    @patch('cell_cover.utils.file_handler.requests.get')
    @patch('cell_cover.utils.api.time.sleep', return_value=None) # Mock sleep in polling
    @patch('cell_cover.utils.prompt.pyperclip.copy', return_value=None) # Mock clipboard
    def test_generate_single_variation_sync(self, mock_pyperclip, mock_sleep, mock_requests_get, mock_requests_post, mock_load_config):
        """Test generating an image with a single variation in sync mode."""
        print("\n--- test_generate_single_variation_sync ---")
        # Configure mock responses
        mock_requests_post.side_effect = [
            mock_imagine_success,    # Response to /imagine
            mock_fetch_pending,      # First response to /fetch (polling)
            mock_fetch_success_sync  # Second response to /fetch (polling)
        ]
        mock_requests_get.return_value = mock_download_success # Response to image download

        # --- Execute script's main function --- #
        # Save original sys.argv
        original_argv = sys.argv
        # Set command line arguments for the test, INCLUDING the 'create' command
        sys.argv = [
            'generate_cover.py',
            'create',            # <-- Add the subcommand here
            '-c', 'concept_a',
            '-var', 'varA',
            '--save-prompt'
        ]

        try:
            # Reload the module to pick up patches if necessary (might not be needed with direct call)
            importlib.reload(generate_cover)
            generate_cover.main()
        except SystemExit as e:
            # Sync mode with successful fetch should not exit with error code
            self.assertIsNone(e.code, f"Script exited unexpectedly with code {e.code}")
        except Exception as e:
            self.fail(f"Script failed with exception: {e}")
        finally:
            # Restore original sys.argv
            sys.argv = original_argv

        # --- Assertions --- #
        # Verify load_config was called (implicitly, by the script startup)
        # We patched it at the class level, so it's always called with the fixture data
        # mock_load_config.assert_called() # This assertion isn't strictly needed unless we check args

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

        # Verify image file creation
        image_files = glob.glob(os.path.join(IMAGE_DIR, "concept_a_varA_image_*.png"))
        self.assertEqual(len(image_files), 1, "Expected one image file to be created")

        # Verify metadata file creation and content
        self.assertTrue(os.path.exists(META_FILE), "Metadata file should be created")
        with open(META_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        self.assertEqual(len(metadata['images']), 1, "Expected one entry in metadata")
        img_meta = metadata['images'][0]
        self.assertEqual(img_meta['concept'], 'concept_a')
        self.assertEqual(img_meta['variations'], ['varA'])
        self.assertEqual(img_meta['job_id'], 'mock_job_123')
        self.assertEqual(img_meta['seed'], '12345')
        self.assertEqual(img_meta['url'], "http://mock.url/image_sync.png")
        self.assertTrue(img_meta['filename'].startswith("concept_a_varA_image_"))

        # Verify prompt file creation
        prompt_files = glob.glob(os.path.join(OUTPUT_DIR, "concept_a_varA_prompt_*.txt"))
        self.assertEqual(len(prompt_files), 1, "Expected one prompt file to be created")
        with open(prompt_files[0], 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        self.assertEqual(prompt_content, "test prompt base with variation A --ar 8:11 --q 1 --v 6")

    @patch('cell_cover.utils.api.requests.post')
    @patch('cell_cover.utils.file_handler.requests.get')
    @patch('cell_cover.utils.api.time.sleep', return_value=None)
    @patch('cell_cover.utils.prompt.pyperclip.copy', return_value=None)
    def test_generate_multiple_variations_async(self, mock_pyperclip, mock_sleep, mock_requests_get, mock_requests_post, mock_load_config):
        """Test generating an image with multiple variations in async mode."""
        print("\n--- test_generate_multiple_variations_async ---")
        # Configure mock responses
        mock_requests_post.return_value = mock_imagine_success # Only imagine is called in async

        # --- Execute script's main function --- #
        original_argv = sys.argv
        # Set command line arguments for the test, INCLUDING the 'create' command
        sys.argv = [
            'generate_cover.py',
            'create',            # <-- Add the subcommand here
            '-c', 'concept_a',
            '-var', 'varA', 'varB',
            '--hook-url', 'http://mock-webhook.com/notify' # Enable async
        ]

        try:
            importlib.reload(generate_cover)
            generate_cover.main()
        except SystemExit as e:
            # Async mode should exit gracefully (code None) without errors
            self.assertIsNone(e.code, f"Async script exited with unexpected code {e.code}")
        except Exception as e:
            self.fail(f"Script failed with exception: {e}")
        finally:
            sys.argv = original_argv

        # --- Assertions --- #
        # Verify load_config was called
        # mock_load_config.assert_called()

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

        # Verify no image or metadata files were created locally
        image_files = glob.glob(os.path.join(IMAGE_DIR, "*.png"))
        self.assertEqual(len(image_files), 0, "No image file should be created in async mode")
        self.assertFalse(os.path.exists(META_FILE), "Metadata file should not be created in async mode")

if __name__ == '__main__':
    # Running with unittest discovery is preferred
    # This allows running individual tests via CLI
    unittest.main(verbosity=2) 