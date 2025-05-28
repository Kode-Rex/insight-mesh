#!/bin/bash
set -e

echo "Running Insight Mesh Slack Bot Tests"
echo "===================================="

# Install test dependencies if needed
if ! pip show pytest pytest-asyncio > /dev/null; then
  echo "Installing test dependencies..."
  pip install pytest pytest-asyncio
fi

# Run pytest with appropriate configuration
python -m pytest tests/ -v

echo "===================================="
echo "Tests completed" 