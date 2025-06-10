#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Insight Mesh Test Runner ===${NC}"
echo -e "${BLUE}Running tests using the same configuration as GitHub Actions${NC}"
echo ""

# Function to run tests for a component
run_tests() {
  local component=$1
  local dir=$2
  local cmd=$3
  
  echo -e "${BLUE}Running $component tests...${NC}"
  echo -e "${BLUE}-----------------------------------${NC}"
  
  cd "$dir" || { echo -e "${RED}Directory $dir not found${NC}"; return 1; }
  
  # Create Python 3.11 virtual environment if it doesn't exist
  if [ ! -d "venv" ]; then
    echo "Creating Python 3.11 virtual environment..."
    python3.11 -m venv venv
  else
    echo "Using existing virtual environment..."
  fi
  
  # Activate virtual environment
  source venv/bin/activate
  
  # Install dependencies
  echo "Installing dependencies..."
  pip install -r requirements.txt
  
  # Ensure pytest is installed
  pip install pytest pytest-asyncio pytest-cov
  
  # Run the tests
  echo "Running tests..."
  eval "$cmd"
  
  local status=$?
  
  # Deactivate virtual environment
  deactivate
  
  # Return to original directory
  cd - > /dev/null
  
  if [ $status -eq 0 ]; then
    echo -e "${GREEN}$component tests: PASSED${NC}"
  else
    echo -e "${RED}$component tests: FAILED${NC}"
    exit 1
  fi
  
  echo ""
  
  return $status
}

# MCP Server Tests
run_tests "MCP Server" "mcp-server" "python -m pytest test_mcp_mocked.py test_fastmcp.py tests/ -v"

# RAG Pipeline Tests
run_tests "RAG Pipeline" "rag_pipeline" "python -m pytest test_rag_handler.py -v"

# Dagster Tests
run_tests "Dagster" "dagster_project" "python -m pytest test_assets.py test_web_assets.py -v"

# Slack Bot Tests
SLACK_BOT_TOKEN="xoxb-test-token" \
SLACK_APP_TOKEN="xapp-test-token" \
SLACK_BOT_ID="B12345678" \
LLM_API_URL="http://localhost:8000" \
LLM_API_KEY="test-key" \
LLM_MODEL="gpt-4o-mini" \
run_tests "Slack Bot" "slack-bot" "python -m pytest tests/ -v --cov=. --cov-report=term"

echo -e "${GREEN}=== All tests passed! ===${NC}" 