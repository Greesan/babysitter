# Quick Start Guide - Agent SDK

## 🚀 Start Using the Agent Right Now

### Option 1: Via Webhook Server (Recommended)

```bash
# 1. Start the server
uv run uvicorn src.webhook_server:app --reload

# 2. In another terminal, trigger agent for a ticket
curl -X POST http://localhost:8000/webhook/notion \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "your-notion-page-id",
    "database_id": "your-notion-db-id",
    "event_type": "page_created"
  }'

# You'll get back: {"job_id": "job-abc123", "status": "queued"}
```

### Option 2: Direct Python Execution

```python
# Create a file: run_agent.py
import asyncio
import os
from dotenv import load_dotenv
from src.agent import run_agent_for_ticket, AgentConfig

load_dotenv()

async def main():
    config = AgentConfig(
        notion_token=os.getenv("NOTION_TOKEN"),
        notion_db_id=os.getenv("NOTION_DB_ID"),
        model="sonnet",
        max_turns=50
    )

    print("🤖 Starting agent...")
    result = await run_agent_for_ticket(config)

    if result:
        print(f"✅ Done! Status: {result['status']}")
        print(f"   Ticket: {result['ticket_name']}")
    else:
        print("ℹ️  No pending tickets found")

if __name__ == "__main__":
    asyncio.run(main())
```

Then run:
```bash
uv run python run_agent.py
```

---

## 📋 Environment Setup

Create `.env` file:
```bash
NOTION_TOKEN=secret_your_notion_integration_token
NOTION_DB_ID=your_database_id_here
```

---

## 🧪 Run Tests

```bash
# All tests (52 total)
uv run pytest tests/ -v

# Just agent tests
uv run pytest tests/test_agent.py -v

# Just hooks
uv run pytest tests/test_hooks_*.py -v

# Just webhook server
uv run pytest tests/test_webhook_server.py -v
```

---

## 🔍 What Happens When Agent Runs

1. **Claims pending ticket** from Notion database
2. **Initializes Claude SDK** with hooks registered
3. **Calls session_start_hook** → Updates status to "Agent Working"
4. **Executes** `await client.query(prompt, session_id)`
5. **During execution**:
   - PostToolUse hook fires after each tool call
   - UserPromptSubmit hook fires when agent needs input
   - All conversation saved to Notion
6. **On completion** → Status updated to "Completed"

---

## 🔌 WebSocket (for UI Integration)

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// Receive messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Message from server:', data);
};

// Send user response when agent asks
ws.send(JSON.stringify({
    type: 'user_response',
    session_id: 'session-123',
    response: 'Yes, please proceed'
}));
```

---

## 📊 Current Status

✅ **52/52 tests passing** (100%)
✅ **All hooks working** (UserPromptSubmit, PostToolUse, SessionStart)
✅ **Agent actually executes** (client.query implemented)
✅ **Webhook server ready** (FastAPI + WebSocket)
✅ **Conversation persistence** (Notion database)

---

## 🎯 Try It Now

1. **Create a test ticket in Notion**
   - Add a "Pending" ticket to your database
   - Give it a clear task name

2. **Run the agent**
   ```bash
   uv run python -c "
   import asyncio
   from src.agent import run_agent_for_ticket, AgentConfig
   import os
   from dotenv import load_dotenv
   load_dotenv()

   async def test():
       config = AgentConfig(
           notion_token=os.getenv('NOTION_TOKEN'),
           notion_db_id=os.getenv('NOTION_DB_ID')
       )
       result = await run_agent_for_ticket(config)
       print(result)

   asyncio.run(test())
   "
   ```

3. **Check Notion** - Your ticket status should update to "Agent Working" → "Completed"

---

## 💡 Tips

- **Session IDs**: Each ticket gets a unique session ID for conversation continuity
- **Turn Count**: Tracks conversation progress, incremented by hooks
- **Status Flow**: Pending → Agent Planning → Agent Working → [Requesting User Input] → Completed
- **Error Handling**: Failures update status to "Error" with error message

---

## 🆘 Troubleshooting

**No tickets found?**
- Check Notion database has tickets with Status = "Pending"
- Verify NOTION_DB_ID is correct
- Ensure Notion integration has access to database

**Agent not running?**
- Check NOTION_TOKEN is valid
- Verify `claude` CLI is authenticated
- Check you're not setting ANTHROPIC_API_KEY (uses Pro subscription)

**Tests failing?**
- Run `uv sync` to ensure dependencies are installed
- Check Python version is 3.12+
- Verify pytest-asyncio is installed

---

That's it! The agent is ready to run. 🎉
