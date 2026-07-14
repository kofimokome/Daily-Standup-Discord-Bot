# Discord Daily Standup Bot

A Python Discord bot that automates daily standup meetings by sending prompts at scheduled times, tracking responses, and following up on commitments.

## Features

- **Daily Standup Messages**: Automatically sends standup prompts at 5:00 PM (configurable)
- **Response Tracking**: Monitors and collects user responses to standup questions
- **Commitment Extraction**: Parses user messages to extract what they worked on today and what they'll work on tomorrow
- **Accountability Follow-ups**: Sends follow-up messages the next day asking if users completed their commitments
- **Persistent Storage**: Uses SQLite database to save commitments between bot restarts
- **Slash Commands**: Easy-to-use commands for configuration and management
- **Optional OpenAI Integration**: Uses OpenAI API for intelligent message parsing (falls back to pattern matching if not available)
- **Google Sheets Task Management** (Optional): Seamlessly integrates with Google Sheets for task tracking, assignment, and completion tracking

## Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) package manager (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`)
- A Discord account and bot token
- (Optional) OpenAI API key for intelligent parsing
- (Optional) Google Cloud account and service account credentials for task management features

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot" and confirm
5. Under "Token", click "Reset Token" or "Copy" to get your bot token
6. Save this token for later

### 2. Set Bot Permissions

1. In the Discord Developer Portal, go to the "OAuth2" > "URL Generator" section
2. Select the following scopes:
   - `bot`
   - `applications.commands`
3. Select the following bot permissions:
   - `Send Messages`
   - `Read Message History`
   - `View Channels`
   - `Use Slash Commands`
   - `Read Messages/View Channels`
   - `Embed Links` (optional, for better formatting)
4. Copy the generated URL and open it in your browser
5. Select the server where you want to add the bot
6. Click "Authorize"

### 3. Get Channel ID

1. Enable Developer Mode in Discord:
   - Go to User Settings > Advanced
   - Enable "Developer Mode"
2. Right-click on the channel where you want standup messages
3. Click "Copy ID"
4. Save this ID for later

### 4. Install uv (if not already installed)

Install `uv` using one of these methods:

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Or via pip:**
```bash
pip install uv
```

### 5. Install Dependencies

`uv` will automatically create and manage a virtual environment for you:

```bash
uv sync
```

This will:
- Create a virtual environment automatically (`.venv/`)
- Install all dependencies from `pyproject.toml`
- Create a `uv.lock` file for reproducible builds
- Make it ready to use

**Note:** The first time you run `uv sync`, it will create a `uv.lock` file. You should commit this file to version control for reproducible builds across different environments.

### 6. Configure Environment Variables

1. Create a `.env` file in the project root:
   ```bash
   touch .env
   ```

2. Edit `.env` and add the following variables:
   ```env
   # Discord Bot Configuration
   DISCORD_BOT_TOKEN=your_actual_bot_token
   DISCORD_CHANNEL_ID=your_channel_id
   
   # Standup Time Configuration (optional, defaults to 5:00 PM)
   STANDUP_HOUR=17
   STANDUP_MINUTE=0
   
   # Timezone Configuration (optional, defaults to UTC)
   # Examples: 'America/New_York', 'America/Los_Angeles', 'Europe/London', 'Asia/Tokyo'
   # See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for full list
   TIMEZONE=UTC
   
   # OpenAI API Configuration (optional)
   USE_OPENAI=false
   OPENAI_API_KEY=your_openai_key_if_using
   
   # Google Sheets Integration (optional, for task management)
   SPREADSHEET_ID=your_spreadsheet_id_here
   GOOGLE_CREDENTIALS_PATH=credentials.json
   GOOGLE_SHEETS_HEADER_ROW=6
   ```

   Replace `your_actual_bot_token` with your Discord bot token and `your_channel_id` with your Discord channel ID.
   
   **For Google Sheets integration:** See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for detailed setup instructions.

### 7. Run the Bot

Using `uv` to run the bot (automatically uses the virtual environment):

```bash
uv run python main.py
```

Or activate the virtual environment manually:

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python main.py
```

The bot should now be running and will send standup messages at the configured time.

## Deployment to Heroku

### Prerequisites

- A Heroku account (sign up at [heroku.com](https://www.heroku.com))
- Heroku CLI installed ([install instructions](https://devcenter.heroku.com/articles/heroku-cli))
- Git repository initialized

### Deployment Steps

1. **Install Heroku CLI** (if not already installed):
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku
   
   # Or download from https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Login to Heroku**:
   ```bash
   heroku login
   ```

3. **Create a Heroku App**:
   ```bash
   heroku create your-bot-name
   ```

4. **Set Environment Variables**:
   ```bash
   heroku config:set DISCORD_BOT_TOKEN=your_bot_token
   heroku config:set DISCORD_CHANNEL_ID=your_channel_id
   heroku config:set TIMEZONE=America/New_York
   heroku config:set STANDUP_HOUR=17
   heroku config:set STANDUP_MINUTE=0
   heroku config:set USE_OPENAI=false
   # If using OpenAI:
   # heroku config:set USE_OPENAI=true
   # heroku config:set OPENAI_API_KEY=your_openai_key
   
   # If using Google Sheets integration:
   # heroku config:set SPREADSHEET_ID=your_spreadsheet_id
   # heroku config:set GOOGLE_SHEETS_HEADER_ROW=6
   
   # For credentials, encode your credentials.json to base64 and set it:
   # macOS: base64 -i credentials.json  # Copy the output
   # Linux: base64 credentials.json  # Copy the output
   # heroku config:set GOOGLE_CREDENTIALS_BASE64="<paste_base64_string>"
   ```
   
   **Important:** For Google Sheets integration, see [HEROKU_CREDENTIALS_SETUP.md](HEROKU_CREDENTIALS_SETUP.md) for detailed instructions on setting up credentials on Heroku.
   
   **Quick Setup:**
   ```bash
   # 1. Encode your credentials.json file to base64
   # macOS:
   base64 -i credentials.json > temp_base64.txt
   # Linux:
   # base64 credentials.json > temp_base64.txt
   
   # 2. Copy the entire base64 string from temp_base64.txt and set it:
   heroku config:set GOOGLE_CREDENTIALS_BASE64="<paste_entire_base64_string_here>"
   
   # 3. Clean up
   rm temp_base64.txt
   ```
   
   The bot will automatically decode and use the credentials at runtime.

5. **Deploy to Heroku**:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

6. **Scale the Worker Dyno**:
   ```bash
   heroku ps:scale worker=1
   ```

7. **View Logs**:
   ```bash
   heroku logs --tail
   ```

### Important Notes for Heroku

- **Procfile**: The `Procfile` uses `python main.py`. Heroku will automatically detect Python and install dependencies from `requirements.txt` during the build process.

- **Database Persistence**: Heroku's filesystem is ephemeral. The SQLite database will be reset on each dyno restart. For production, consider:
  - Using Heroku Postgres (free tier available) and modifying the database layer
  - Using a persistent storage addon like Bucketeer
  - For now, the bot will work but data may be lost on restarts
  
- **Google Sheets Credentials**: If using Google Sheets integration:
  - Store credentials as base64-encoded config var: `GOOGLE_CREDENTIALS_BASE64`
  - The bot automatically decodes and writes the file at runtime
  - See [HEROKU_CREDENTIALS_SETUP.md](HEROKU_CREDENTIALS_SETUP.md) for detailed instructions
  - Ensure the service account email has access to your spreadsheet
  
- **Dyno Types**: 
  - Use **Standard** or **Eco** dyno (Eco dynos sleep after 30 minutes of inactivity, which is fine for a bot that runs scheduled tasks)
  - Standard 1X dyno: $25/month (recommended for 24/7 uptime)
  - Eco dyno: $5/month (sleeps when inactive, but scheduled tasks wake it up)

- **Monitoring**: 
  - Check `heroku logs --tail` regularly
  - Set up Heroku alerts for errors
  - Monitor dyno hours usage
  - Watch for API rate limits (Discord and Google Sheets APIs)

### Updating the Bot

After making changes:
```bash
git add .
git commit -m "Your commit message"
git push heroku main
```

The bot will automatically restart with the new code.

## Usage

### Slash Commands

The bot supports the following slash commands:

- `/set_channel <channel>` - Set the channel for daily standups
- `/set_time <hour> <minute>` - Change the daily message time (24-hour format)
- `/view_commitments` - View all pending commitments for today
- `/skip_today` - Skip today's standup (feature in development)
- `/test_standup` - Send a test standup message immediately
- `/schedule_test_standup <minutes>` - Schedule a test standup message X minutes from now (for testing)
- `/test_follow_ups` - Test follow-up messages for commitments (simulates next day)

### Task Management Commands (Google Sheets Integration)

The bot includes a powerful task management system that integrates directly with Google Sheets, allowing you to track tasks, assignments, and outcomes all from Discord.

**Available Commands:**

- **`/add_task`** - Add a new task via an interactive modal form
  - Opens a Discord modal with fields for:
    - **Description**: Detailed task description (supports multi-line text)
    - **Assigned To**: Username or Discord mention (e.g., `@user` or `john_doe`)
    - **Start Date**: Task start date in `YYYY-MM-DD` format
    - **End Date**: Task end date in `YYYY-MM-DD` format
    - **Measurable Outcome**: What should be achieved (supports multi-line text)
  - Tasks are automatically assigned a unique Task ID
  - Description column is automatically merged across multiple columns for better formatting
  - Sends a confirmation embed with task details

- **`/view_tasks [user]`** - View all tasks or filter by assigned user
  - Shows up to 10 most recent tasks (newest first)
  - Filter by username or Discord mention
  - Displays task status (Complete or In Progress)
  - Shows task description, assignee, dates, and outcomes

- **`/my_tasks`** - Show tasks assigned to you
  - Automatically detects your username, mention, or display name
  - Shows all your tasks with full details
  - Includes completion status and outcomes

- **`/complete_task <number> <outcome>`** - Mark a task as complete with an outcome
  - Updates the "Actual Outcome" column in Google Sheets
  - Records what was actually achieved
  - Sends a confirmation message

**Features:**

✅ **Automatic Task Numbering**: Tasks are assigned unique, auto-incrementing IDs  
✅ **Smart Merging**: Description column automatically merges cells for better formatting  
✅ **Recent Tasks First**: Tasks are displayed with newest first for better UX  
✅ **Flexible Filtering**: Filter tasks by username, mention, or partial match  
✅ **Rich Embeds**: All responses use Discord embeds for better readability  
✅ **Input Validation**: Date validation and format checking  
✅ **Error Handling**: Clear error messages if something goes wrong  

**Setup Required:**

Task management commands require Google Sheets integration. See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for detailed setup instructions.

**Sheet Format:**

Tasks are stored in a Google Sheet with the following columns:
- **Task ID**: Auto-incremented unique identifier
- **Status**: Task status (can be set manually in the sheet)
- **Description**: Task description (merged across columns C-F)
- **Assigned to**: Username or Discord mention
- **Start Date**: Task start date
- **End Date**: Task end date
- **Measurable Outcome**: Expected outcome
- **Actual Outcome**: What was actually achieved (set via `/complete_task`)

### How It Works

#### Daily Standup Workflow

1. **Daily Standup**: At the configured time (default 5:00 PM), the bot sends private DM reminders asking:
   - "What did you work on yesterday? What will you work on today?"

2. **Response Tracking**: Users reply to the standup message. The bot:
   - Monitors responses for 2-3 hours after the standup message
   - Accepts both replies to the standup message and direct messages in the channel
   - Parses the message to extract today's work and tomorrow's commitment
   - Saves the information to the database
   - Sends a confirmation message with what was recorded

3. **Follow-up Messages**: The next day, before the new standup (at 4:30 PM by default), the bot:
   - Sends a message to each user asking if they completed their commitment
   - Uses rich embeds for better visual appeal
   - Format: "Hey @user, yesterday you said you'd [commitment]. Did you get this done?"

#### Task Management Workflow

1. **Adding Tasks**: Use `/add_task` to open an interactive modal form
   - Fill in all required fields (description, assignee, dates, outcome)
   - Task is immediately added to Google Sheets with auto-incremented ID
   - Description cells are automatically merged for formatting
   - Confirmation message shows all task details

2. **Viewing Tasks**: Use `/view_tasks` or `/my_tasks` to see task lists
   - Tasks are displayed newest first
   - Shows status (Complete or In Progress)
   - Includes all relevant details in an organized embed

3. **Completing Tasks**: Use `/complete_task` when a task is finished
   - Updates the "Actual Outcome" column in Google Sheets
   - Records what was actually achieved
   - Task remains in the sheet for historical tracking

**Integration Benefits:**

- **Unified Workflow**: Manage standups and tasks all from Discord
- **Persistent Storage**: Tasks are stored in Google Sheets (accessible outside Discord)
- **Team Visibility**: Everyone can view tasks and assignments
- **Accountability**: Track commitments from standups and task outcomes
- **Historical Tracking**: All tasks and outcomes are preserved in the sheet

## File Structure

```
daily-standup-discord-bot/
├── main.py                 # Bot initialization and event handlers
├── scheduler.py            # Scheduling logic for daily messages
├── message_parser.py      # Parse and extract commitments from messages
├── database.py            # SQLite database storage layer
├── sheets_manager.py      # Google Sheets integration module
├── pyproject.toml         # Project dependencies and metadata (for uv)
├── uv.lock                # Lock file for reproducible builds (created by uv)
├── requirements.txt       # Python dependencies (backup, pyproject.toml is primary)
├── Procfile               # Heroku process file (for deployment)
├── runtime.txt            # Python version specification (for Heroku)
├── .env                   # Environment variables (create this yourself, not in repo)
├── .venv/                 # Virtual environment (created automatically by uv)
├── standup_bot.db         # SQLite database (created automatically)
├── bot.log                # Bot log file (created automatically)
├── credentials.json       # Google service account credentials (not in repo, see setup)
├── GOOGLE_SHEETS_SETUP.md # Google Sheets setup instructions
└── README.md              # This file
```

## Configuration

### Environment Variables

- `DISCORD_BOT_TOKEN` (required): Your Discord bot token
- `DISCORD_CHANNEL_ID` (optional): Channel ID for standups (can be set via command)
- `STANDUP_HOUR` (optional): Hour for standup (0-23, default: 17 for 5:00 PM)
- `STANDUP_MINUTE` (optional): Minute for standup (0-59, default: 0)
- `TIMEZONE` (optional): Timezone for scheduling (default: UTC). Use IANA timezone names like 'America/New_York', 'Europe/London', etc.
- `USE_OPENAI` (optional): Enable OpenAI parsing (true/false, default: false)
- `OPENAI_API_KEY` (optional): OpenAI API key if using OpenAI parsing
- `SPREADSHEET_ID` (optional): Google Spreadsheet ID for task management (see [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md))
- `GOOGLE_CREDENTIALS_PATH` (optional): Path to Google service account credentials JSON file (default: `credentials.json`)
- `GOOGLE_SHEETS_HEADER_ROW` (optional): Row number where headers are located (default: 6)

### Message Parsing

The bot has two modes for parsing messages:

1. **Simple Pattern Matching** (default): Uses regex patterns to extract commitments
   - Looks for keywords like "today", "tomorrow", "will", "plan to"
   - Works well for structured responses

2. **OpenAI Parsing** (optional): Uses GPT-3.5-turbo for intelligent parsing
   - Better at understanding natural language
   - Requires OpenAI API key
   - Falls back to simple parsing if unavailable

## Database Schema

The bot uses SQLite with the following tables:

- `standup_responses`: Stores user responses with parsed commitments
- `follow_ups`: Tracks follow-up messages sent
- `bot_config`: Stores bot configuration settings

## Troubleshooting

### Bot doesn't respond

- Check that the bot token is correct in `.env`
- Verify the bot has the necessary permissions in the server
- Check the console/logs for error messages

### Messages not being sent

- Verify the channel ID is correct
- Ensure the bot has "Send Messages" permission in that channel
- Check that the bot is online in Discord

### Commands not working

- Wait a few minutes after starting the bot for commands to sync
- Ensure the bot has "Use Slash Commands" permission
- Try restarting the bot

### Parsing not working correctly

- Try using more structured responses (e.g., "Today: ... Tomorrow: ...")
- If using OpenAI, verify your API key is valid
- Check the bot logs for parsing errors

## Logging

The bot logs to both:
- Console output
- `bot.log` file (in the project root)

Log levels include INFO, WARNING, and ERROR messages.

## Code Quality

The codebase follows best practices:
- **Type hints**: Used throughout for better code clarity
- **Comprehensive logging**: All operations are logged for debugging
- **Error handling**: Try-except blocks with proper error messages
- **Documentation**: Inline comments and docstrings for all functions
- **Modular design**: Separated concerns (database, scheduler, parser, sheets manager)
- **Environment-based configuration**: All sensitive data via environment variables

## Production Readiness

### Before Deploying to Production

1. **Security**:
   - Never commit `.env` or `credentials.json` to version control
   - Use environment variables for all sensitive data
   - Review and set appropriate Discord bot permissions
   - Rotate credentials regularly

2. **Database**:
   - Consider migrating from SQLite to PostgreSQL for production
   - Set up database backups
   - Monitor database size and performance

3. **Monitoring**:
   - Set up error tracking (e.g., Sentry)
   - Monitor API rate limits
   - Track bot uptime and response times
   - Set up alerts for critical errors

4. **Testing**:
   - Test all slash commands before deployment
   - Verify scheduled messages work correctly
   - Test Google Sheets integration (if used)
   - Verify timezone handling

5. **Documentation**:
   - Document your specific configuration
   - Keep team members informed of bot capabilities
   - Maintain a changelog for updates

## License

This project is open source and available for use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the bot logs for error messages
3. Check the [Google Sheets Setup Guide](GOOGLE_SHEETS_SETUP.md) if using task management
4. Check the [Heroku Credentials Setup Guide](HEROKU_CREDENTIALS_SETUP.md) if deploying to Heroku
5. Open an issue on the project repository

## Google Sheets Integration

The bot includes comprehensive task management features that integrate with Google Sheets. This allows you to:

- **Track Tasks**: Create, view, and complete tasks directly from Discord
- **Assign Work**: Assign tasks to team members using usernames or Discord mentions
- **Monitor Progress**: View task lists, filter by assignee, and track completion
- **Record Outcomes**: Document what was actually achieved vs. what was planned
- **Persistent Storage**: All data is stored in Google Sheets (accessible outside Discord)
- **Historical Tracking**: Keep a complete record of all tasks and outcomes

**Key Benefits:**

- **No Database Setup**: Uses Google Sheets instead of a separate database
- **Easy Access**: View and edit tasks directly in Google Sheets
- **Team Collaboration**: Multiple team members can view tasks simultaneously
- **Export & Analysis**: Export data from Google Sheets for reporting and analysis
- **Automatic Formatting**: Description columns are automatically merged for readability

**Setup:**

See [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) for detailed setup instructions. The setup process includes:
1. Creating a Google Cloud project
2. Enabling Google Sheets and Drive APIs
3. Creating a service account
4. Downloading credentials
5. Setting up your spreadsheet
6. Configuring the bot

**For Heroku Deployment:**

See [HEROKU_CREDENTIALS_SETUP.md](HEROKU_CREDENTIALS_SETUP.md) for instructions on securely storing Google credentials on Heroku.