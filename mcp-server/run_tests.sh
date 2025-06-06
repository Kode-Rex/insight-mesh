#!/bin/bash

# Exit on error
set -e

# Print commands being executed
set -x

# Check if we're in a virtual environment, if not try to activate it
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    else
        echo "No virtual environment found. Make sure dependencies are installed."
    fi
fi

# Run all tests with pytest
echo "Running all tests..."
python -m pytest -v

# Run specific tests if they exist
if [ -f "test_web_assets.py" ]; then
    echo "Running web assets tests..."
    python test_web_assets.py
fi

if [ -f "test_rag_handler.py" ]; then
    echo "Running RAG handler tests..."
    python test_rag_handler.py
fi

if [ -f "test_fast_mcp.py" ]; then
    echo "Running FastMCP tests..."
    python test_fast_mcp.py
fi

echo "All tests completed!" 