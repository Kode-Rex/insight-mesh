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

6. **MCP Registry**
   - Runs unit tests for the MCP registry service
   - Tests REST API endpoints, configuration loading, and scope filtering
   - Generates coverage reports
   - Uploads coverage to Codecov with the `mcpregistry` flag

7. **Infrastructure Tests**
   - Runs tests that verify infrastructure dependencies are working correctly
   - Includes Neo4j connectivity test
   - This job is optional and will not fail the workflow if it fails

8. **Test Summary & Coverage Analysis**
   - **Depends on**: All test jobs must complete successfully
   - **Downloads**: Coverage artifacts from all test jobs
   - **Analyzes**: XML coverage reports from each component
   - **Displays**: Comprehensive test and coverage summary including:
     - Total test count and pass/fail status per component
     - Coverage percentage and line counts for each component  
     - Overall coverage statistics
     - Color-coded coverage assessment (🟢 Excellent ≥80%, 🟡 Good ≥60%, 🟠 Moderate ≥40%, 🔴 Low <40%)
   - **Reports**: Final deployment readiness status

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
   python -m pytest tests/ -v --cov=bin/modules --cov-report=term-missing
   ```

6. For the MCP Registry:
   ```bash
   cd mcp_registry
   PYTHONPATH=.. python -m pytest test_app.py -v --cov=mcp_registry.app --cov-report=term-missing
   ```

7. For Infrastructure Tests:
   ```bash
   # Neo4j test (requires Neo4j running locally)
   cd dagster_project
   python test_neo4j.py
   ```

#### Coverage Reports

Each test job generates coverage reports that are:
1. **Uploaded to Codecov** with component-specific flags for tracking trends
2. **Stored as artifacts** for the test summary job to analyze
3. **Analyzed collectively** to provide overall project health metrics

#### Test Summary Output

The test summary job provides a comprehensive report like this:

```
🧪 TEST & COVERAGE SUMMARY
==================================================

📊 TEST RESULTS
------------------------------
✅ Slack Bot          92 tests
✅ MCP Server         37 tests
✅ RAG Pipeline       10 tests
✅ Dagster Project    19 tests
✅ Annotations         8 tests
✅ MCP Client          1 tests
✅ Weave CLI          11 tests
✅ MCP Registry       20 tests
------------------------------
✅ TOTAL TESTS PASSED: 198

📈 COVERAGE ANALYSIS
--------------------------------------------------
Component        Coverage   Lines        Status
--------------------------------------------------
Slack Bot          65.0%    123/189     🟡 Good
MCP Server         64.0%    147/230     🟡 Good
RAG Pipeline       64.0%    158/247     🟡 Good
Dagster Project    23.0%    374/1633    🔴 Low
Annotations        99.0%     78/79      🟢 Excellent
Weave CLI          N/A      N/A         ⚪ No data
MCP Registry       83.0%    111/134     🟢 Excellent
--------------------------------------------------
OVERALL            58.2%    991/1702

🎯 SUMMARY
--------------------
✅ All 198 tests passing
📦 8 components tested
📈 4/6 components with good coverage (≥60%)
🚀 Ready for deployment!
```

#### Local Development

## Adding New Workflows

When adding new workflows, please follow these guidelines:

1. Use descriptive names for workflow files
2. Include all necessary environment variables
3. Update this README.md with information about the new workflow
4. Use GitHub secrets for sensitive information 