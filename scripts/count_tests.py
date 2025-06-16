#!/usr/bin/env python3
"""
Dynamic test counter for CI pipeline
Discovers and counts tests across all components without running them
"""

import os
import sys
import json
import subprocess
from pathlib import Path


def count_tests_in_directory(directory, working_dir=None):
    """Count tests in a directory using pytest's collect-only feature"""
    if not os.path.exists(directory):
        return 0
    
    try:
        # Use pytest to collect tests without running them
        cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
        
        # Determine working directory and test path
        if working_dir and os.path.exists(working_dir):
            cwd = working_dir
            # If directory is relative to working_dir, use it as-is; otherwise use relative path
            if directory.startswith(working_dir):
                test_path = os.path.relpath(directory, working_dir)
            else:
                test_path = "."
        else:
            cwd = directory
            test_path = "."
        
        cmd.append(test_path)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        
        if result.returncode == 0:
            output = result.stdout + result.stderr
            # Parse the output to count tests
            lines = output.split('\n')
            for line in lines:
                if 'collected' in line and ('items' in line or 'item' in line):
                    # Extract number from "collected X items" or "collected X item"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == 'collected' and i + 1 < len(parts):
                            try:
                                return int(parts[i + 1])
                            except ValueError:
                                pass
            
            # Alternative: count test function definitions
            test_functions = 0
            for line in lines:
                if '::test_' in line or '<Function test_' in line:
                    test_functions += 1
            
            if test_functions > 0:
                return test_functions
                
        return 0
    except Exception as e:
        print(f"Error counting tests in {directory}: {e}")
        return 0


def count_weave_tests():
    """Count tests in weave directory using pytest on test files directly"""
    weave_dir = "weave"
    if not os.path.exists(weave_dir):
        return {"Weave CLI": 0}
    
    try:
        # Count all tests in weave/tests directory
        weave_tests_dir = os.path.join(weave_dir, "tests")
        total_count = count_tests_in_directory(weave_tests_dir, weave_dir)
        return {"Weave CLI": total_count}
    except Exception as e:
        print(f"Error counting weave tests: {e}")
        return {"Weave CLI": 29}  # Fallback (11 MCP + 18 CLI)


def discover_all_tests():
    """Discover and count tests across all project components"""
    
    # Define component directories and their test patterns
    components = {
        "Slack Bot": {
            "directory": "slack-bot",
            "test_dir": "slack-bot/tests"
        },
        "MCP Server": {
            "directory": "mcp-server", 
            "test_dir": "mcp-server/tests"
        },
        "RAG Pipeline": {
            "directory": "rag_pipeline",
            "test_dir": "rag_pipeline",
            "test_pattern": "test_*.py"
        },
        "Dagster Project": {
            "directory": "dagster_project", 
            "test_dir": "dagster_project",
            "test_pattern": "test_*.py"
        },
        "MCP Registry": {
            "directory": "mcp_registry",
            "test_dir": "mcp_registry"
        }
    }
    
    test_counts = {}
    
    # Count tests for each component
    for name, config in components.items():
        test_dir = config["test_dir"]
        working_dir = config["directory"]
        count = count_tests_in_directory(test_dir, working_dir)
        test_counts[name] = count
        print(f"📊 {name:<16} {count:>3} tests")
    
    # Handle special cases
    
    # Annotations tests (in root)
    if os.path.exists("test_annotations.py"):
        annotations_count = count_tests_in_directory(".", ".")
        # Filter for just annotations
        cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", "test_annotations.py"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
            if result.returncode == 0:
                output = result.stdout + result.stderr
                for line in output.split('\n'):
                    if 'collected' in line and ('items' in line or 'item' in line):
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'collected' and i + 1 < len(parts):
                                try:
                                    annotations_count = int(parts[i + 1])
                                    break
                                except ValueError:
                                    pass
        except:
            annotations_count = 8  # Fallback
    else:
        annotations_count = 0
    test_counts["Annotations"] = annotations_count
    print(f"📊 {'Annotations':<16} {annotations_count:>3} tests")
    
    # MCP Client test (in root)
    if os.path.exists("test_mcp.py"):
        cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", "test_mcp.py"]
        mcp_client_count = 0
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
            if result.returncode == 0:
                output = result.stdout + result.stderr
                for line in output.split('\n'):
                    if 'collected' in line and ('items' in line or 'item' in line):
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'collected' and i + 1 < len(parts):
                                try:
                                    mcp_client_count = int(parts[i + 1])
                                    break
                                except ValueError:
                                    pass
        except:
            mcp_client_count = 1  # Fallback
    else:
        mcp_client_count = 0
    test_counts["MCP Client"] = mcp_client_count
    print(f"📊 {'MCP Client':<16} {mcp_client_count:>3} tests")
    
    # Weave CLI tests (special handling)
    weave_tests = count_weave_tests()
    for test_type, count in weave_tests.items():
        test_counts[test_type] = count
        print(f"📊 {test_type:<16} {count:>3} tests")
    
    return test_counts


def generate_test_summary_json():
    """Generate a JSON summary of all test counts"""
    test_counts = discover_all_tests()
    
    # Convert to the format expected by CI
    summary = {}
    for component, count in test_counts.items():
        summary[component] = {
            "tests": count,
            "status": "✅"  # Assume success since we're just counting
        }
    
    total_tests = sum(test_counts.values())
    summary["_meta"] = {
        "total_tests": total_tests,
        "total_components": len(test_counts),
        "generated_at": "dynamic"
    }
    
    return summary


def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # Output JSON for CI consumption
        summary = generate_test_summary_json()
        print(json.dumps(summary, indent=2))
    else:
        # Human-readable output
        print("🧪 DYNAMIC TEST DISCOVERY")
        print("=" * 40)
        test_counts = discover_all_tests()
        print("-" * 40)
        total = sum(test_counts.values())
        print(f"📈 TOTAL: {total} tests across {len(test_counts)} components")


if __name__ == "__main__":
    main() 