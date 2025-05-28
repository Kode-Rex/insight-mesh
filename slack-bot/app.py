import os
import logging
import aiohttp
import asyncio
import re
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
    session: Optional[aiohttp.ClientSession] = None,
    user_id: Optional[str] = None
) -> Optional[str]:
    """Get response from LLM via LiteLLM proxy"""
    if not LLM_API_KEY:
        logger.error("LLM_API_KEY is not set")
        return None
        
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Add user auth token if provided
    if user_id:
        auth_token = f"slack:{user_id}"
        headers["X-Auth-Token"] = auth_token
        logger.info(f"Added X-Auth-Token header: {auth_token}")
    
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    # Add metadata with user auth token for the callback pipeline
    if user_id:
        auth_token = f"slack:{user_id}"
        payload["metadata"] = {
            "X-Auth-Token": auth_token,
            "user_id": user_id
        }
        logger.info(f"Added user auth token to metadata: {auth_token}")
    
    logger.info(f"LLM API URL: {LLM_API_URL}")
    logger.info(f"LLM Model: {LLM_MODEL}")
    
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True
        
    try:
        logger.info(f"Sending request to LLM API with {len(messages)} messages")
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
    
    # Show thinking indicator
    thinking_message = await client.chat_postMessage(
        channel=channel,
        text="⏳ _Starting process..._",
        thread_ts=thread_ts,
        mrkdwn=True
    )
    
    # Run the agent process
    result = await run_agent_process(action_id)
    
    # Delete thinking message
    try:
        await client.chat_delete(
            channel=channel,
            ts=thinking_message["ts"]
        )
    except Exception:
        pass
    
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

async def handle_message(
    text: str,
    user_id: str,
    client: WebClient,
    channel: str,
    thread_ts: Optional[str] = None
):
    logger.info(f"Handling message: '{text}' from user {user_id} in channel {channel}, thread {thread_ts}")
    
    # For tracking the thinking indicator message
    thinking_message_ts = None
    
    try:
        # Log thread info
        if thread_ts:
            logger.info(f"Responding in existing thread: {thread_ts}")
        else:
            logger.info("Starting a new thread")
            
        # Post a thinking message (we'll delete this later)
        try:
            thinking_response = await client.chat_postMessage(
                channel=channel,
                text="⏳ _Thinking..._",
                thread_ts=thread_ts,
                mrkdwn=True
            )
            thinking_message_ts = thinking_response["ts"]
            logger.info(f"Posted thinking message: {thinking_message_ts}")
        except Exception as msg_error:
            logger.error(f"Error posting thinking message: {msg_error}")
            
        # Retrieve thread history if this is a message in a thread
        thread_messages = []
        if thread_ts and thread_ts != "None":
            try:
                logger.info(f"Retrieving thread history for thread {thread_ts}")
                history_response = await client.conversations_replies(
                    channel=channel,
                    ts=thread_ts,
                    limit=20  # Get up to 20 messages of context
                )
                
                if history_response and history_response.get("messages"):
                    messages = history_response["messages"]
                    logger.info(f"Retrieved {len(messages)} messages from thread history")
                    
                    # Get bot's user ID to identify bot messages
                    bot_info = await client.auth_test()
                    bot_user_id = bot_info.get("user_id")
                    
                    # Process each message in the thread
                    for msg in messages:
                        # Skip the current message (it's the one we're processing)
                        if msg.get("ts") == thread_ts and not text:
                            continue
                            
                        # Skip the thinking indicator message if we posted one
                        if thinking_message_ts and msg.get("ts") == thinking_message_ts:
                            continue
                            
                        msg_text = msg.get("text", "").strip()
                        msg_user = msg.get("user")
                        
                        # Clean up message text (remove mentions)
                        if "<@" in msg_text:
                            msg_text = re.sub(r'<@[A-Z0-9]+>', '', msg_text).strip()
                        
                        # Skip empty messages
                        if not msg_text:
                            continue
                            
                        # Add to thread messages with appropriate role
                        if msg_user == bot_user_id:
                            thread_messages.append({"role": "assistant", "content": msg_text})
                        else:
                            thread_messages.append({"role": "user", "content": msg_text})
                            
                    logger.info(f"Processed {len(thread_messages)} meaningful messages from thread")
            except Exception as e:
                logger.error(f"Error retrieving thread history: {e}")
                import traceback
                logger.error(f"Thread history error traceback: {traceback.format_exc()}")
        
        # Use the LLM to generate a response
        llm_response = None
        try:
            async with aiohttp.ClientSession() as session:
                # We'll add the auth header through our modified get_llm_response function
                # Start with system message
                messages = [
                    {"role": "system", "content": "You are a helpful assistant for Insight Mesh, a RAG (Retrieval-Augmented Generation) system. You help users understand and work with their data. You can also start agent processes on behalf of users when they request it."},
                ]
                
                # Add thread history if available
                if thread_messages:
                    messages.extend(thread_messages)
                    logger.info("Added thread history to context")
                
                # Add current message if it's not already included in thread history
                if text and (not thread_messages or thread_messages[-1]["content"] != text):
                    messages.append({"role": "user", "content": text})
                
                logger.info(f"Sending request to LLM API with {len(messages)} messages")
                llm_response = await get_llm_response(
                    messages=messages, 
                    session=session,
                    user_id=user_id  # Pass user_id to the function
                )
                logger.info(f"Got LLM response: {llm_response is not None}")
        except Exception as llm_error:
            logger.error(f"Error getting LLM response: {llm_error}")
            import traceback
            logger.error(f"LLM error traceback: {traceback.format_exc()}")
            
        # Delete the thinking message if we posted one
        if thinking_message_ts:
            try:
                await client.chat_delete(
                    channel=channel,
                    ts=thinking_message_ts
                )
                logger.info(f"Deleted thinking message: {thinking_message_ts}")
            except Exception as delete_error:
                logger.error(f"Error deleting thinking message: {delete_error}")
            
        # Send the response
        try:
            if llm_response:
                logger.info(f"Sending response to Slack: channel={channel}, thread_ts={thread_ts}")
                response = await client.chat_postMessage(
                    channel=channel,
                    text=llm_response,
                    thread_ts=thread_ts
                )
                logger.info(f"Response sent successfully")
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
                
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        import traceback
        logger.error(f"Handle message traceback: {traceback.format_exc()}")
        
        # Delete the thinking message if there was an error
        if thinking_message_ts:
            try:
                await client.chat_delete(
                    channel=channel,
                    ts=thinking_message_ts
                )
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

@app.event("assistant_thread_started")
async def handle_assistant_thread_started(body, client):
    """Handle the event when a user starts an AI assistant thread"""
    logger.info("Assistant thread started")
    try:
        event = body["event"]
        channel_id = event["channel"]
        thread_ts = event.get("thread_ts")
        user_id = event.get("user")
        
        # Send a welcome message
        await client.chat_postMessage(
            channel=channel_id,
            text="👋 Hello! I'm Insight Mesh Assistant. I can help answer questions about your data or start agent processes for you.",
            thread_ts=thread_ts
        )
    except Exception as e:
        logger.error(f"Error handling assistant thread started: {e}")

@app.event("app_mention")
async def handle_mention(body, client):
    """Handle when the bot is mentioned in a channel"""
    logger.info("Received app mention")
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
        logger.error(f"Mention handler error: {traceback.format_exc()}")
        await client.chat_postMessage(
            channel=body["event"]["channel"],
            text="I'm sorry, I encountered an error while processing your request.",
            thread_ts=body["event"].get("thread_ts", body["event"].get("ts"))
        )

@app.event({"type": "message", "subtype": None})
@app.event("message")
async def handle_message_event(body, client):
    """Handle all message events including those in threads"""
    logger.info("Received message event")
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
        
        logger.debug(f"Processing message: channel_type={channel_type}, thread_ts={thread_ts}, text='{text}'")
        
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
        logger.error(f"Message handler error: {traceback.format_exc()}")

def main():
    """Start the Slack bot asynchronously"""
    # Set bot presence to "auto" (online) using a synchronous client
    try:
        from slack_sdk import WebClient as SyncWebClient
        token = os.environ.get("SLACK_BOT_TOKEN")
        
        # Log token format (first few chars) for debugging
        if token:
            token_prefix = token[:10] + "..." if len(token) > 10 else token
            logger.info(f"Bot token prefix: {token_prefix}")
        else:
            logger.error("SLACK_BOT_TOKEN is not set")
            
        sync_client = SyncWebClient(token=token)
        
        # Get bot user info first to verify we have the right user
        auth_test = sync_client.auth_test()
        logger.info(f"Auth test response: {auth_test}")
        logger.info(f"Bot user ID: {auth_test.get('user_id')}")
        logger.info(f"Bot name: {auth_test.get('user')}")
        
        # Set presence with detailed logging
        logger.info("Setting presence to 'auto'...")
        presence_response = sync_client.users_setPresence(presence="auto")
        logger.info(f"Presence API response: {presence_response}")
        
    except Exception as e:
        logger.error(f"Error setting bot presence: {e}")
        import traceback
        logger.error(f"Presence error traceback: {traceback.format_exc()}")
    
    async def maintain_presence():
        """Keep the bot's presence status active"""
        while True:
            try:
                from slack_sdk import WebClient as SyncWebClient
                sync_client = SyncWebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
                sync_client.users_setPresence(presence="auto")
                logger.debug("Updated bot presence status")
            except Exception as e:
                logger.error(f"Error updating presence: {e}")
            
            # Sleep for 5 minutes
            await asyncio.sleep(300)
    
    async def run():
        # Start the presence maintenance task
        asyncio.create_task(maintain_presence())
        
        # Start the Socket Mode handler
        handler = AsyncSocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
        logger.info("Starting Insight Mesh Assistant...")
        await handler.start_async()
    
    asyncio.run(run())

if __name__ == "__main__":
    main() 