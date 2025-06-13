#!/usr/bin/env python

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add the weave modules to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from modules.mcp_config import (
    load_weave_config,
    save_weave_config,
    add_mcp_server_to_config,
    remove_mcp_server_from_config,
    list_mcp_servers_from_config,
    get_mcp_servers_from_config
)

from modules.mcp_sync import (
    get_existing_mcp_servers,
    create_mcp_server_in_litellm,
    sync_mcp_servers_to_litellm,
    wait_for_litellm_service
)


class TestMCPConfig(unittest.TestCase):
    """Test MCP configuration management functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config = {
            "project_name": "test-project",
            "mcp_servers": {
                "webcat": {
                    "url": "http://webcat:8765/mcp",
                    "transport": "sse",
                    "spec_version": "2024-11-05",
                    "description": "Test WebCat server",
                    "env": {
                        "API_KEY": "test-key"
                    }
                }
            }
        }
        
        self.empty_config = {
            "project_name": "test-project"
        }
    
    @patch('modules.mcp_config.get_weave_config_path')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_weave_config_success(self, mock_file, mock_path):
        """Test successful loading of weave config"""
        mock_path.return_value = Path("/test/config.json")
        mock_file.return_value.read.return_value = json.dumps(self.test_config)
        
        with patch('pathlib.Path.exists', return_value=True):
            config = load_weave_config()
            
        self.assertEqual(config, self.test_config)
        mock_file.assert_called_once()
    
    @patch('modules.mcp_config.get_weave_config_path')
    def test_load_weave_config_file_not_found(self, mock_path):
        """Test loading config when file doesn't exist"""
        mock_path.return_value = Path("/nonexistent/config.json")
        
        with patch('pathlib.Path.exists', return_value=False):
            config = load_weave_config()
            
        self.assertEqual(config, {})
    
    @patch('modules.mcp_config.load_weave_config')
    @patch('modules.mcp_config.save_weave_config')
    def test_add_mcp_server_to_config_new_server(self, mock_save, mock_load):
        """Test adding a new MCP server to config"""
        mock_load.return_value = self.empty_config.copy()
        mock_save.return_value = True
        
        result = add_mcp_server_to_config(
            server_name="test-server",
            url="http://test:8080/mcp",
            transport="sse",
            spec_version="2024-11-05",
            description="Test server",
            env_vars={"KEY": "value"}
        )
        
        self.assertTrue(result)
        mock_save.assert_called_once()
        
        # Check the config that was saved
        saved_config = mock_save.call_args[0][0]
        self.assertIn("mcp_servers", saved_config)
        self.assertIn("test-server", saved_config["mcp_servers"])
        
        server_config = saved_config["mcp_servers"]["test-server"]
        self.assertEqual(server_config["url"], "http://test:8080/mcp")
        self.assertEqual(server_config["transport"], "sse")
        self.assertEqual(server_config["description"], "Test server")
        self.assertEqual(server_config["env"], {"KEY": "value"})
    
    @patch('modules.mcp_config.load_weave_config')
    @patch('modules.mcp_config.save_weave_config')
    def test_add_mcp_server_existing_without_force(self, mock_save, mock_load):
        """Test adding an existing MCP server without force flag"""
        mock_load.return_value = self.test_config.copy()
        
        result = add_mcp_server_to_config(
            server_name="webcat",
            url="http://new:8080/mcp",
            force=False
        )
        
        self.assertFalse(result)
        mock_save.assert_not_called()
    
    @patch('modules.mcp_config.load_weave_config')
    @patch('modules.mcp_config.save_weave_config')
    def test_add_mcp_server_existing_with_force(self, mock_save, mock_load):
        """Test adding an existing MCP server with force flag"""
        mock_load.return_value = self.test_config.copy()
        mock_save.return_value = True
        
        result = add_mcp_server_to_config(
            server_name="webcat",
            url="http://new:8080/mcp",
            description="Updated server",
            force=True
        )
        
        self.assertTrue(result)
        mock_save.assert_called_once()
        
        # Check the config was updated
        saved_config = mock_save.call_args[0][0]
        server_config = saved_config["mcp_servers"]["webcat"]
        self.assertEqual(server_config["url"], "http://new:8080/mcp")
        self.assertEqual(server_config["description"], "Updated server")
    
    @patch('modules.mcp_config.load_weave_config')
    @patch('modules.mcp_config.save_weave_config')
    def test_add_mcp_server_with_auth_type(self, mock_save, mock_load):
        """Test adding an MCP server with auth_type"""
        mock_load.return_value = self.empty_config.copy()
        mock_save.return_value = True
        
        result = add_mcp_server_to_config(
            server_name="secure-api",
            url="https://api.example.com/mcp",
            auth_type="bearer_token",
            description="Secure API server",
            env_vars={"BEARER_TOKEN": "secret123"}
        )
        
        self.assertTrue(result)
        mock_save.assert_called_once()
        
        # Check the config that was saved
        saved_config = mock_save.call_args[0][0]
        server_config = saved_config["mcp_servers"]["secure-api"]
        self.assertEqual(server_config["auth_type"], "bearer_token")
        self.assertEqual(server_config["env"]["BEARER_TOKEN"], "secret123")
    
    @patch('modules.mcp_config.load_weave_config')
    @patch('modules.mcp_config.save_weave_config')
    def test_remove_mcp_server_success(self, mock_save, mock_load):
        """Test successful removal of MCP server"""
        mock_load.return_value = self.test_config.copy()
        mock_save.return_value = True
        
        result = remove_mcp_server_from_config("webcat")
        
        self.assertTrue(result)
        mock_save.assert_called_once()
        
        # Check the server was removed
        saved_config = mock_save.call_args[0][0]
        self.assertNotIn("webcat", saved_config["mcp_servers"])
    
    @patch('modules.mcp_config.load_weave_config')
    def test_remove_mcp_server_not_found(self, mock_load):
        """Test removing a non-existent MCP server"""
        mock_load.return_value = self.test_config.copy()
        
        result = remove_mcp_server_from_config("nonexistent")
        
        self.assertFalse(result)
    
    @patch('modules.mcp_config.load_weave_config')
    def test_get_mcp_servers_from_config(self, mock_load):
        """Test getting MCP servers from config"""
        mock_load.return_value = self.test_config.copy()
        
        servers = get_mcp_servers_from_config()
        
        self.assertEqual(servers, self.test_config["mcp_servers"])
    
    @patch('modules.mcp_config.load_weave_config')
    def test_get_mcp_servers_from_config_empty(self, mock_load):
        """Test getting MCP servers from config when none exist"""
        mock_load.return_value = self.empty_config.copy()
        
        servers = get_mcp_servers_from_config()
        
        self.assertEqual(servers, {})


class TestMCPSync(unittest.TestCase):
    """Test MCP synchronization functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_servers = {
            "webcat": {
                "url": "http://webcat:8765/mcp",
                "transport": "sse",
                "spec_version": "2024-11-05",
                "description": "Test WebCat server",
                "env": {"API_KEY": "test-key"}
            }
        }
        
        self.litellm_response = [
            {
                "server_id": "test-id-123",
                "alias": "webcat",
                "url": "http://webcat:8765/mcp",
                "description": "Test WebCat server"
            }
        ]
    
    @patch('requests.get')
    def test_wait_for_litellm_service_success(self, mock_get):
        """Test successful wait for LiteLLM service"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = wait_for_litellm_service("http://test:4000", timeout=1, interval=1)
        
        self.assertTrue(result)
        mock_get.assert_called_with("http://test:4000/health", timeout=5)
    
    @patch('requests.get')
    @patch('time.sleep')
    def test_wait_for_litellm_service_timeout(self, mock_sleep, mock_get):
        """Test timeout when waiting for LiteLLM service"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
        
        result = wait_for_litellm_service("http://test:4000", timeout=1, interval=1)
        
        self.assertFalse(result)
    
    @patch('requests.get')
    def test_get_existing_mcp_servers_success(self, mock_get):
        """Test successful retrieval of existing MCP servers"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.litellm_response
        mock_get.return_value = mock_response
        
        servers = get_existing_mcp_servers("http://test:4000", "test-key")
        
        self.assertEqual(servers, self.litellm_response)
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_existing_mcp_servers_error(self, mock_get):
        """Test error handling when retrieving existing MCP servers"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
        
        servers = get_existing_mcp_servers("http://test:4000", "test-key")
        
        self.assertEqual(servers, [])
    
    @patch('requests.post')
    def test_create_mcp_server_success(self, mock_post):
        """Test successful creation of MCP server in LiteLLM"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        server_config = self.test_servers["webcat"]
        result = create_mcp_server_in_litellm(
            "http://test:4000", "test-key", "webcat", server_config
        )
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check the request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['alias'], 'webcat')
        self.assertEqual(payload['url'], 'http://webcat:8765/mcp')
        self.assertEqual(payload['transport'], 'sse')
    
    @patch('requests.post')
    def test_create_mcp_server_with_auth_type(self, mock_post):
        """Test successful creation of MCP server with auth_type"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        server_config = {
            "url": "https://api.example.com/mcp",
            "transport": "sse",
            "spec_version": "2024-11-05",
            "description": "Secure API server",
            "auth_type": "bearer_token",
            "env": {"BEARER_TOKEN": "secret123"}
        }
        
        result = create_mcp_server_in_litellm(
            "http://test:4000", "test-key", "secure-api", server_config
        )
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check the request payload includes auth_type
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['alias'], 'secure-api')
        self.assertEqual(payload['auth_type'], 'bearer_token')
    
    @patch('requests.post')
    def test_create_mcp_server_error(self, mock_post):
        """Test error handling when creating MCP server"""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("API Error")
        
        server_config = self.test_servers["webcat"]
        result = create_mcp_server_in_litellm(
            "http://test:4000", "test-key", "webcat", server_config
        )
        
        self.assertFalse(result)
    
    @patch('modules.mcp_sync.get_mcp_servers_from_config')
    @patch('modules.mcp_sync.get_existing_mcp_servers')
    @patch('modules.mcp_sync.create_mcp_server_in_litellm')
    def test_sync_mcp_servers_create_new(self, mock_create, mock_get_existing, mock_get_config):
        """Test syncing when creating new servers"""
        mock_get_config.return_value = self.test_servers
        mock_get_existing.return_value = []
        mock_create.return_value = True
        
        result = sync_mcp_servers_to_litellm("http://test:4000", "test-key")
        
        self.assertTrue(result)
        mock_create.assert_called_once_with(
            "http://test:4000", "test-key", "webcat", self.test_servers["webcat"]
        )
    
    @patch('modules.mcp_sync.get_mcp_servers_from_config')
    def test_sync_mcp_servers_no_config(self, mock_get_config):
        """Test syncing when no servers are configured"""
        mock_get_config.return_value = {}
        
        result = sync_mcp_servers_to_litellm("http://test:4000", "test-key")
        
        self.assertTrue(result)  # Should succeed with no action
    
    @patch('modules.mcp_sync.get_mcp_servers_from_config')
    @patch('modules.mcp_sync.get_existing_mcp_servers')
    def test_sync_mcp_servers_dry_run(self, mock_get_existing, mock_get_config):
        """Test dry run mode of sync"""
        mock_get_config.return_value = self.test_servers
        mock_get_existing.return_value = []
        
        result = sync_mcp_servers_to_litellm(
            "http://test:4000", "test-key", dry_run=True
        )
        
        self.assertTrue(result)


class TestMCPIntegration(unittest.TestCase):
    """Integration tests for MCP management"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        
        # Create a test config file
        test_config = {
            "project_name": "test-project",
            "mcp_servers": {
                "webcat": {
                    "url": "http://webcat:8765/mcp",
                    "transport": "sse",
                    "spec_version": "2024-11-05",
                    "description": "Test WebCat server"
                }
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('modules.mcp_config.get_weave_config_path')
    def test_full_config_workflow(self, mock_path):
        """Test the full configuration workflow"""
        mock_path.return_value = Path(self.config_file)
        
        # Load config
        config = load_weave_config()
        self.assertIn("mcp_servers", config)
        self.assertIn("webcat", config["mcp_servers"])
        
        # Add a new server
        result = add_mcp_server_to_config(
            "filesystem",
            "http://filesystem:8766/mcp",
            description="Filesystem server"
        )
        self.assertTrue(result)
        
        # Verify it was added
        updated_config = load_weave_config()
        self.assertIn("filesystem", updated_config["mcp_servers"])
        
        # Remove a server
        result = remove_mcp_server_from_config("webcat")
        self.assertTrue(result)
        
        # Verify it was removed
        final_config = load_weave_config()
        self.assertNotIn("webcat", final_config["mcp_servers"])
        self.assertIn("filesystem", final_config["mcp_servers"])


if __name__ == '__main__':
    # Set up test environment
    os.environ['WEAVE_TEST_MODE'] = 'true'
    
    # Run tests
    unittest.main(verbosity=2) 