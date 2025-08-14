# Slack Message Deletion Bot

A powerful Slack bot that allows workspace administrators to delete messages and replies through multiple methods: right-click shortcuts for individual messages and slash commands for time-based bulk deletion. Features comprehensive time format support and silent operation.

## ✨ Features

- **🔧 Admin Power**: Workspace admins can delete messages from anyone
- **👤 User Control**: Regular users can delete their own messages  
- **🔇 Silent Operation**: No confirmation messages - messages just disappear
- **📦 Bulk Deletion**: Removes selected message and all its replies
- **⚡ Real-time**: Uses Socket Mode for instant responses
- **🛡️ Smart Permissions**: Automatically detects user roles and permissions
- **📝 Detailed Logging**: Comprehensive logging for debugging and monitoring
- **💬 Slash Command**: Use `/remove-orphaned-messages` with flexible time formats
- **⏰ Time-Based Bulk Deletion**: Remove all messages from specified time periods
- **🎯 Comprehensive Formats**: Supports 1H, 2D, 30M, 1 hour, 2 days, etc.
- **🔗 Reply Deletion**: Automatically removes message threads and replies

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.6+
- Slack workspace with admin access
- Slack app creation permissions

### 2. Installation

```bash
# Clone or download the bot files
# Download or clone this repository

# Install dependencies
pip install -r requirements.txt

# Create environment file
# Create a .env file with your tokens (see Environment Setup below)
```

**💡 Pro Tip**: Use the included `manifest.json` file when creating your Slack app for automatic configuration!

### 3. Environment Setup

Create a `.env` file with your tokens:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here  
SLACK_USER_TOKEN=xoxp-your-user-token-here
```

**⚠️ Critical:** The `SLACK_USER_TOKEN` is required for admins to delete messages from other users. Without it, even admins can only delete their own messages.

### 4. Run the Bot

```bash
python app.py
```

## 🔐 Slack App Configuration

Choose one of the two setup methods below. The **App Manifest method is strongly recommended** as it automatically configures everything for you.

---

## 🚀 Method 1: App Manifest Setup (Recommended)

The fastest and most reliable way to set up your Slack app. This method uses the included `manifest.json` file to automatically configure all settings.

### Step 1: Create App from Manifest

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From an app manifest"**
3. Select your workspace
4. Choose **JSON** format
5. Copy and paste the **entire contents** of [`manifest.json`](manifest.json) from this repository
6. Review the configuration and click **"Create"**
7. ✅ **Done!** Your app is now configured with all necessary settings

### Step 2: Generate App-Level Token

1. Go to **Basic Information** → **App-Level Tokens**
2. Click **"Generate Token and Scopes"**
3. Configure the token:
   - **Token Name**: `socket_token`
   - **Scopes**: Select `connections:write`
4. Click **"Generate"**
5. **Copy the token** (starts with `xapp-`) → This is your `SLACK_APP_TOKEN`

### Step 3: Install App & Get OAuth Tokens

1. Go to **OAuth & Permissions**
2. Click **"Install to Workspace"**
3. **Authorize the app** (review and accept permissions)
4. Copy the tokens:
   - **Bot User OAuth Token** (starts with `xoxb-`) → This is your `SLACK_BOT_TOKEN`
   - **User OAuth Token** (starts with `xoxp-`) → This is your `SLACK_USER_TOKEN`

### ✅ Manifest Setup Complete!

Your app is now fully configured with:
- ✅ Socket Mode enabled
- ✅ All OAuth scopes configured
- ✅ Message shortcut created
- ✅ Slash command registered
- ✅ Event subscriptions set up
- ✅ Interactivity enabled

**Next**: Add your tokens to the `.env` file and run the bot!

---

## 🛠️ Method 2: Manual Setup (Alternative)

If you prefer to configure everything manually or need to customize settings, follow this step-by-step process.

### Step 1: Create New App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Configure basic information:
   - **App Name**: `Message Remover Bot`
   - **Development Slack Workspace**: Select your workspace
4. Click **"Create App"**

### Step 2: Configure Socket Mode

1. Go to **Socket Mode** in the left sidebar
2. **Enable Socket Mode** (toggle on)
3. Create an **App-Level Token**:
   - Click **"Generate Token and Scopes"**
   - **Token Name**: `socket_token`
   - **Scopes**: Select `connections:write`
   - Click **"Generate"**
4. **Copy the token** (starts with `xapp-`) → This is your `SLACK_APP_TOKEN`

### Step 3: Configure OAuth Scopes

1. Go to **OAuth & Permissions** in the left sidebar
2. Scroll to **Bot Token Scopes** and add these scopes:
   - `app_mentions:read` - Respond to @mentions
   - `chat:write` - Send messages and confirmations
   - `channels:read` - Access channel information
   - `channels:history` - Read message history in public channels
   - `groups:history` - Read message history in private channels
   - `im:history` - Read direct message history
   - `mpim:history` - Read group DM history
   - `users:read` - Check user admin permissions
   - `commands` - Handle slash commands

3. Scroll to **User Token Scopes** and add these scopes:
   - `chat:write` - Delete messages as user (critical for admin functionality)
   - `channels:history` - Access channel history
   - `groups:history` - Access private channel history
   - `im:history` - Access DM history
   - `mpim:history` - Access group DM history

### Step 4: Install App & Get OAuth Tokens

1. Still in **OAuth & Permissions**
2. Click **"Install to Workspace"**
3. **Authorize the app** (review and accept permissions)
4. Copy the tokens:
   - **Bot User OAuth Token** (starts with `xoxb-`) → This is your `SLACK_BOT_TOKEN`
   - **User OAuth Token** (starts with `xoxp-`) → This is your `SLACK_USER_TOKEN`

### Step 5: Configure Slash Commands

1. Go to **Slash Commands** in the left sidebar
2. Click **"Create New Command"**
3. Configure the command:
   - **Command**: `/remove-orphaned-messages`
   - **Request URL**: Leave blank (Socket Mode handles this)
   - **Short Description**: `Remove messages from a time period with flexible formats (1H, 2D, 30M, 1 hour, etc.)`
   - **Usage Hint**: `<time_period>`
4. Click **"Save"**

### Step 6: Configure Message Shortcuts

1. Go to **Interactivity & Shortcuts** in the left sidebar
2. **Enable Interactivity** (toggle on)
3. **Request URL**: Leave blank (Socket Mode handles this)
4. Under **Shortcuts**, click **"Create New Shortcut"**
5. Select **"On messages"**
6. Configure the shortcut:
   - **Name**: `Remove Message & Replies`
   - **Description**: `Silently remove this message and all its replies`
   - **Callback ID**: `delete-message-with-all-threads`
7. Click **"Save"**

### Step 7: Configure Event Subscriptions

1. Go to **Event Subscriptions** in the left sidebar
2. **Enable Events** (toggle on)
3. **Request URL**: Leave blank (Socket Mode handles this)
4. Under **Subscribe to bot events**, click **"Add Bot User Event"**
5. Add this event:
   - `app_mention` - Respond to @mentions
6. Click **"Save Changes"**

### Step 8: Configure App Home (Optional)

1. Go to **App Home** in the left sidebar
2. Configure settings:
   - **Home Tab**: Disabled
   - **Messages Tab**: Enabled
   - **Allow users to send Slash commands and messages from the messages tab**: Enabled

### ✅ Manual Setup Complete!

Your app is now fully configured with all the same functionality as the manifest method.

**Next**: Add your tokens to the `.env` file and run the bot!

## 🎯 How to Use

### Method 1: Right-Click Shortcut (Individual Messages)

#### For Workspace Admins

1. **Right-click any message** (or click the three dots ⋯)
2. **Select "Remove Message & Replies"**
3. **Message disappears instantly** - no confirmation needed
4. **All replies are also deleted**

#### For Regular Users

1. **Right-click your own message**
2. **Select "Remove Message & Replies"** 
3. **Your message disappears** - only works on your own messages

### Method 2: Slash Command (Bulk Time-Based Deletion)

#### Using `/remove-orphaned-messages`

**Basic Usage:**
```
/remove-orphaned-messages <time_period>
```

**Examples:**
```bash
/remove-orphaned-messages 2H              # Remove orphaned messages from last 2 hours
/remove-orphaned-messages 1D              # Remove orphaned messages from last 1 day  
/remove-orphaned-messages 30M             # Remove orphaned messages from last 30 minutes
/remove-orphaned-messages 1 hour          # Remove orphaned messages from last 1 hour
/remove-orphaned-messages 2 days          # Remove orphaned messages from last 2 days
/remove-orphaned-messages                 # Show help (no parameters)
```

**Supported Time Formats:**
- **Concise**: `30M`, `2H`, `1D` (minutes, hours, days)
- **Alternative**: `30m`, `2h`, `1d` (lowercase also works)
- **Full Words**: `30 minutes`, `2 hours`, `1 day`
- **Abbreviated**: `30 min`, `2 hour`, `1 d`

**Key Features:**
- ✅ **Bulk time-based deletion** - removes all orphaned messages from specified period
- ✅ **Includes all replies** - deletes message threads completely
- ✅ **Silent operation** - no confirmation messages on success
- ✅ **Smart timing** - includes messages sent right before command
- ✅ **Same permission rules** as right-click method
- ✅ **Built-in help** - run without parameters to see usage guide
- ✅ **Error handling** - clear messages only when something goes wrong
- ✅ **Current channel only** - operates on the channel where command is used

**Permissions:**
- **Admins**: Can remove any messages and replies from the time period
- **Regular Users**: Can only remove their own messages and replies from the time period

**Getting Help:**
Simply run `/remove-orphaned-messages` without any parameters to see the built-in help with examples and format options.

### Check Your Permissions

Mention the bot to see your current permissions:
```
@Message Remover
```

(The bot's display name is "Message Remover" as configured in the manifest)

Response examples:
- **Admin**: `Hello John! 👋 Your Status: Admin ⚡ Delete Permissions: You can delete messages from anyone!`
- **User**: `Hello Jane! 👋 Your Status: Member 👤 Delete Permissions: You can only delete your own messages.`

## 🔧 Permission System

### Workspace Roles

| Role | Can Delete Own Messages | Can Delete Others' Messages | Requirements |
|------|------------------------|----------------------------|--------------|
| **Primary Owner** 👑 | ✅ Yes | ✅ Yes | User token configured |
| **Owner** 🔑 | ✅ Yes | ✅ Yes | User token configured |
| **Admin** ⚡ | ✅ Yes | ✅ Yes | User token configured |
| **Member** 👤 | ✅ Yes | ❌ No | - |
| **Guest** 👥 | ✅ Yes | ❌ No | - |

### Technical Details

- **Bot Token**: Can delete the user's own messages and bot messages
- **User Token**: Required for admins to delete messages from other users
- **Permission Check**: Bot automatically detects user role on each action
- **Fallback**: If user token unavailable, admins can only delete their own messages and bot messages

## 🛠️ Troubleshooting

### Common Issues

#### ❌ "No messages could be deleted" (For Admins)

**Most likely cause**: Missing or invalid user token

**Solutions**:
1. Verify `SLACK_USER_TOKEN` is in your `.env` file
2. Ensure the user token starts with `xoxp-`
3. Check that User Token Scopes are properly configured
4. Try reinstalling the app to workspace

#### ❌ Action doesn't appear in menu

**Solutions**:
1. Verify the bot is installed to your workspace
2. Check that Callback ID is exactly `delete-message-with-all-threads`
3. Ensure Interactivity is enabled
4. Reinstall the app if needed

#### ❌ Bot doesn't respond to mentions

**Solutions**:
1. Check Socket Mode is enabled
2. Verify `SLACK_APP_TOKEN` is correct
3. Ensure `app_mention` event is subscribed
4. Check console for connection errors

#### ❌ Permission denied for own messages

**Solutions**:
1. Message might be too old (Slack has time limits)
2. Check if you're in a restricted channel
3. Verify bot has proper scopes

### Debug Information

The bot logs detailed information to help with troubleshooting:

```bash
# Run with verbose logging
python app.py

# Look for these log messages:
# - "User [ID] admin status - Admin: True/False, Owner: True/False"  
# - "Using user token for admin deletion" or "Using bot token for deletion"
# - "Successfully deleted message with ts: [timestamp]"
# - "Failed to delete message with ts: [timestamp]"
```

### Getting Help

1. **Check the logs** - Most issues show up in console output
2. **Mention the bot** - Verify your permissions and token status
3. **Reinstall the app** - Sometimes fixes permission issues
4. **Check Slack API status** - api.slack.com/status

## 🔒 Security & Privacy

### What the Bot Can Access

- **Message content**: Only for deletion purposes, not stored
- **User information**: Only admin status, not personal data  
- **Channel access**: Only channels where bot is invited
- **Deletion logs**: Stored locally for debugging

### Best Practices

- **Limit admin access**: Only give admin roles to trusted users
- **Secure tokens**: Keep your `.env` file private and secure
- **Regular audits**: Monitor deletion logs for unusual activity
- **Backup important data**: Consider message exports before deployment

### Token Security

```bash
# Secure your .env file
chmod 600 .env

# Never commit tokens to version control
echo ".env" >> .gitignore

# Use environment variables in production
export SLACK_USER_TOKEN="xoxp-..."
```

## 📝 Development

### File Structure

```
slackbot/
├── app.py              # Main bot application
├── README.md           # This documentation
├── requirements.txt    # Python dependencies
├── manifest.json       # Slack app manifest
├── .env               # Environment variables (create this)
└── .gitignore         # Git ignore file
```

### Key Dependencies

```txt
slack-bolt>=1.14.0
python-dotenv>=0.19.0
```

### App Manifest

The `manifest.json` file contains the complete Slack app configuration and can be used to automatically set up:
- OAuth scopes (bot and user tokens)
- Event subscriptions
- Interactivity settings
- Message shortcuts
- Socket mode configuration

This eliminates the need for manual configuration in most cases.

### Customization

#### Change the Action Name

Edit the message action name in your Slack app settings under **Interactivity & Shortcuts**.

#### Modify Deletion Behavior

Edit the `handle_message_action` function in `app.py`:

```python
# Example: Add deletion confirmation
if successful_deletions > 0:
    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id, 
        text=f"✅ Deleted {successful_deletions} messages"
    )
```

#### Add More Actions

Create additional shortcuts by:
1. Adding new `@app.shortcut("callback_id")` handlers
2. Configuring them in Slack app settings

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📋 FAQ

**Q: Can regular users delete messages from others?**  
A: No, only workspace admins/owners can delete messages from other users.

**Q: Are deleted messages recoverable?**  
A: No, deletion is permanent. Consider message exports for backup.

**Q: Does this work in all channel types?**  
A: Yes - public channels, private channels, DMs, and group DMs.

**Q: Can I delete very old messages?**  
A: Slack has time limits on message deletion. Very old messages may not be deletable.

**Q: Will users know who deleted their message?**  
A: No, the deletion appears to happen silently without attribution.

**Q: Can I run this on multiple workspaces?**  
A: You need separate app configurations and tokens for each workspace.

## 📄 License

This project is open source. Use responsibly and in accordance with your organization's policies.

---

**⚠️ Important**: This bot gives significant power to delete messages. Ensure proper governance and only grant admin access to trusted users. 