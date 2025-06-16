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