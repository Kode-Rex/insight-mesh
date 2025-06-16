#!/usr/bin/env python

"""
Test runner for Weave MCP management functionality.

This script runs all tests for the weave CLI tool, with special focus
on the new MCP server management features.
"""

import os
import sys
import unittest
from pathlib import Path

# Add the weave modules to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin'))

def run_tests():
    """Run all weave tests"""
    # Set test mode
    os.environ['WEAVE_TEST_MODE'] = 'true'
    
    # Discover and run tests
    test_dir = Path(__file__).parent / 'tests'
    loader = unittest.TestLoader()
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

def run_mcp_tests_only():
    """Run only MCP-related tests"""
    os.environ['WEAVE_TEST_MODE'] = 'true'
    
    # Import and run MCP tests specifically
    from tests.test_mcp_management import TestMCPConfig, TestMCPIntegration
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add MCP test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMCPConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Weave tests')
    parser.add_argument('--mcp-only', action='store_true', 
                       help='Run only MCP management tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    if args.mcp_only:
        print("🧪 Running MCP management tests only...")
        exit_code = run_mcp_tests_only()
    else:
        print("🧪 Running all Weave tests...")
        exit_code = run_tests()
    
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(exit_code) 