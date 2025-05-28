# Insight Mesh Slack AI Bot

A Slack bot for Insight Mesh that leverages Slack's latest AI Apps features to provide a better user experience.

## Features

- **Slack AI Apps Integration**: Uses Slack's newest AI Apps interface for improved discoverability and user experience
- **Thread Management**: Automatically manages conversation threads and context
- **Typing Indicators**: Shows typing states while generating responses
- **Suggested Prompts**: Provides helpful prompt suggestions to guide users
- **RAG Integration**: Connects to your LLM API for Retrieval-Augmented Generation
- **Agent Processes**: Allows users to start and monitor data processing jobs directly from Slack
- **Home Tab**: Custom App Home experience with quick action buttons
- **Interactive Components**: Button actions for starting agent processes

## Quick Start

1. Follow the setup instructions in [SETUP.md](SETUP.md) to configure your Slack app
2. Create a `.env` file with the following variables:
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   LLM_API_URL=http://your-llm-api-url
   LLM_API_KEY=your-llm-api-key
   LLM_MODEL=gpt-4
   ```
3. Run the bot:
   ```bash
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

## AI Apps Features

The bot uses several features from Slack's AI Apps framework:

### 1. Assistant Typing Indicators
Shows when the bot is "thinking" while generating a response.

### 2. Suggested Prompts
Provides helpful suggestions for users to try next, including:
- General information prompts
- Agent action prompts that trigger automated processes

### 3. App Home Tab
Custom Home tab with:
- Information about the bot
- Quick action buttons for starting agent processes

### 4. Interactive Components
Button actions that allow users to trigger agent processes directly.

## Agent Processes

The bot enables users to start and manage data processing jobs directly from Slack:

### Available Processes:

- **Data Indexing Job**: Index documents into the RAG system
- **Slack Import Job**: Import data from Slack channels
- **Check Job Status**: Check the status of running jobs

To start an agent process, users can:
1. Select one of the suggested prompts (e.g., "Start a data indexing job")
2. Type the exact command in the chat (e.g., "Start a data indexing job")
3. Click a button in the App Home tab

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

- **app_ai.py**: Main application with AI Apps support
- **app.py**: Legacy application (kept for reference)
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