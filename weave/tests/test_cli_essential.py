#!/usr/bin/env python3

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from click.testing import CliRunner
import sys

# Add the weave modules to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

# Set up comprehensive mocking before importing CLI modules
def setup_test_mocks():
    """Set up all necessary mocks for CLI testing"""
    # Mock configuration functions that are called during module import
    with patch('modules.config.load_config') as mock_load_config, \
         patch('modules.config.get_managed_databases') as mock_get_dbs, \
         patch('modules.config.get_databases_config') as mock_get_db_config:
        
        # Setup mock return values
        mock_load_config.return_value = {
            "project_name": "test-project",
            "databases": {
                "slack": {"type": "sql", "migration_tool": "alembic"},
                "insightmesh": {"type": "graph", "migration_tool": "neo4j-migrations"}
            },
            "services": {}
        }
        mock_get_dbs.return_value = ['slack', 'insightmesh']
        mock_get_db_config.return_value = {
            "slack": {"type": "sql", "migration_tool": "alembic"},
            "insightmesh": {"type": "graph", "migration_tool": "neo4j-migrations"}
        }
        
        # Import CLI modules with mocked config
        from modules.cli import cli
        from modules.cli_tools import tool_group
        from modules.cli_services import service_group
        from modules.cli_db import db_group
        
        return cli, tool_group, service_group, db_group

# Import with mocks
cli, tool_group, service_group, db_group = setup_test_mocks()


class TestEssentialCLI(unittest.TestCase):
    """Test essential CLI functionality that should work reliably"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        os.environ['WEAVE_TEST_MODE'] = 'true'
        
    def tearDown(self):
        """Clean up test fixtures"""
        if 'WEAVE_TEST_MODE' in os.environ:
            del os.environ['WEAVE_TEST_MODE']


class TestMainCLICore(TestEssentialCLI):
    """Test core CLI functionality"""
    
    def test_cli_version(self):
        """Test --version flag"""
        result = self.runner.invoke(cli, ['--version'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Weave', result.output)
        self.assertIn('version', result.output)
    
    def test_cli_help(self):
        """Test help output"""
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Weaver: A Rails-like framework', result.output)
        self.assertIn('Commands:', result.output)
        self.assertIn('tool', result.output)
        self.assertIn('service', result.output)
        self.assertIn('db', result.output)
    
    def test_cli_test_mode_flag(self):
        """Test that test mode flag is recognized"""
        result = self.runner.invoke(cli, ['--test-mode', '--help'])
        self.assertEqual(result.exit_code, 0)
        # The output should contain both test mode indicator and help
        self.assertTrue('test mode' in result.output.lower() or 'TEST MODE' in result.output)


class TestToolCommandsCore(TestEssentialCLI):
    """Test core tool command functionality"""
    
    def test_tool_help(self):
        """Test tool command help"""
        result = self.runner.invoke(tool_group, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Manage MCP', result.output)
        self.assertIn('add', result.output)
        self.assertIn('remove', result.output)
        self.assertIn('list', result.output)
    
    @patch('modules.mcp_config.load_weave_config')
    @patch('modules.mcp_config.save_weave_config')
    def test_tool_add_basic(self, mock_save, mock_load):
        """Test basic tool add command"""
        mock_load.return_value = {"project_name": "test"}
        mock_save.return_value = True
        
        result = self.runner.invoke(tool_group, [
            'add', 'test-server', 'http://test:8080/mcp',
            '--description', 'Test server'
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Added MCP server', result.output)
        mock_save.assert_called_once()
    
    @patch('modules.mcp_config.load_weave_config')
    @patch('modules.mcp_config.save_weave_config')
    def test_tool_add_with_options(self, mock_save, mock_load):
        """Test tool add with various options"""
        mock_load.return_value = {"project_name": "test"}
        mock_save.return_value = True
        
        result = self.runner.invoke(tool_group, [
            'add', 'secure-server', 'https://api.example.com/mcp',
            '--env', 'API_KEY=secret123',
            '--env', 'TIMEOUT=30',
            '--auth-type', 'bearer_token',
            '--scope', 'rag',
            '--transport', 'sse'
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Added MCP server', result.output)
        
        # Verify the config was saved with correct parameters
        call_args = mock_save.call_args[0][0]
        self.assertIn('mcp_servers', call_args)
        server_config = call_args['mcp_servers']['secure-server']
        self.assertEqual(server_config['env']['API_KEY'], 'secret123')
        self.assertEqual(server_config['auth_type'], 'bearer_token')
        self.assertEqual(server_config['scope'], 'rag')
    
    @patch('modules.mcp_config.remove_mcp_server_from_config')
    def test_tool_remove_with_yes_flag(self, mock_remove):
        """Test tool remove with --yes flag (skip confirmation)"""
        mock_remove.return_value = True
        
        result = self.runner.invoke(tool_group, [
            'remove', 'test-server', '--yes'
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Removed MCP server', result.output)
        mock_remove.assert_called_once_with('test-server')
    
    def test_tool_add_invalid_env_format(self):
        """Test tool add with invalid environment variable format"""
        result = self.runner.invoke(tool_group, [
            'add', 'test-server', 'http://test:8080/mcp',
            '--env', 'INVALID_FORMAT'  # Missing = sign
        ])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Invalid environment variable format', result.output)


class TestServiceCommandsCore(TestEssentialCLI):
    """Test core service command functionality"""
    
    def test_service_help(self):
        """Test service command help"""
        result = self.runner.invoke(service_group, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Manage Docker services', result.output)
        self.assertIn('add', result.output)
        self.assertIn('status', result.output)


class TestDatabaseCommandsCore(TestEssentialCLI):
    """Test core database command functionality"""
    
    def test_db_help(self):
        """Test database command help"""
        result = self.runner.invoke(db_group, ['--help'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Database management commands', result.output)
        self.assertIn('migrate', result.output)
        self.assertIn('rollback', result.output)
        self.assertIn('create', result.output)
        self.assertIn('history', result.output)
    
    @patch('modules.cli_db.get_managed_databases')
    def test_db_rollback_dry_run(self, mock_get_dbs):
        """Test database rollback dry run"""
        mock_get_dbs.return_value = ['slack', 'insightmesh']
        
        result = self.runner.invoke(db_group, ['rollback', 'slack', '--dry-run'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('DRY RUN', result.output)
        self.assertIn('rollback', result.output.lower())


class TestCLICommandDiscovery(TestEssentialCLI):
    """Test that CLI commands are properly discoverable"""
    
    def test_main_commands_discovery(self):
        """Test that all main command groups are discoverable"""
        result = self.runner.invoke(cli, ['--help'])
        
        self.assertEqual(result.exit_code, 0)
        # Check that main command groups are listed
        self.assertIn('tool', result.output)
        self.assertIn('service', result.output)
        self.assertIn('db', result.output)
        self.assertIn('log', result.output)
    
    def test_tool_subcommands_discovery(self):
        """Test that tool subcommands are discoverable"""
        result = self.runner.invoke(cli, ['tool', '--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('add', result.output)
        self.assertIn('remove', result.output)
        self.assertIn('list', result.output)
    
    def test_service_subcommands_discovery(self):
        """Test that service subcommands are discoverable"""
        result = self.runner.invoke(cli, ['service', '--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('add', result.output)
        self.assertIn('status', result.output)
    
    def test_db_subcommands_discovery(self):
        """Test that database subcommands are discoverable"""
        result = self.runner.invoke(cli, ['db', '--help'])
        
        self.assertEqual(result.exit_code, 0)
        self.assertIn('migrate', result.output)
        self.assertIn('rollback', result.output)
        self.assertIn('create', result.output)


class TestCLIArgumentParsing(TestEssentialCLI):
    """Test CLI argument parsing logic"""
    
    def test_global_flags_parsing(self):
        """Test that global flags are parsed correctly"""
        # Test verbose flag
        result = self.runner.invoke(cli, ['--verbose', '--help'])
        self.assertEqual(result.exit_code, 0)
        
        # Test test-mode flag
        result = self.runner.invoke(cli, ['--test-mode', '--help'])
        self.assertEqual(result.exit_code, 0)
    
    def test_command_options_parsing(self):
        """Test that command-specific options are parsed correctly"""
        # Test tool add with multiple options
        with patch('modules.mcp_config.load_weave_config') as mock_load, \
             patch('modules.mcp_config.save_weave_config') as mock_save:
            
            mock_load.return_value = {"project_name": "test"}
            mock_save.return_value = True
            
            result = self.runner.invoke(tool_group, [
                'add', 'test-server', 'http://test:8080/mcp',
                '--transport', 'sse',
                '--auth-type', 'api_key',
                '--scope', 'agent',
                '--description', 'Test description with spaces'
            ])
            
            self.assertEqual(result.exit_code, 0)
    
    def test_required_arguments_validation(self):
        """Test that required arguments are validated"""
        # Test tool add without required arguments
        result = self.runner.invoke(tool_group, ['add'])
        self.assertNotEqual(result.exit_code, 0)  # Should fail due to missing args
        
        # Test with only one required argument
        result = self.runner.invoke(tool_group, ['add', 'server-name'])
        self.assertNotEqual(result.exit_code, 0)  # Should fail due to missing URL


if __name__ == '__main__':
    # Set up test environment
    os.environ['WEAVE_TEST_MODE'] = 'true'
    
    # Run tests
    unittest.main(verbosity=2) 