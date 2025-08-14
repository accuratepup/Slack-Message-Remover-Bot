from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.respond import Respond
from slack_sdk import WebClient
import os
import json
import re
import logging

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN")  # Add user token for admin operations

app = App(token=SLACK_BOT_TOKEN)

# Create a separate client for user token operations
user_client = WebClient(token=SLACK_USER_TOKEN) if SLACK_USER_TOKEN else None

# Help text for the remove-orphaned-messages command
REMOVE_ORPHANED_MESSAGES_HELP = """*🗑️ Remove Orphaned Messages Command Help*

*Usage:*
`/remove-orphaned-messages <time_period>`

*Examples:*
• `/remove-orphaned-messages 2H` - Remove orphaned messages from last 2 hours
• `/remove-orphaned-messages 1D` - Remove orphaned messages from last 1 day
• `/remove-orphaned-messages 30M` - Remove orphaned messages from last 30 minutes
• `/remove-orphaned-messages 1 hour` - Remove orphaned messages from last 1 hour
• `/remove-orphaned-messages 2 days` - Remove orphaned messages from last 2 days

*Supported Formats:*
• **Concise**: `30M`, `2H`, `1D` (minutes, hours, days)
• **Full**: `30 minutes`, `2 hours`, `1 day`

*What it does:*
• Removes all orphaned messages from the specified time period in this channel
• Admins can remove any orphaned messages
• Regular users can only remove their own orphaned messages

*Permissions:*
"""

print("🤖 Bot starting up...")
print(f"Bot token configured: {'✅' if SLACK_BOT_TOKEN else '❌'}")
print(f"App token configured: {'✅' if SLACK_APP_TOKEN else '❌'}")
print(f"User token configured: {'✅' if SLACK_USER_TOKEN else '❌'}")

@app.event("app_mention")
def handle_app_mention(body, say, client, logger):
    user_id = body["event"]["user"]
    
    try:
        # Check user's admin status
        user_info = client.users_info(user=user_id)
        user_data = user_info.get("user", {})
        
        is_admin = user_data.get("is_admin", False)
        is_owner = user_data.get("is_owner", False)
        is_primary_owner = user_data.get("is_primary_owner", False)
        
        name = user_data.get("real_name", user_data.get("name", "Unknown"))
        
        # Check if user token is available for admin operations
        user_token_available = SLACK_USER_TOKEN is not None
        
        if is_primary_owner:
            status = "Primary Owner 👑"
            if user_token_available:
                permissions = "You can delete messages from anyone!"
            else:
                permissions = "You can delete messages from anyone! (User token needed for full functionality)"
        elif is_owner:
            status = "Owner 🔑"
            if user_token_available:
                permissions = "You can delete messages from anyone!"
            else:
                permissions = "You can delete messages from anyone! (User token needed for full functionality)"
        elif is_admin:
            status = "Admin ⚡"
            if user_token_available:
                permissions = "You can delete messages from anyone!"
            else:
                permissions = "You can delete messages from anyone! (User token needed for full functionality)"
        else:
            status = "Member 👤"
            permissions = "You can only delete your own messages."
        
        say(f"Hello {name}! 👋\n\n**Your Status:** {status}\n**Delete Permissions:** {permissions}")
        
    except Exception as e:
        logger.error(f"Error checking user info: {e}")
        say("Hello, I'm here! 👋")

@app.shortcut("delete-message-with-all-threads")
def handle_message_action(ack, body, client, logger):
    # Acknowledge the action request
    ack()
    
    # Debug logging
    logger.info(f"Message action triggered! Body: {json.dumps(body, indent=2)}")
    
    try:
        # Get the message details
        message = body["message"]
        channel_id = body["channel"]["id"]
        user_id = body["user"]["id"]
        message_ts = message.get("ts", "")
        message_author = message.get("user", "")
        
        # Extract message text for logging
        message_text = message.get("text", "")
        logger.info(f"Processing message: {message_text[:50]}... from user {message_author} by requester {user_id} in channel {channel_id}")
        
        # Check if the user requesting deletion has admin permissions
        try:
            user_info = client.users_info(user=user_id)
            is_admin = user_info.get("user", {}).get("is_admin", False)
            is_owner = user_info.get("user", {}).get("is_owner", False)
            is_primary_owner = user_info.get("user", {}).get("is_primary_owner", False)
            
            has_admin_perms = is_admin or is_owner or is_primary_owner
            
            logger.info(f"User {user_id} admin status - Admin: {is_admin}, Owner: {is_owner}, Primary Owner: {is_primary_owner}")
            
        except Exception as e:
            logger.error(f"Error checking user permissions: {e}")
            has_admin_perms = False
        
        # Determine which client to use for deletion
        if has_admin_perms and user_client:
            # Use user token for admin operations
            delete_client = user_client
            logger.info("Using user token for admin deletion")
        else:
            # Use bot token for regular operations
            delete_client = client
            logger.info("Using bot token for deletion")
        
        # Check if this is the user's own message or if they have admin permissions
        can_delete = (message_author == user_id) or has_admin_perms
        
        if not can_delete:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="❌ You can only delete your own messages. Only workspace admins can delete messages from other users."
            )
            return
        
        # For admins without user token, show limitation message
        if has_admin_perms and not user_client:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⚠️ Admin detected but user token not configured. You can only delete your own messages and bot messages. See README for user token setup."
            )
        
        # Get all replies to this message
        try:
            replies_response = delete_client.conversations_replies(
                channel=channel_id,
                ts=message_ts
            )
            
            if replies_response["ok"]:
                messages_to_delete = replies_response["messages"]
                logger.info(f"Found {len(messages_to_delete)} messages to delete (including original)")
                
                successful_deletions = 0
                failed_deletions = 0
                
                # Delete all messages in reverse order (replies first, then original)
                for msg in reversed(messages_to_delete):
                    msg_ts = msg.get("ts", "")
                    msg_author = msg.get("user", "")
                    
                    # For each message, determine if we can delete it
                    if delete_client == user_client:
                        # With user token, admins can delete any message
                        can_delete_this = has_admin_perms
                    else:
                        # With bot token, only own messages and bot messages
                        can_delete_this = (msg_author == user_id) or (msg.get("bot_id") is not None)
                    
                    if not can_delete_this:
                        logger.info(f"Skipping message {msg_ts} - insufficient permissions to delete message from user {msg_author}")
                        failed_deletions += 1
                        continue
                    
                    try:
                        # Delete the message
                        delete_response = delete_client.chat_delete(
                            channel=channel_id,
                            ts=msg_ts
                        )
                        
                        if delete_response["ok"]:
                            logger.info(f"Successfully deleted message with ts: {msg_ts}")
                            successful_deletions += 1
                        else:
                            error_msg = delete_response.get('error', 'Unknown error')
                            logger.error(f"Failed to delete message with ts: {msg_ts}. Error: {error_msg}")
                            
                            # Handle specific error cases
                            if error_msg == "cant_delete_message":
                                logger.info(f"Cannot delete message {msg_ts} - insufficient permissions or message too old")
                            failed_deletions += 1
                            
                    except Exception as e:
                        logger.error(f"Exception while deleting message {msg_ts}: {e}")
                        failed_deletions += 1
                
                # Log results but don't send confirmation messages
                logger.info(f"Deletion complete - Success: {successful_deletions}, Failed: {failed_deletions}")
                
                # Only send message if there were failures (to inform user of issues)
                if failed_deletions > 0 and successful_deletions == 0:
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text="❌ No messages could be deleted. You may not have permission to delete these messages, or they may be too old to delete."
                    )
                
            else:
                logger.error(f"Failed to get replies: {replies_response.get('error', 'Unknown error')}")
                # Try to delete just the original message
                if can_delete:
                    delete_response = delete_client.chat_delete(
                        channel=channel_id,
                        ts=message_ts
                    )
                    
                    if delete_response["ok"]:
                        logger.info("Successfully deleted single message")
                    else:
                        error_msg = delete_response.get('error', 'Unknown error')
                        logger.error(f"Failed to delete message: {error_msg}")
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=f"❌ Failed to remove message: {error_msg}"
                        )
                else:
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text="❌ You don't have permission to delete this message."
                    )
                    
        except Exception as e:
            logger.error(f"Error getting replies: {e}")
            # Fallback: try to delete just the original message
            if can_delete:
                try:
                    delete_response = delete_client.chat_delete(
                        channel=channel_id,
                        ts=message_ts
                    )
                    
                    if delete_response["ok"]:
                        logger.info("Successfully deleted fallback message")
                    else:
                        error_msg = delete_response.get('error', 'Unknown error')
                        logger.error(f"Failed to delete fallback message: {error_msg}")
                        if error_msg == "cant_delete_message":
                            client.chat_postEphemeral(
                                channel=channel_id,
                                user=user_id,
                                text="❌ Cannot delete this message. You may not have permission or the message may be too old."
                            )
                        else:
                            client.chat_postEphemeral(
                                channel=channel_id,
                                user=user_id,
                                text=f"❌ Failed to remove message: {error_msg}"
                            )
                except Exception as delete_error:
                    logger.error(f"Error deleting original message: {delete_error}")
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text="❌ Failed to remove message due to an error."
                    )
            else:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="❌ You don't have permission to delete this message."
                )
        
    except Exception as e:
        logger.error(f"Error handling message action: {e}")
        # Try to send error message to user
        try:
            client.chat_postEphemeral(
                channel=body.get("channel", {}).get("id", ""),
                user=body.get("user", {}).get("id", ""),
                text="❌ An error occurred while processing your request."
            )
        except:
            pass

@app.command("/remove-orphaned-messages")
def handle_remove_messages_command(ack, body, client, logger, command):
    """Handle the /remove-orphaned-messages slash command"""
    ack()
    
    print("🗑️ /remove-orphaned-messages command triggered!")
    
    try:
        user_id = body["user_id"]
        channel_id = body["channel_id"]
        command_text = command.get("text", "").strip()
        
        print(f"User: {user_id}, Channel: {channel_id}, Text: '{command_text}'")
        logger.info(f"Remove messages command triggered by user {user_id} in channel {channel_id} with text: {command_text}")
        
        # Check user permissions
        try:
            user_info = client.users_info(user=user_id)
            is_admin = user_info.get("user", {}).get("is_admin", False)
            is_owner = user_info.get("user", {}).get("is_owner", False)
            is_primary_owner = user_info.get("user", {}).get("is_primary_owner", False)
            
            has_admin_perms = is_admin or is_owner or is_primary_owner
            
            logger.info(f"User {user_id} admin status - Admin: {is_admin}, Owner: {is_owner}, Primary Owner: {is_primary_owner}")
            
        except Exception as e:
            logger.error(f"Error checking user permissions: {e}")
            has_admin_perms = False
        
        # If no text provided, show help
        if not command_text:
            help_text = REMOVE_ORPHANED_MESSAGES_HELP + ("✅ You have admin permissions - can remove any orphaned messages" if has_admin_perms else "👤 You can only remove your own orphaned messages")
            
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=help_text
            )
            return
        
        # Parse time period
        import time
        from datetime import datetime, timedelta
        
        def parse_time_period(text):
            """Parse time period like '1 hour', '2 days', '30 minutes' into seconds"""
            text = text.strip()  # Don't convert to lowercase yet
            
            # Common patterns - check case-sensitive patterns first, then case-insensitive
            patterns = [
                # Single letter formats (both upper and lower case)
                (r'^(\d+)[Hh]$', 3600),                   # 2H, 2h, 24H, 24h
                (r'^(\d+)[Dd]$', 86400),                  # 1D, 1d, 7D, 7d
                (r'^(\d+)[Mm]$', 60),                     # 30M, 30m, 45M, 45m
                
                # Word formats with optional 's' (case-insensitive)
                (r'^(\d+)\s*h(?:our)?s?$', 3600),          # 1h, 2hours, 3 hour
                (r'^(\d+)\s*m(?:in)?(?:ute)?s?$', 60),     # 1m, 30min, 45 minutes
                (r'^(\d+)\s*d(?:ay)?s?$', 86400),          # 1d, 2days, 3 day
            ]
            
            for i, (pattern, multiplier) in enumerate(patterns):
                if i < 3:  # First 3 patterns are case-sensitive
                    match = re.match(pattern, text)
                else:  # Rest are case-insensitive
                    match = re.match(pattern, text.lower())
                if match:
                    return int(match.group(1)) * multiplier
            
            return None
        
        seconds = parse_time_period(command_text)
        if seconds is None:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="❌ Invalid time format. Use formats like: `2H`, `1D`, `30M` or `2 hours`, `1 day`, `30 minutes`"
            )
            return
        
        # Calculate cutoff time with a small buffer to include recent messages
        current_time = time.time()
        cutoff_time = current_time - seconds - 30  # Add 30 second buffer
        cutoff_datetime = datetime.fromtimestamp(cutoff_time)
        current_datetime = datetime.fromtimestamp(current_time)
        
        logger.info(f"Current time: {current_datetime} (timestamp: {current_time})")
        logger.info(f"Cutoff time: {cutoff_datetime} (timestamp: {cutoff_time}) - with 30s buffer")
        logger.info(f"Looking for messages newer than {cutoff_datetime} ({command_text} ago + 30s buffer)")
        
        # Determine which client to use for deletion
        if has_admin_perms and user_client:
            delete_client = user_client
            logger.info("Using user token for admin deletion")
        else:
            delete_client = client
            logger.info("Using bot token for deletion")
        
        # For admins without user token, show limitation message
        if has_admin_perms and not user_client:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="⚠️ Admin detected but user token not configured. You can only delete your own messages and bot messages. See README for user token setup."
            )
        
        # Get messages from the time period
        try:
            # Get channel history from the cutoff time
            logger.info(f"Retrieving messages since {cutoff_datetime} (timestamp: {cutoff_time})")
            
            # Format the timestamp properly for Slack API (string with 6 decimal places)
            oldest_param = f"{cutoff_time:.6f}"
            logger.info(f"API call parameters - oldest: '{oldest_param}', inclusive: True")
            
            history_response = delete_client.conversations_history(
                channel=channel_id,
                oldest=oldest_param,
                inclusive=True,  # Include messages with exact timestamp
                limit=1000  # Slack API limit
            )
            
            logger.info(f"API Response: {history_response.get('ok')}, Messages count: {len(history_response.get('messages', []))}")
            
            # If no messages with inclusive=True, try without it
            if history_response.get('ok') and len(history_response.get('messages', [])) == 0:
                logger.info("Trying API call without inclusive parameter...")
                history_response_2 = delete_client.conversations_history(
                    channel=channel_id,
                    oldest=oldest_param,
                    limit=1000
                )
                logger.info(f"API Response (no inclusive): {history_response_2.get('ok')}, Messages count: {len(history_response_2.get('messages', []))}")
                
                # If this works better, use it
                if len(history_response_2.get('messages', [])) > 0:
                    logger.info("Using results from call without inclusive parameter")
                    history_response = history_response_2
            
            # Debug: Show first few messages found
            messages_found = history_response.get('messages', [])
            if messages_found:
                logger.info("Sample messages found:")
                for i, msg in enumerate(messages_found[:3]):  # Show first 3 messages
                    msg_time = datetime.fromtimestamp(float(msg.get('ts', 0)))
                    logger.info(f"  Message {i+1}: {msg.get('user', 'unknown')} at {msg_time} - {msg.get('text', '[no text]')[:50]}")
            else:
                logger.info("No messages returned by API call")
                # Let's also try without the oldest parameter to see if we get ANY messages
                test_response = delete_client.conversations_history(channel=channel_id, limit=5)
                logger.info(f"Test call (no time filter): {test_response.get('ok')}, Messages: {len(test_response.get('messages', []))}")
                
                # Show what messages the test call found
                test_messages = test_response.get('messages', [])
                if test_messages:
                    logger.info("Messages found in test call:")
                    for i, msg in enumerate(test_messages):
                        try:
                            msg_time = datetime.fromtimestamp(float(msg.get('ts', 0)))
                            logger.info(f"  Test Message {i+1}: {msg.get('user', 'unknown')} at {msg_time} (ts: {msg.get('ts')}) - {msg.get('text', '[no text]')[:50]}")
                            logger.info(f"    Cutoff: {cutoff_time}, Message: {float(msg.get('ts', 0))}, Should include: {float(msg.get('ts', 0)) > cutoff_time}")
                        except Exception as e:
                            logger.info(f"  Test Message {i+1}: Error parsing - {e}")
                else:
                    logger.info("No messages in test call either")
            
            if not history_response["ok"]:
                error_msg = history_response.get('error', 'Unknown error')
                logger.error(f"API call failed: {error_msg}")
                
                # Show helpful error message based on the specific error
                if error_msg == "not_in_channel":
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text="❌ The bot needs to be added to this channel first. Please invite the bot to this channel and try again."
                    )
                elif error_msg == "channel_not_found":
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text="❌ Channel not found. The bot may not have access to this channel."
                    )
                else:
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=f"❌ Could not retrieve channel history: {error_msg}"
                    )
                return
            
            messages_to_process = history_response["messages"]
            
            if not messages_to_process:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"ℹ️ No messages found in the last {command_text}."
                )
                return
            
            logger.info(f"Found {len(messages_to_process)} messages from the last {command_text}")
            
            successful_deletions = 0
            failed_deletions = 0
            skipped_deletions = 0
            total_processed = 0
            
            # Process each message
            for msg in messages_to_process:
                
                if msg.get("subtype") != "tombstone":
                    continue

                msg_ts = msg.get("ts", "")
                msg_author = msg.get("user", "")
                msg_text = msg.get("text", "")[:50] + "..." if msg.get("text") else "[no text]"
                
                logger.info(f"Processing message from {msg_author} at {msg_ts}: {msg_text}")
                
                # Convert timestamp to readable format for debugging
                try:
                    msg_datetime = datetime.fromtimestamp(float(msg_ts))
                    logger.info(f"Message time: {msg_datetime} (timestamp: {msg_ts})")
                except:
                    logger.info(f"Could not parse message timestamp: {msg_ts}")
                
                # Skip only if it's the actual command message itself (has slash command indicator)
                if msg.get("subtype") == "bot_message" and "/remove-orphaned-messages" in msg.get("text", ""):
                    logger.info(f"Skipping the command message itself at {msg_ts}")
                    continue
                
                logger.info(f"---------msg_ts: {msg_ts}---------")
                total_processed += 1
                
                # For each message, determine if we can delete it
                if delete_client == user_client:
                    # With user token, admins can delete any message
                    can_delete_this = has_admin_perms
                    logger.info(f"---------msg_ts: {msg}---------")
                    logger.info(f"Using user token - Admin perms: {has_admin_perms}")
                else:
                    # With bot token, only own messages and bot messages
                    can_delete_this = (msg_author == user_id) or (msg.get("bot_id") is not None)
                    logger.info(f"Using bot token - Can delete: {can_delete_this} (own: {msg_author == user_id}, bot: {msg.get('bot_id') is not None})")
                
                if not can_delete_this:
                    logger.info(f"Skipping message {msg_ts} - insufficient permissions to delete message from user {msg_author}")
                    skipped_deletions += 1
                    continue
                
                # Get all replies to this message (including the original message)
                try:
                    replies_response = delete_client.conversations_replies(
                        channel=channel_id,
                        ts=msg_ts
                    )
                    
                    if replies_response["ok"]:
                        messages_to_delete = replies_response["messages"]
                        logger.info(f"Found {len(messages_to_delete)} messages to delete for thread {msg_ts} (including original)")
                        
                        # Delete all messages in reverse order (replies first, then original)
                        thread_successful = 0
                        thread_failed = 0
                        
                        for thread_msg in reversed(messages_to_delete):
                            thread_msg_ts = thread_msg.get("ts", "")
                            thread_msg_author = thread_msg.get("user", "")
                            
                            # Check permissions for each message in the thread
                            if delete_client == user_client:
                                can_delete_thread_msg = has_admin_perms
                            else:
                                can_delete_thread_msg = (thread_msg_author == user_id) or (thread_msg.get("bot_id") is not None)
                            
                            if not can_delete_thread_msg:
                                logger.info(f"Skipping thread message {thread_msg_ts} - insufficient permissions")
                                thread_failed += 1
                                continue
                            
                            try:
                                # Delete the message
                                delete_response = delete_client.chat_delete(
                                    channel=channel_id,
                                    ts=thread_msg_ts
                                )
                                
                                if delete_response["ok"]:
                                    logger.info(f"Successfully deleted thread message with ts: {thread_msg_ts}")
                                    thread_successful += 1
                                else:
                                    error_msg = delete_response.get('error', 'Unknown error')
                                    logger.error(f"Failed to delete thread message with ts: {thread_msg_ts}. Error: {error_msg}")
                                    thread_failed += 1
                                    
                            except Exception as e:
                                logger.error(f"Exception while deleting thread message {thread_msg_ts}: {e}")
                                thread_failed += 1
                        
                        successful_deletions += thread_successful
                        failed_deletions += thread_failed
                        
                    else:
                        logger.error(f"Failed to get replies for {msg_ts}: {replies_response.get('error', 'Unknown error')}")
                        # Fallback: try to delete just the original message
                        try:
                            delete_response = delete_client.chat_delete(
                                channel=channel_id,
                                ts=msg_ts
                            )
                            
                            if delete_response["ok"]:
                                logger.info(f"Successfully deleted message with ts: {msg_ts} (fallback)")
                                successful_deletions += 1
                            else:
                                error_msg = delete_response.get('error', 'Unknown error')
                                logger.error(f"Failed to delete message with ts: {msg_ts}. Error: {error_msg}")
                                failed_deletions += 1
                                
                        except Exception as e:
                            logger.error(f"Exception while deleting message {msg_ts}: {e}")
                            failed_deletions += 1
                
                except Exception as e:
                    logger.error(f"Error getting replies for {msg_ts}: {e}")
                    # Fallback: try to delete just the original message
                    try:
                        delete_response = delete_client.chat_delete(
                            channel=channel_id,
                            ts=msg_ts
                        )
                        
                        if delete_response["ok"]:
                            logger.info(f"Successfully deleted message with ts: {msg_ts} (exception fallback)")
                            successful_deletions += 1
                        else:
                            error_msg = delete_response.get('error', 'Unknown error')
                            logger.error(f"Failed to delete message with ts: {msg_ts}. Error: {error_msg}")
                            failed_deletions += 1
                            
                    except Exception as delete_e:
                        logger.error(f"Exception while deleting message {msg_ts}: {delete_e}")
                        failed_deletions += 1
            
            # Log results and send confirmation
            logger.info(f"Bulk deletion complete - Success: {successful_deletions}, Failed: {failed_deletions}, Skipped: {skipped_deletions}")
            
            # Send summary message only for errors or issues
            if successful_deletions == 0:
                if skipped_deletions > 0:
                    if has_admin_perms and not user_client:
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=f"⚠️ Found {total_processed} message{'s' if total_processed != 1 else ''} from the last {command_text}, but user token not configured. As an admin, you need a user token to delete messages from other users. See README for setup instructions."
                        )
                    elif not has_admin_perms:
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=f"ℹ️ Found {total_processed} message{'s' if total_processed != 1 else ''} from the last {command_text}, but you can only delete your own messages. Only workspace admins can delete messages from other users."
                        )
                    else:
                        client.chat_postEphemeral(
                            channel=channel_id,
                            user=user_id,
                            text=f"ℹ️ Found {total_processed} message{'s' if total_processed != 1 else ''} from the last {command_text}, but you don't have permission to delete them."
                        )
                else:
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=f"❌ No messages could be deleted from the last {command_text}. Messages may be too old or you may not have sufficient permissions."
                    )
            # Only show message if there were significant failures
            elif failed_deletions > 0 and failed_deletions >= successful_deletions:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text=f"⚠️ Some messages couldn't be deleted: {failed_deletions} failed, {successful_deletions} succeeded from the last {command_text}."
                )
                
        except Exception as e:
            logger.error(f"Error getting channel history: {e}")
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="❌ An error occurred while trying to retrieve messages from the channel."
            )
        
    except Exception as e:
        logger.error(f"Error handling remove-messages command: {e}")
        try:
            client.chat_postEphemeral(
                channel=body.get("channel_id", ""),
                user=body.get("user_id", ""),
                text="❌ An error occurred while processing your request."
            )
        except:
            pass

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    print("🚀 Starting bot...")
    handler.start()
    print("✅ Bot is running!")