import pytest
from fastmcp import FastMCP
from unittest.mock import patch, MagicMock
import image_gen_mcp.core.server as server_module

class TestServer:
    def test_create_server_returns_fastmcp_instance(self):
        """Test that create_server returns a FastMCP instance."""
        server = server_module.create_server()
        assert isinstance(server, FastMCP)
        assert server.name == "Image Generator MCP Server"

    @patch('image_gen_mcp.core.server.importlib.import_module')
    def test_load_plugins_calls_register(self, mock_import_module):
        """Test that _load_plugins calls register on valid plugins."""
        # We patch pkgutil.iter_modules specifically on the server module's imported pkgutil
        with patch.object(server_module.pkgutil, 'iter_modules') as mock_iter_modules:
            # Setup mock to simulate finding a plugin
            mock_iter_modules.return_value = [(None, "test_plugin_12345", True)]
            
            # Setup mock for the imported module
            mock_module = MagicMock()
            mock_import_module.return_value = mock_module
            
            # Test create_server
            server_module.create_server()
            
            # Verify import_module was called with the correct fully qualified name
            mock_import_module.assert_called_with("image_gen_mcp.apps.test_plugin_12345")
            
            # Verify register was called
            mock_module.register.assert_called_once()

    @patch('image_gen_mcp.core.server.importlib.import_module')
    def test_load_plugins_skips_invalid_plugins(self, mock_import_module):
        """Test that _load_plugins handles plugins without register function gracefully."""
        with patch.object(server_module.pkgutil, 'iter_modules') as mock_iter_modules:
            mock_iter_modules.return_value = [(None, "bad_plugin", True)]
            
            mock_module = MagicMock()
            del mock_module.register # Ensure no register attribute
            mock_import_module.return_value = mock_module
            
            # Should not raise exception
            server_module.create_server()
            
            # Verify import occurred but nothing else happened
            mock_import_module.assert_called_with("image_gen_mcp.apps.bad_plugin")

    @patch('image_gen_mcp.core.server.importlib.import_module')
    def test_load_plugins_handles_import_error(self, mock_import_module):
        """Test that _load_plugins logs errors when import fails."""
        with patch.object(server_module.pkgutil, 'iter_modules') as mock_iter_modules, \
             patch.object(server_module, 'logger') as mock_logger:
            mock_iter_modules.return_value = [(None, "broken_plugin", True)]
            mock_import_module.side_effect = ImportError("Broken")
            
            server_module.create_server()
            
            # Verify error was logged
            mock_logger.error.assert_called()
