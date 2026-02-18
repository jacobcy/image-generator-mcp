import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock

# --- Path Setup --- #
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
# tests/apps/cell_cover/test_integration
APPS_TEST_DIR = os.path.dirname(TEST_DIR)
# tests/apps/cell_cover
TESTS_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(APPS_TEST_DIR)))
# project_root
if TESTS_ROOT not in sys.path:
    sys.path.insert(0, TESTS_ROOT)

from image_gen_mcp.apps.cell_cover.commands.create import handle_create

# Load sample config
FIXTURES_DIR = os.path.join(APPS_TEST_DIR, "fixtures")
SAMPLE_CONFIG_PATH = os.path.join(FIXTURES_DIR, "sample_config.json")

try:
    with open(SAMPLE_CONFIG_PATH, 'r', encoding='utf-8') as f:
        SAMPLE_CONFIG_DATA = json.load(f)
except Exception as e:
    print(f"ERROR: Could not load sample config: {e}")
    SAMPLE_CONFIG_DATA = {}

DUMMY_API_KEY = "dummy_test_key"

class TestCreateCommand(unittest.TestCase):

    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir_obj.name
        
        self.dirs = {
            'cwd': self.temp_dir_path,
            'state_dir': os.path.join(self.temp_dir_path, "state"),
            'metadata_dir': os.path.join(self.temp_dir_path, "metadata"),
            'output_dir': os.path.join(self.temp_dir_path, "output"),
        }
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
            
        self.logger = MagicMock()

    def tearDown(self):
        self.temp_dir_obj.cleanup()

    @patch('image_gen_mcp.apps.cell_cover.commands.create.check_prompt')
    @patch('image_gen_mcp.apps.cell_cover.commands.create.call_imagine_api')
    @patch('image_gen_mcp.apps.cell_cover.commands.create.poll_for_result')
    @patch('image_gen_mcp.apps.cell_cover.commands.create.download_and_save_image')
    @patch('image_gen_mcp.apps.cell_cover.commands.create.save_text_prompt')
    def test_create_sync_success(self, mock_save, mock_download, mock_poll, mock_imagine, mock_check):
        """Test happy path: sync creation with polling and download."""
        print("\n--- test_create_sync_success ---")
        
        # Setup mocks
        mock_check.return_value = True
        mock_imagine.return_value = "mock_job_123"
        mock_poll.return_value = ("SUCCESS", {"url": "http://img.com/1.png", "seed": 42})
        mock_download.return_value = (True, "/tmp/saved.png", {})

        # Run
        ret = handle_create(
            config=SAMPLE_CONFIG_DATA,
            logger=self.logger,
            api_key=DUMMY_API_KEY,
            concept="concept_a",
            variation="varA",
            mode="fast",
            cwd=self.dirs['cwd'],
            state_dir=self.dirs['state_dir'],
            metadata_dir=self.dirs['metadata_dir']
        )

        # Assertions
        self.assertEqual(ret, 0)
        mock_imagine.assert_called_once()
        mock_poll.assert_called_once_with(self.logger, "mock_job_123", DUMMY_API_KEY)
        mock_download.assert_called_once()
        
        # Verify metadata was written (submitted status)
        meta_file = os.path.join(self.dirs['metadata_dir'], "images_metadata.json")
        self.assertTrue(os.path.exists(meta_file))
        with open(meta_file, 'r') as f:
            data = json.load(f)
            # We expect at least one entry. Note: create.py writes metadata MULTIPLE times.
            # 1. submitted
            # 2. download_and_save_image (mocked) usually writes completed
            # Since we mocked download, it won't write 'completed'.
            # But 'submitted' should be there.
            self.assertTrue(len(data['images']) >= 1)
            self.assertEqual(data['images'][0]['job_id'], "mock_job_123")

    @patch('image_gen_mcp.apps.cell_cover.commands.create.check_prompt')
    @patch('image_gen_mcp.apps.cell_cover.commands.create.call_imagine_api')
    @patch('image_gen_mcp.apps.cell_cover.commands.create.poll_for_result')
    def test_create_async_hook(self, mock_poll, mock_imagine, mock_check):
        """Test async creation with hook URL."""
        print("\n--- test_create_async_hook ---")
        
        mock_check.return_value = True
        mock_imagine.return_value = "mock_job_async"

        ret = handle_create(
            config=SAMPLE_CONFIG_DATA,
            logger=self.logger,
            api_key=DUMMY_API_KEY,
            concept="concept_a",
            hook_url="http://webhook.com",
            cwd=self.dirs['cwd'],
            state_dir=self.dirs['state_dir'],
            metadata_dir=self.dirs['metadata_dir']
        )

        self.assertEqual(ret, 0)
        mock_imagine.assert_called_once()
        # Verify hook url was passed
        args, kwargs = mock_imagine.call_args
        self.assertEqual(kwargs['hook_url'], "http://webhook.com")
        
        # Should NOT poll
        mock_poll.assert_not_called()

if __name__ == '__main__':
    unittest.main()
