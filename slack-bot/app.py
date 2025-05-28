import os
import logging
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack app
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))

# LLM configuration
LLM_API_URL = os.environ.get("LLM_API_URL", "http://localhost:8000/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4")

# Default suggested prompts - including agent actions
DEFAULT_PROMPTS = [
    {"text": "Tell me about Insight Mesh", "action_id": "prompt_about"},
    {"text": "How can I query my data?", "action_id": "prompt_query"},
    {"text": "Start a data indexing job", "action_id": "agent_index_data"},
    {"text": "Check job status", "action_id": "agent_check_status"},
    {"text": "Import data from Slack", "action_id": "agent_import_slack"},
    {"text": "Tell me about the actions I can take", "action_id": "prompt_actions"}
]

# Available agent processes
AGENT_PROCESSES = {
    "agent_index_data": {
        "name": "Data Indexing Job",
        "description": "Indexes your documents into the RAG system",
        "command": "python dagster_project/run_job.py index_files"
    },
    "agent_import_slack": {
        "name": "Slack Import Job",
        "description": "Imports data from Slack channels",
        "command": "python dagster_project/slack_assets.py run slack_channels_job"
    },
    "agent_check_status": {
        "name": "Job Status Check",
        "description": "Checks status of running jobs",
        "command": "python dagster_project/check_status.py"
    }
    # Add more agent processes as needed
}

async def get_llm_response(
    messages: List[Dict[str, str]],
    session: Optional[aiohttp.ClientSession] = None
) -> Optional[str]:
    """Get response from LLM via LiteLLM proxy"""
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY is not set")
        return None
        
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    logger.info(f"LLM API URL: {LLM_API_URL}")
    logger.info(f"LLM Model: {LLM_MODEL}")
    logger.info(f"Request payload: {payload}")
    
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True
        
    try:
        logger.info(f"Sending request to {LLM_API_URL}/chat/completions")
        async with session.post(
            f"{LLM_API_URL}/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            logger.info(f"Response status: {response.status}")
            if response.status == 200:
                result = await response.json()
                logger.info("Successfully received response from LLM API")
                return result["choices"][0]["message"]["content"]
            else:
                error_text = await response.text()
                logger.error(f"LLM API error: Status {response.status} - {error_text}")
                return None
    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None
    finally:
        if close_session:
            await session.close()

async def run_agent_process(process_id: str) -> Dict[str, Any]:
    """Run an agent process in the background and return status info"""
    if process_id not in AGENT_PROCESSES:
        return {"success": False, "message": f"Unknown agent process: {process_id}"}
    
    process = AGENT_PROCESSES[process_id]
    
    try:
        # Create a process to run the command
        process_obj = await asyncio.create_subprocess_shell(
            process["command"],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Return immediately with process info
        return {
            "success": True,
            "process_id": process_id,
            "name": process["name"],
            "status": "started",
            "pid": process_obj.pid
        }
    except Exception as e:
        logger.error(f"Error running agent process {process_id}: {e}")
        return {
            "success": False,
            "process_id": process_id,
            "name": process["name"],
            "error": str(e)
        }

async def update_home_tab(client: WebClient, user_id: str):
    """Update the Home tab for a user with available actions"""
    try:
        # Create blocks for the Home tab
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Insight Mesh Assistant",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Welcome to Insight Mesh! I can help you interact with your data or run data processing tasks."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Available Agent Actions",
                    "emoji": True
                }
            }
        ]
        
        # Add agent process actions
        for process_id, process in AGENT_PROCESSES.items():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{process['name']}*\n{process['description']}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": f"Start {process['name']}",
                        "emoji": True
                    },
                    "value": process_id,
                    "action_id": f"start_{process_id}"
                }
            })
        
        # Publish view
        await client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except SlackApiError as e:
        logger.error(f"Error publishing home tab: {e}")

async def set_assistant_status(client: WebClient, channel: str, thread_ts: str, status: str = "Thinking..."):
    """Set the assistant status indicator"""
    try:
        # Using the proper typing indicator API
        if status:
            # Start typing
            await client.chat_postEphemeral(
                channel=channel,
                user=client.token.split('-')[1].split(':')[0],
                text=f"_{status}_",
                thread_ts=thread_ts
            )
        # If empty status, we don't need to do anything as typing indicators
        # automatically disappear after a few seconds
    except SlackApiError as e:
        logger.error(f"Error setting typing status: {e}")

async def set_suggested_prompts(client: WebClient, channel: str, thread_ts: str, prompts: List[Dict[str, str]] = None):
    """Set suggested prompts for the assistant thread"""
    if prompts is None:
        prompts = DEFAULT_PROMPTS
    
    try:
        # Note: This is a simplified approach since the actual
        # chat_assistants_prompt method might not be available
        # We'll add the prompts as a message instead
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Suggested actions:*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": prompt["text"],
                            "emoji": True
                        },
                        "value": prompt["action_id"],
                        "action_id": prompt["action_id"]  # Use the action_id directly
                    }
                    for prompt in prompts[:5]  # Limit to 5 buttons
                ]
            }
        ]
        
        await client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text="Here are some suggested actions:",
            thread_ts=thread_ts
        )
    except SlackApiError as e:
        logger.error(f"Error setting suggested prompts: {e}")

async def handle_agent_action(action_id: str, user_id: str, client: WebClient, channel: str, thread_ts: str):
    """Handle agent process actions"""
    logger.info(f"Handling agent action: {action_id}")
    
    if action_id not in AGENT_PROCESSES:
        await client.chat_postMessage(
            channel=channel,
            text=f"Sorry, I couldn't find the requested agent process: {action_id}",
            thread_ts=thread_ts
        )
        return
    
    # Set a status to indicate we're starting the process
    await set_assistant_status(client, channel, thread_ts, f"Starting {AGENT_PROCESSES[action_id]['name']}...")
    
    # Run the agent process
    result = await run_agent_process(action_id)
    
    if result["success"]:
        # Create a rich message with process info
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚀 *Agent Process Started*: {result['name']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:* {result['status']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Process ID:* {result['pid']}"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Process started by <@{user_id}>"
                    }
                ]
            }
        ]
        
        await client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"Agent process {result['name']} started successfully.",
            thread_ts=thread_ts
        )
    else:
        await client.chat_postMessage(
            channel=channel,
            text=f"❌ Failed to start agent process: {result.get('error', 'Unknown error')}",
            thread_ts=thread_ts
        )
    
    # Clear the status
    await set_assistant_status(client, channel, thread_ts, "")

async def handle_message(
    text: str,
    user_id: str,
    client: WebClient,
    channel: str,
    thread_ts: Optional[str] = None
):
    logger.info(f"Handling message: '{text}' from user {user_id} in channel {channel}, thread {thread_ts}")
    
    # Log all available environment variables that might affect this
    logger.info(f"Bot ID: {os.environ.get('SLACK_BOT_ID', 'Not set')}")
    logger.info(f"App ID: {os.environ.get('SLACK_APP_ID', 'Not set')}")
    
    # Check if this is an agent action trigger
    for prompt in DEFAULT_PROMPTS:
        if prompt["action_id"].startswith("agent_") and text.lower() == prompt["text"].lower():
            logger.info(f"Detected agent action trigger: {prompt['action_id']}")
            await handle_agent_action(prompt["action_id"], user_id, client, channel, thread_ts)
            return
    
    try:
        # Log thread info more explicitly
        if thread_ts:
            logger.info(f"Responding in existing thread: {thread_ts}")
        else:
            logger.info("Starting a new thread")
            
        # Set thinking status if in a thread
        try:
            if thread_ts:
                await set_assistant_status(client, channel, thread_ts, "Thinking...")
                logger.info("Set typing indicator")
        except Exception as status_error:
            logger.error(f"Error setting status: {status_error}")
        
        # Use the LLM to generate a response
        try:
            async with aiohttp.ClientSession() as session:
                session.headers.update({"X-Auth-Token": f"slack:{user_id}"})
                messages = [
                    {"role": "system", "content": "You are a helpful assistant for Insight Mesh, a RAG (Retrieval-Augmented Generation) system. You help users understand and work with their data. You can also start agent processes on behalf of users when they request it."},
                    {"role": "user", "content": text}
                ]
                
                logger.info("Sending request to LLM API")
                llm_response = await get_llm_response(messages, session=session)
                logger.info(f"Got LLM response: {llm_response is not None}")
        except Exception as llm_error:
            logger.error(f"Error getting LLM response: {llm_error}")
            import traceback
            logger.error(f"LLM error traceback: {traceback.format_exc()}")
            llm_response = None
            
        # Send the response and clear status
        try:
            if llm_response:
                logger.info(f"Sending response to Slack: channel={channel}, thread_ts={thread_ts}")
                response = await client.chat_postMessage(
                    channel=channel,
                    text=llm_response,
                    thread_ts=thread_ts
                )
                logger.info(f"Response sent successfully: {response}")
                
                # Set suggested follow-up prompts
                if thread_ts:
                    logger.info("Setting suggested prompts")
                    await set_suggested_prompts(client, channel, thread_ts)
            else:
                logger.error("No LLM response received, sending error message")
                await client.chat_postMessage(
                    channel=channel,
                    text="I'm sorry, I encountered an error while generating a response.",
                    thread_ts=thread_ts
                )
        except Exception as posting_error:
            logger.error(f"Error posting message to Slack: {posting_error}")
            import traceback
            logger.error(f"Posting error traceback: {traceback.format_exc()}")
            
        # Clear the status if we were in a thread
        try:
            if thread_ts:
                await set_assistant_status(client, channel, thread_ts, "")
        except Exception as clear_status_error:
            logger.error(f"Error clearing status: {clear_status_error}")
                
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        import traceback
        logger.error(f"Handle message traceback: {traceback.format_exc()}")
        
        try:
            if thread_ts:
                await set_assistant_status(client, channel, thread_ts, "")
        except:
            pass
        
        try:
            await client.chat_postMessage(
                channel=channel,
                text="I'm sorry, something went wrong. Please try again later.",
                thread_ts=thread_ts
            )
        except Exception as final_error:
            logger.error(f"Error sending final error message: {final_error}")

# Action handlers for interactive components
@app.action(r"start_agent_.*")
async def handle_start_agent_action(ack, body, client):
    """Handle action when a user clicks a button to start an agent process"""
    await ack()
    try:
        user_id = body["user"]["id"]
        action_id = body["actions"][0]["value"]
        channel_id = body["channel"]["id"]
        
        # For actions from Home tab, start a new DM conversation
        if body["container"].get("type") == "home":
            # Open a DM with the user
            response = await client.conversations_open(users=[user_id])
            channel_id = response["channel"]["id"]
            thread_ts = None
        else:
            # For actions from messages, use the existing thread
            thread_ts = body.get("message", {}).get("thread_ts")
        
        await handle_agent_action(
            action_id=action_id,
            user_id=user_id,
            client=client,
            channel=channel_id,
            thread_ts=thread_ts
        )
    except Exception as e:
        logger.error(f"Error handling start agent action: {e}")

@app.event("app_home_opened")
async def handle_app_home_opened(client, event):
    """Handle when a user opens the app home tab"""
    user_id = event["user"]
    await update_home_tab(client, user_id)

@app.event("assistant_thread_started")
async def handle_assistant_thread_started(body, client):
    """Handle the event when a user starts an AI assistant thread"""
    logger.info("Assistant thread started")
    try:
        event = body["event"]
        channel_id = event["channel"]
        thread_ts = event.get("thread_ts")
        user_id = event.get("user")
        
        # Set suggested prompts
        await set_suggested_prompts(client, channel_id, thread_ts)
        
        # Optional: send a welcome message
        await client.chat_postMessage(
            channel=channel_id,
            text="👋 Hello! I'm Insight Mesh Assistant. I can help answer questions about your data or start agent processes for you. Try one of the suggested actions above!",
            thread_ts=thread_ts
        )
    except Exception as e:
        logger.error(f"Error handling assistant thread started: {e}")

@app.event("app_mention")
async def handle_mention(body, client):
    """Handle when the bot is mentioned in a channel"""
    logger.info(f"Received app mention: {body}")
    try:
        event = body["event"]
        user_id = event["user"]
        text = event["text"]
        text = text.split("<@", 1)[-1].split(">", 1)[-1].strip() if ">" in text else text
        channel = event["channel"]
        
        # Always use the original message timestamp as thread_ts if not already in a thread
        thread_ts = event.get("thread_ts", event.get("ts"))
        
        logger.info(f"Handling mention in channel {channel}, thread {thread_ts}, text: '{text}'")
        
        await handle_message(
            text=text,
            user_id=user_id,
            client=client,
            channel=channel,
            thread_ts=thread_ts
        )
    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        import traceback
        logger.error(f"Mention handler traceback: {traceback.format_exc()}")
        await client.chat_postMessage(
            channel=body["event"]["channel"],
            text="I'm sorry, I encountered an error while processing your request.",
            thread_ts=body["event"].get("thread_ts", body["event"].get("ts"))
        )

# Handle all message events
@app.event({"type": "message", "subtype": None})
@app.event("message")
async def handle_message_event(body, client):
    """Handle all message events including those in threads"""
    logger.info(f"Received message event: {body}")
    try:
        event = body["event"]
        
        # Skip if it's from a bot
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            logger.info("Skipping bot message")
            return
        
        user_id = event.get("user")
        if not user_id:
            logger.info("Skipping message with no user")
            return
            
        channel = event.get("channel")
        channel_type = event.get("channel_type", "")
        text = event.get("text", "").strip()
        thread_ts = event.get("thread_ts")
        ts = event.get("ts")
        
        logger.info(f"Processing message: channel_type={channel_type}, thread_ts={thread_ts}, text='{text}'")
        
        # ALWAYS process if:
        # 1. It's a DM (im)
        # 2. It's a thread message (respond to all thread messages for simplicity)
        
        # Check if message is in a DM
        if channel_type == "im":
            logger.info("Processing DM message")
            await handle_message(
                text=text,
                user_id=user_id,
                client=client,
                channel=channel,
                thread_ts=thread_ts or ts  # Use thread_ts if in thread, otherwise ts
            )
            return
            
        # Check if message mentions the bot (in any context)
        bot_id = os.environ.get("SLACK_BOT_ID", "")
        is_mention = f"<@{bot_id}>" in text if bot_id else False
        
        if is_mention:
            logger.info("Processing message with bot mention")
            # Extract text after mention
            clean_text = text.split(">", 1)[-1].strip() if ">" in text else text
            await handle_message(
                text=clean_text,
                user_id=user_id,
                client=client,
                channel=channel,
                thread_ts=thread_ts or ts
            )
            return
            
        # If in thread, respond to all messages in the thread
        if thread_ts:
            logger.info("Message is in a thread, processing")
            await handle_message(
                text=text,
                user_id=user_id,
                client=client,
                channel=channel,
                thread_ts=thread_ts
            )
            return
                
        logger.info("Message doesn't meet criteria for bot response, ignoring")
            
    except Exception as e:
        logger.error(f"Error in message event handler: {e}")
        import traceback
        logger.error(f"Message handler traceback: {traceback.format_exc()}")

# Handle any button clicks from our suggested prompts
@app.action("prompt_about")
@app.action("prompt_query")
@app.action("prompt_actions")
@app.action("agent_index_data")
@app.action("agent_check_status")
@app.action("agent_import_slack")
async def handle_suggested_prompt(ack, body, client):
    """Handle when a user clicks a suggested prompt button"""
    await ack()
    try:
        user_id = body["user"]["id"]
        action_id = body["actions"][0]["action_id"]  # Get the action_id directly
        channel_id = body["channel"]["id"]
        thread_ts = body.get("message", {}).get("thread_ts") or body.get("container", {}).get("thread_ts")
        
        logger.info(f"Handling suggested prompt action: {action_id}")
        
        # Get the text for this action
        prompt_text = next((p["text"] for p in DEFAULT_PROMPTS if p["action_id"] == action_id), None)
        
        if prompt_text:
            if action_id.startswith("agent_"):
                await handle_agent_action(
                    action_id=action_id,
                    user_id=user_id,
                    client=client,
                    channel=channel_id,
                    thread_ts=thread_ts
                )
            else:
                # For regular prompts, process as a message
                await handle_message(
                    text=prompt_text,
                    user_id=user_id,
                    client=client,
                    channel=channel_id,
                    thread_ts=thread_ts
                )
    except Exception as e:
        logger.error(f"Error handling suggested prompt: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def main():
    """Start the Slack bot asynchronously"""
    async def run():
        handler = AsyncSocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
        logger.info("Starting Insight Mesh Assistant with AI Apps support...")
        await handler.start_async()
    asyncio.run(run())

if __name__ == "__main__":
    main() 