#!/bin/bash
set -e

echo "Running Insight Mesh Slack Bot Tests"
echo "===================================="

# Install test dependencies if needed
if ! pip show pytest pytest-asyncio pytest-cov > /dev/null; then
  echo "Installing test dependencies..."
  pip install pytest pytest-asyncio pytest-cov
fi

# Set environment variables for testing
export SLACK_BOT_TOKEN="xoxb-test-token"
export SLACK_APP_TOKEN="xapp-test-token"
export SLACK_BOT_ID="B12345678"
export LLM_API_URL="http://localhost:8000"
export LLM_API_KEY="test-key"
export LLM_MODEL="gpt-4o-mini"

# Run pytest with appropriate configuration
python -m pytest tests/ -v --cov=. --cov-report=term

echo "===================================="
echo "Tests completed" 