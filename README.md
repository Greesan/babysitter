# Babysitter POC
COOL STUFF I CAN NOW VIBECODE FROM ON MY CLAUDE CODE INSTANCE FROM MY PHONE THROUGH NOTION :D
Autonomous Claude AI loop with human-in-the-loop intervention via Notion.

## How It Works

1. Claude runs continuously in a loop
2. When Claude needs human input, it calls `notion_mcp.py` to create a Notion ticket
3. Claude suspends and waits
4. Human responds in Notion
5. `resume_poll.py` detects the response and resumes Claude with the answer

## Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync --no-install-project
   ```

3. **Set up Notion**:
   - Create a Notion integration at https://www.notion.so/my-integrations
   - Create a database with these properties:
     - `Name` (title)
     - `Status` (select with at least "Pending" option)
     - `Ticket` (rich_text)
   - Share the database with your integration
   - Copy the integration token and database ID

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Notion credentials
   ```

5. **Customize the initial prompt** (optional):
   Edit `first_prompt.txt` to change what Claude does initially

## Running

```bash
bash rwLOOP.sh
```

The script will automatically load environment variables from `.env` on startup.

## Files

- `rwLOOP.sh` - Main loop that runs Claude continuously
- `scripts/notion_mcp.py` - MCP tool for creating Notion tickets
- `scripts/resume_poll.py` - Polls Notion for human responses
- `first_prompt.txt` - Initial prompt for Claude
- `pyproject.toml` - Python dependencies managed by uv

## Notes

- The loop uses `--dangerously-skip-permissions` flag for automation
- Tickets are stored in `./tickets/` directory
- Conversation state is saved in `./claude_conversations/session.json`
