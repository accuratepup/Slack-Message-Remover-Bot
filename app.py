from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.respond import Respond
from slack_sdk import WebClient
import os
import json

from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN")  # Add user token for admin operations

app = App(token=SLACK_BOT_TOKEN)

# Create a separate client for user token operations
user_client = WebClient(token=SLACK_USER_TOKEN) if SLACK_USER_TOKEN else None

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

# delete-message-with-all-threads shortcut - appears in three-dots menu
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

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()