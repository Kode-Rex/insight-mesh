# GitHub Workflows for Insight Mesh

This directory contains the GitHub Actions workflows for the Insight Mesh project.

## Available Workflows

### Tests (`tests.yml`)

This workflow runs all tests for the Insight Mesh project on every push to the main branch and for all pull requests.

#### Components Tested

1. **Slack Bot**
   - Runs unit tests for the Slack bot component
   - Generates coverage reports
   - Uploads coverage to Codecov with the `slackbot` flag

2. **MCP Server**
   - Runs unit tests for the MCP server component
   - Generates coverage reports
   - Uploads coverage to Codecov with the `mcpserver` flag

3. **RAG Pipeline**
   - Runs unit tests for the RAG pipeline component
   - Generates coverage reports
   - Uploads coverage to Codecov with the `ragpipeline` flag

4. **Dagster Project**
   - Runs unit tests for the Dagster data pipeline component
   - Generates coverage reports
   - Uploads coverage to Codecov with the `dagster` flag

5. **Weave CLI**
   - Runs unit tests for the weave CLI MCP management functionality
   - Tests configuration management, synchronization, and integration features
   - Generates coverage reports
   - Uploads coverage to Codecov with the `weave` flag

6. **Infrastructure Tests**
   - Runs tests that verify infrastructure dependencies are working correctly
   - Includes Neo4j connectivity test
   - This job is optional and will not fail the workflow if it fails

#### Environment Setup

The workflow uses test environment variables to simulate the production environment without using real credentials.

For infrastructure tests, Docker containers are spun up as services to provide the necessary infrastructure components like Neo4j.

#### Running Tests Locally

To run the same tests locally:

1. For the Slack Bot:
   ```bash
   cd slack-bot
   python -m pytest tests/ -v --cov=. --cov-report=term-missing
   ```

2. For the MCP Server:
   ```bash
   cd mcp-server
   python -m pytest tests/ -v --cov=. --cov-report=term-missing
   ```

3. For the RAG Pipeline:
   ```bash
   cd rag_pipeline
   python -m pytest test_*.py -v --cov=. --cov-report=term-missing
   ```

4. For the Dagster Project:
   ```bash
   cd dagster_project
   python -m pytest test_assets.py test_web_assets.py -v --cov=. --cov-report=term-missing
   ```

5. For the Weave CLI:
   ```bash
   cd weave
   python run_tests.py --mcp-only
   # Or run all tests with coverage
   python -m pytest tests/ -v --cov=bin/modules --cov-report=term-missing
   ```

6. For Infrastructure Tests:
   ```bash
   # Neo4j test (requires Neo4j running locally)
   cd dagster_project
   python test_neo4j.py
   ```

## Adding New Workflows

When adding new workflows, please follow these guidelines:

1. Use descriptive names for workflow files
2. Include all necessary environment variables
3. Update this README.md with information about the new workflow
4. Use GitHub secrets for sensitive information 