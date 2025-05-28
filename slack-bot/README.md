# Insight Mesh Slack AI Bot

A Slack bot for Insight Mesh that leverages Slack's API to provide intelligent assistance via LLM integration.

## Features

- **Thread Management**: Automatically manages conversation threads and context
- **Typing Indicators**: Shows typing states while generating responses
- **Online Presence**: Shows as "online" with a green status indicator
- **RAG Integration**: Connects to your LLM API for Retrieval-Augmented Generation
- **Agent Processes**: Allows users to start and monitor data processing jobs directly from Slack
- **Simplified Interface**: Clean interface showing only Messages and About tabs

## Quick Start

1. Follow the setup instructions in [SETUP.md](SETUP.md) to configure your Slack app
2. Create a `.env` file with the following variables in your project root:
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   LLM_API_URL=http://your-llm-api-url
   LLM_API_KEY=your-llm-api-key
   LLM_MODEL=gpt-4
   ```
3. Run the bot:
   ```bash
   cd slack-bot
   ./run_local.sh
   ```
   
## Docker Deployment

Build and run the Docker container:

```bash
docker build -t insight-mesh-slack-bot .
docker run -d --env-file .env --name insight-mesh-bot insight-mesh-slack-bot
```

## Architecture

The bot is built using:
- **slack-bolt**: Slack's official Python framework for building Slack apps
- **aiohttp**: Asynchronous HTTP client/server for Python
- **LiteLLM Proxy**: Compatible with OpenAI's API for connecting to different LLM providers

## Slack Integration Features

The bot implements several key Slack integration features:

### 1. Thread-Based Conversations
The bot automatically creates and maintains threads for all conversations, keeping discussions organized.

### 2. Typing Indicators
Shows when the bot is "thinking" while generating a response.

### 3. Universal Thread Response
The bot will respond to any message in a thread it's part of, without requiring explicit mentions.

### 4. Online Status
The bot maintains an online presence with a green status indicator.

## Agent Processes

The bot enables users to start and manage data processing jobs directly from Slack:

### Available Processes:

- **Data Indexing Job**: Index documents into the RAG system
- **Slack Import Job**: Import data from Slack channels
- **Check Job Status**: Check the status of running jobs

To start an agent process, users can type the command in chat:
```
Start a data indexing job
```

### Adding Custom Agent Processes

To add a new agent process:

1. Add it to the `AGENT_PROCESSES` dictionary in `app.py`:
   ```python
   "agent_your_process": {
       "name": "Your Process Name",
       "description": "What your process does",
       "command": "python path/to/script.py arg1 arg2"
   }
   ```
2. Add a corresponding prompt in `DEFAULT_PROMPTS`:
   ```python
   {"text": "Start your process", "action_id": "agent_your_process"}
   ```

## Development

- **app.py**: Main application with Slack bot implementation
- **requirements.txt**: Python dependencies
- **SETUP.md**: Configuration guide for Slack app settings

## Troubleshooting

If you're experiencing issues:

1. Ensure all Slack app permissions and event subscriptions are configured correctly
2. Check that your environment variables are set correctly
3. Verify your LLM API is accessible from the bot
4. Look for error messages in the bot logs

## Notes About Socket Mode

While this implementation uses Socket Mode for development convenience, we recommend:

1. Using Socket Mode during development for easy testing
2. Switching to HTTP endpoints for production deployments by:
   - Disabling Socket Mode in your Slack app settings
   - Setting up a public HTTP endpoint for your bot
   - Updating your app to use that endpoint instead of Socket Mode 