#!/usr/bin/env python3

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the MCP registry app
from mcp_registry.app import app, MCPRegistry, MCPServerConfig


class TestMCPRegistry(unittest.TestCase):
    """Test cases for MCPRegistry class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.json"
        
        # Sample test configuration
        self.test_config = {
            "project_name": "test-project",
            "mcp_servers": {
                "webcat": {
                    "url": "http://webcat:8765/mcp",
                    "transport": "sse",
                    "spec_version": "2024-11-05",
                    "description": "WebCat MCP Server",
                    "scope": "rag",
                    "env": {
                        "WEBCAT_API_KEY": "${WEBCAT_API_KEY}"
                    }
                },
                "filesystem": {
                    "url": "http://filesystem:8766/mcp", 
                    "transport": "sse",
                    "spec_version": "2024-11-05",
                    "description": "Filesystem MCP Server",
                    "scope": "all",
                    "env": {}
                },
                "agent-only": {
                    "url": "http://agent:8767/mcp",
                    "transport": "sse", 
                    "spec_version": "2024-11-05",
                    "description": "Agent-only MCP Server",
                    "scope": "agent",
                    "env": {}
                }
            }
        }
        
        # Write test config to file
        with open(self.config_file, 'w') as f:
            json.dump(self.test_config, f)
            
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_load_config_success(self):
        """Test successful config loading"""
        registry = MCPRegistry(str(self.config_file))
        config = registry._load_config()
        
        self.assertEqual(config, self.test_config)
        
    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist"""
        registry = MCPRegistry("/nonexistent/config.json")
        
        with self.assertRaises(Exception):
            registry._load_config()
    
    def test_load_config_invalid_json(self):
        """Test config loading with invalid JSON"""
        invalid_file = Path(self.temp_dir) / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
            
        registry = MCPRegistry(str(invalid_file))
        
        with self.assertRaises(Exception):
            registry._load_config()
    
    def test_get_mcp_servers_all(self):
        """Test getting all MCP servers"""
        registry = MCPRegistry(str(self.config_file))
        servers = registry.get_mcp_servers()
        
        self.assertEqual(len(servers), 3)
        self.assertIn("webcat", servers)
        self.assertIn("filesystem", servers)
        self.assertIn("agent-only", servers)
        
        # Check server config structure
        webcat = servers["webcat"]
        self.assertIsInstance(webcat, MCPServerConfig)
        self.assertEqual(webcat.url, "http://webcat:8765/mcp")
        self.assertEqual(webcat.scope, "rag")
    
    def test_get_mcp_servers_with_scope_filter(self):
        """Test getting MCP servers with scope filter"""
        registry = MCPRegistry(str(self.config_file))
        
        # Test RAG scope filter
        rag_servers = registry.get_mcp_servers(scope_filter=["rag"])
        self.assertEqual(len(rag_servers), 1)
        self.assertIn("webcat", rag_servers)
        
        # Test ALL scope filter
        all_servers = registry.get_mcp_servers(scope_filter=["all"])
        self.assertEqual(len(all_servers), 1)
        self.assertIn("filesystem", all_servers)
        
        # Test multiple scope filter
        rag_and_all = registry.get_mcp_servers(scope_filter=["rag", "all"])
        self.assertEqual(len(rag_and_all), 2)
        self.assertIn("webcat", rag_and_all)
        self.assertIn("filesystem", rag_and_all)
    
    def test_get_server_by_name(self):
        """Test getting specific server by name"""
        registry = MCPRegistry(str(self.config_file))
        
        # Test existing server
        webcat = registry.get_server_by_name("webcat")
        self.assertIsNotNone(webcat)
        self.assertEqual(webcat.url, "http://webcat:8765/mcp")
        
        # Test non-existing server
        nonexistent = registry.get_server_by_name("nonexistent")
        self.assertIsNone(nonexistent)
    
    def test_get_servers_by_scope(self):
        """Test getting servers by specific scope"""
        registry = MCPRegistry(str(self.config_file))
        
        rag_servers = registry.get_servers_by_scope("rag")
        self.assertEqual(len(rag_servers), 1)
        self.assertIn("webcat", rag_servers)
        
        agent_servers = registry.get_servers_by_scope("agent")
        self.assertEqual(len(agent_servers), 1)
        self.assertIn("agent-only", agent_servers)
    
    def test_get_rag_servers(self):
        """Test getting RAG servers (rag + all scopes)"""
        registry = MCPRegistry(str(self.config_file))
        
        rag_servers = registry.get_rag_servers()
        self.assertEqual(len(rag_servers), 2)
        self.assertIn("webcat", rag_servers)  # scope: rag
        self.assertIn("filesystem", rag_servers)  # scope: all
        self.assertNotIn("agent-only", rag_servers)  # scope: agent
    
    def test_health_check_healthy(self):
        """Test health check when config is healthy"""
        registry = MCPRegistry(str(self.config_file))
        
        health = registry.health_check()
        
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["config_file"], str(self.config_file))
        self.assertTrue(health["config_exists"])
        self.assertIsNotNone(health["last_modified"])
    
    def test_health_check_config_missing(self):
        """Test health check when config file is missing"""
        registry = MCPRegistry("/nonexistent/config.json")
        
        health = registry.health_check()
        
        self.assertEqual(health["status"], "degraded")
        self.assertFalse(health["config_exists"])
    
    def test_config_reloading(self):
        """Test automatic config reloading on file changes"""
        registry = MCPRegistry(str(self.config_file))
        
        # First load
        servers1 = registry.get_mcp_servers()
        self.assertEqual(len(servers1), 3)
        
        # Modify config file
        modified_config = self.test_config.copy()
        modified_config["mcp_servers"]["new-server"] = {
            "url": "http://new:8768/mcp",
            "transport": "sse",
            "spec_version": "2024-11-05", 
            "description": "New server",
            "scope": "rag",
            "env": {}
        }
        
        # Simulate file modification time change
        import time
        time.sleep(0.1)  # Ensure different timestamp
        
        with open(self.config_file, 'w') as f:
            json.dump(modified_config, f)
            
        # Second load should pick up changes
        servers2 = registry.get_mcp_servers()
        self.assertEqual(len(servers2), 4)
        self.assertIn("new-server", servers2)


class TestMCPRegistryAPI(unittest.TestCase):
    """Test cases for MCP Registry FastAPI endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.json"
        
        # Sample test configuration
        self.test_config = {
            "project_name": "test-project",
            "mcp_servers": {
                "webcat": {
                    "url": "http://webcat:8765/mcp",
                    "transport": "sse", 
                    "spec_version": "2024-11-05",
                    "description": "WebCat MCP Server",
                    "scope": "rag",
                    "env": {
                        "WEBCAT_API_KEY": "${WEBCAT_API_KEY}"
                    }
                },
                "filesystem": {
                    "url": "http://filesystem:8766/mcp",
                    "transport": "sse",
                    "spec_version": "2024-11-05", 
                    "description": "Filesystem MCP Server",
                    "scope": "all",
                    "env": {}
                }
            }
        }
        
        # Write test config to file
        with open(self.config_file, 'w') as f:
            json.dump(self.test_config, f)
            
        # Set up test client with config
        os.environ["MCP_CONFIG_PATH"] = str(self.config_file)
        
        # Initialize the global registry manually for testing
        from mcp_registry.app import registry as global_registry
        import mcp_registry.app as app_module
        app_module.registry = MCPRegistry(str(self.config_file))
        
        self.client = TestClient(app)
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
        if "MCP_CONFIG_PATH" in os.environ:
            del os.environ["MCP_CONFIG_PATH"]
        
        # Reset the global registry
        import mcp_registry.app as app_module
        app_module.registry = None
    
    def test_health_endpoint(self):
        """Test /health endpoint"""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["config_exists"])
    
    def test_get_all_servers_endpoint(self):
        """Test /servers endpoint"""
        response = self.client.get("/servers")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertIn("webcat", data)
        self.assertIn("filesystem", data)
        
        # Check server structure
        webcat = data["webcat"]
        self.assertEqual(webcat["url"], "http://webcat:8765/mcp")
        self.assertEqual(webcat["scope"], "rag")
    
    def test_get_rag_servers_endpoint(self):
        """Test /servers/rag endpoint"""
        response = self.client.get("/servers/rag")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)  # webcat (rag) + filesystem (all)
        self.assertIn("webcat", data)
        self.assertIn("filesystem", data)
    
    def test_get_servers_by_scope_endpoint(self):
        """Test /servers/scope/{scope} endpoint"""
        # Test RAG scope
        response = self.client.get("/servers/scope/rag")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertIn("webcat", data)
        
        # Test ALL scope
        response = self.client.get("/servers/scope/all")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertIn("filesystem", data)
    
    def test_get_server_by_name_endpoint(self):
        """Test /servers/{name} endpoint"""
        # Test existing server
        response = self.client.get("/servers/webcat")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["url"], "http://webcat:8765/mcp")
        
        # Test non-existing server
        response = self.client.get("/servers/nonexistent")
        self.assertEqual(response.status_code, 404)
    
    def test_get_config_endpoint(self):
        """Test /config endpoint"""
        response = self.client.get("/config")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("servers", data)
        self.assertIn("config_path", data)
        self.assertIn("last_modified", data)
        self.assertEqual(len(data["servers"]), 2)


class TestMCPServerConfig(unittest.TestCase):
    """Test cases for MCPServerConfig model"""
    
    def test_server_config_creation(self):
        """Test creating MCPServerConfig with valid data"""
        config_data = {
            "url": "http://test:8765/mcp",
            "transport": "sse",
            "spec_version": "2024-11-05",
            "description": "Test server",
            "scope": "rag",
            "env": {"API_KEY": "test"}
        }
        
        config = MCPServerConfig(**config_data)
        
        self.assertEqual(config.url, "http://test:8765/mcp")
        self.assertEqual(config.transport, "sse")
        self.assertEqual(config.scope, "rag")
        self.assertEqual(config.env, {"API_KEY": "test"})
    
    def test_server_config_defaults(self):
        """Test MCPServerConfig with default values"""
        config_data = {
            "url": "http://test:8765/mcp"
        }
        
        config = MCPServerConfig(**config_data)
        
        self.assertEqual(config.transport, "sse")
        self.assertEqual(config.spec_version, "2024-11-05")
        self.assertEqual(config.scope, "all")
        self.assertEqual(config.env, {})
    
    def test_server_config_validation(self):
        """Test MCPServerConfig validation"""
        # Test missing required field
        try:
            MCPServerConfig()
            self.fail("Expected validation error for missing required field")
        except Exception:
            pass  # Expected
        
        # Test that valid transports work
        config = MCPServerConfig(url="http://test:8765/mcp", transport="sse")
        self.assertEqual(config.transport, "sse")
        
        config = MCPServerConfig(url="http://test:8765/mcp", transport="stdio") 
        self.assertEqual(config.transport, "stdio")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2) 