# Babysitter POC
I can now vibecode on my claude code instance from my phone through notion! :D \
Project is aiming for Autonomous Claude AI loop with human-in-the-loop intervention via Notion.

## How It Works

1. Claude runs continuously in a loop
2. When Claude needs human input, it calls the `ask_human` MCP tool to create/update a Notion ticket
3. Claude suspends and waits
4. Human responds in Notion and checks the "Ready" checkbox
5. `resume_poll.py` detects the response and resumes Claude with the answer
6. **Multi-turn conversations**: Claude can ask follow-up questions in the same ticket, building conversation history

## Features

- **Multi-turn conversations**: Single ticket supports multiple back-and-forth exchanges
- **Status tracking**: Automatic status updates ("Requesting User Input" → "Agent at Work" → "Done"/"Error")
- **Conversation history**: Previous turns collapsed into toggles for easy reference
- **Error handling**: Failed resumes automatically marked with "Error" status
- **Human control**: Set status to "Done" to archive completed tickets

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
     - `Status` (status) - with options: "Requesting User Input", "Agent at Work", "Done", "Error"
     - `Ticket` (rich_text)
     - `Session ID` (rich_text)
     - `Turn Count` (number)
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
- `scripts/notion_mcp_server.py` - MCP server providing the `ask_human` tool for creating/updating Notion tickets
- `scripts/resume_poll.py` - Polls Notion for human responses and resumes Claude conversations
- `first_prompt.txt` - Initial prompt for Claude
- `mcp-config.json` - MCP server configuration
- `pyproject.toml` - Python dependencies managed by uv

## Status Lifecycle

Tickets automatically transition through these statuses:

1. **Requesting User Input** - Claude asked a question, awaiting human response
   - Set automatically by MCP server when `ask_human` is called
   - Human should respond and check "Ready" checkbox

2. **Agent at Work** - Claude is actively processing
   - Set automatically by `resume_poll.py` before resuming Claude
   - Indicates the agent is working on the task

3. **Done** - Task complete (human-controlled)
   - Set manually by human when conversation should end
   - Automatically archives ticket on next poll cycle

4. **Error** - Resume failed
   - Set automatically if `claude --resume` fails
   - Requires human intervention to fix or retry

## Notes

- The loop uses `--dangerously-skip-permissions` flag for automation
- Tickets are stored in `./tickets/` directory
- Multi-turn conversations reuse the same ticket file (.page) until marked Done
- Previous conversation turns are preserved in collapsible toggle blocks
