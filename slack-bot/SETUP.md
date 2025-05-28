# Slack AI App Setup Guide

This guide will help you configure your Slack app to use the latest AI Apps features.

## Step 1: Create or Update App Configuration in Slack

1. Go to [Slack API Apps page](https://api.slack.com/apps) and select your bot application (or create a new one)
2. Navigate to "AI & Assistants" in the left navigation panel (formerly "Agents & AI Apps")
3. Toggle on "Enable AI Features"
4. Add an overview description (e.g., "Insight Mesh Assistant helps you interact with your data using RAG and run agent processes")
5. Configure prompt suggestions:
   - Select "Fixed prompts" and add the same prompts defined in our code, or
   - Select "Dynamic prompts" if you prefer the app to generate them based on context
6. Click "Save Changes"

## Step 2: Configure OAuth Scopes

1. Navigate to "OAuth & Permissions" in the left navigation panel
2. Under "Scopes" > "Bot Token Scopes", add the following:
   - `app_mentions:read` - Read mentions of your app
   - `chat:write` - Send messages
   - `im:history` - View messages in direct messages
   - `im:read` - View basic information about direct messages
   - `im:write` - Send messages in direct messages
   - `chat:write.customize` - Customize messages (for blocks)
   - `chat:write.public` - Send messages to channels the app isn't in
   - `app_mentions:read` - Read @mentions
   - `commands` - Add slash commands
   - `users:read` - View users in the workspace
   - `users:read.email` - View email addresses of users
   - `channels:read` - View basic info about public channels
   - `channels:history` - View messages in public channels
   - `groups:read` - View basic info about private channels
   - `groups:history` - View messages in private channels
   - `reactions:write` - Add reactions to messages
   - `files:write` - Upload, edit, and delete files
   - `chat.ai_prompts:write` - Use AI prompt suggestions
   - `chat.ai_response_status:write` - Show typing indicators
   - `chat.typing:write` - Use typing indicators
3. Click "Save Changes"

## Step 3: Enable Socket Mode (for development)

1. Navigate to "Socket Mode" in the left navigation panel
2. Toggle on "Enable Socket Mode"
3. Create an app-level token if prompted:
   - Name your token (e.g., "Insight Mesh Socket Token")
   - Ensure the `connections:write` scope is added
   - Click "Generate"
   - Save the token (starts with `xapp-`) for use in environment variables

## Step 4: Configure Event Subscriptions

1. Navigate to "Event Subscriptions" in the left navigation panel
2. Toggle on "Enable Events"
3. Under "Subscribe to bot events" add the following:
   - `app_home_opened` - When a user opens the App Home tab
   - `app_mention` - When the app is mentioned in a channel
   - `message.im` - When a message is sent in a DM with the app
   - `message` - When a message is sent (for backward compatibility)
4. Click "Save Changes"

## Step 5: Configure App Home

1. Navigate to "App Home" in the left navigation panel
2. Toggle on "Home Tab" if not already enabled
3. Toggle on "Allow users to send Slash commands and messages from the messages tab"
4. Click "Save Changes"

## Step 6: Configure Interactivity

1. Navigate to "Interactivity & Shortcuts" in the left navigation panel
2. Toggle on "Interactivity"
3. You can leave the Request URL blank for Socket Mode
4. Under "Shortcuts", you can add shortcuts if needed
5. Click "Save Changes"

## Step 7: Reinstall App

1. Navigate to "Install App" in the left navigation panel
2. Click "Reinstall to Workspace" (required after adding new scopes)
3. Review permissions and click "Allow"
4. Note the new Bot User OAuth Token (starts with `xoxb-`) for use in environment variables

## Step 8: Set Environment Variables

Create a `.env` file with the following variables:

```bash
SLACK_BOT_TOKEN="xoxb-your-bot-token"
SLACK_APP_TOKEN="xapp-your-app-token"
LLM_API_URL="http://your-llm-api-url"
LLM_API_KEY="your-llm-api-key"
LLM_MODEL="gpt-4" # or other model supported by your LLM API
```

## Step 9: Configure Agent Processes

The bot supports running agent processes in response to user requests. These processes are defined in the `AGENT_PROCESSES` dictionary in `app.py`.

By default, the following agent processes are available:

1. **Data Indexing Job** - Indexes documents into the RAG system
2. **Slack Import Job** - Imports data from Slack channels
3. **Job Status Check** - Checks status of running jobs

To add or modify agent processes:

1. Edit the `AGENT_PROCESSES` dictionary in `app.py`
2. Make sure commands have the correct paths to their scripts
3. Add corresponding entries to `DEFAULT_PROMPTS` to make them available as prompts
4. Ensure the scripts are available and executable in the expected locations

## Step 10: Run the Bot

Start the bot using:

```bash
python app.py
```

Or using the provided script:

```bash
./run_local.sh
```

Or using Docker:

```bash
docker build -t insight-mesh-slack-bot .
docker run -d --env-file .env --name insight-mesh-bot insight-mesh-slack-bot
```

## Verifying Setup

1. In Slack, you should see your AI App in the sidebar (may need to search in Apps)
2. Click on the app to open the AI split view
3. Try one of the suggested prompts or ask a question
4. You should see the typing indicator while it's thinking and then receive a response
5. Try starting an agent process by using one of the agent prompts (e.g., "Start a data indexing job")
6. The bot should respond with a confirmation that the process has started and provide status details
7. Open the App Home tab to see the agent action buttons 