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

#### Environment Setup

The workflow uses test environment variables to simulate the production environment without using real credentials.

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

## Adding New Workflows

When adding new workflows, please follow these guidelines:

1. Use descriptive names for workflow files
2. Include all necessary environment variables
3. Update this README.md with information about the new workflow
4. Use GitHub secrets for sensitive information 