# Notion Webhook Integration Setup

## 🚨 IMPORTANT: How the Webhook Works

The webhook server **does NOT create tickets**. Here's the actual flow:

```
┌─────────────────────────────────────────────────────────────┐
│  CURRENT IMPLEMENTATION                                     │
├─────────────────────────────────────────────────────────────┤
│  1. Notion Webhook → POST /webhook/notion                   │
│  2. Webhook receives: page_id, database_id, event_type      │
│  3. Agent runner calls: claim_pending_ticket()              │
│  4. Looks for EXISTING tickets with Status = "Pending"      │
│  5. If found → runs agent on that ticket                    │
│  6. If not found → returns None                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Point**: The webhook **triggers** agent execution but doesn't specify which ticket to process. The agent **claims the oldest pending ticket** from the database.

---

## 📋 Current Setup Requirements

### Option 1: Manual Ticket Creation (Simplest)

**This is what you need to do NOW:**

1. **Go to your Notion database**
2. **Create a new page/ticket manually**:
   - Set Status to "Pending"
   - Add a task name (e.g., "Test task: List files in current directory")
3. **The webhook will trigger the agent to claim and process it**

**Example Notion Ticket:**
```
Title: Test Agent Task
Status: Pending
Description: List all Python files in the project
```

### Option 2: Webhook Creates Specific Ticket (Needs Implementation)

If you want the webhook to process a **specific ticket** (the one that triggered the webhook), we need to modify the code:

**Current Code** (src/webhook_server.py):
```python
# Receives page_id but doesn't use it
result = await run_agent_for_ticket(config)  # Claims ANY pending ticket
```

**What it SHOULD do** (if you want ticket-specific processing):
```python
# Pass the specific ticket_id to process
result = await run_agent_for_specific_ticket(config, ticket_id=page_id)
```

---

## 🔧 Two Approaches to Fix This

### Approach A: Keep Current Design (Recommended for Now)

**How it works:**
- Webhook is just a **trigger** (not ticket-specific)
- Agent claims the **oldest pending ticket** from database
- Multiple webhooks can trigger processing of different tickets

**Setup Steps:**
1. ✅ Webhook server running: `uv run uvicorn src.webhook_server:app --reload`
2. ✅ Create a Pending ticket in Notion manually
3. ✅ Trigger webhook (or wait for Notion to trigger it)
4. ✅ Agent claims and processes the pending ticket

**Pros:**
- ✅ Simple queue system
- ✅ Works with any pending ticket
- ✅ No code changes needed

**Cons:**
- ❌ Webhook doesn't process the specific ticket that triggered it
- ❌ Can't have webhook-specific logic per ticket

### Approach B: Modify to Process Specific Ticket

**What needs to change:**

1. Create new function `run_agent_for_specific_ticket()`:
```python
async def run_agent_for_specific_ticket(
    config: AgentConfig,
    ticket_id: str
) -> Optional[Dict[str, Any]]:
    """Process a specific ticket by ID (not just any pending ticket)"""
    # Don't claim - just process the given ticket_id
    # ... rest of logic
```

2. Update webhook to use specific ticket:
```python
result = await run_agent_for_specific_ticket(config, ticket_id=page_id)
```

**Pros:**
- ✅ Webhook processes exactly the ticket that triggered it
- ✅ Better for event-driven architecture

**Cons:**
- ❌ Requires code changes
- ❌ Need to update ticket status logic (no "claiming")

---

## 🎯 Immediate Solution (What You Should Do Now)

**Since no ticket was created, here's what to do:**

### Step 1: Create a Test Ticket in Notion

Go to your Notion database and create:

```
┌─────────────────────────────────────────┐
│ Title: Test Agent Execution             │
│ Status: Pending                         │
│ Session ID: (leave blank - auto-filled) │
│ Description:                            │
│   Please list all Python files in the  │
│   src/ directory and count how many    │
│   there are.                            │
└─────────────────────────────────────────┘
```

### Step 2: Start the Webhook Server

```bash
uv run uvicorn src.webhook_server:app --reload
```

### Step 3: Trigger the Webhook

```bash
curl -X POST http://localhost:8000/webhook/notion \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "any-id-here",
    "database_id": "'"$NOTION_DB_ID"'",
    "event_type": "page_created"
  }'
```

**Expected Result:**
```json
{
  "job_id": "job-abc12345",
  "status": "queued",
  "ticket_id": "any-id-here"
}
```

### Step 4: Check Server Logs

You should see:
```
Processing ticket: Test Agent Execution
  Ticket ID: <actual-notion-page-id>
  Session ID: <generated-session-id>
Starting agent execution for session: <session-id>
Agent execution completed for ticket: <ticket-id>
```

### Step 5: Check Notion

Your ticket should now show:
- Status: "Completed" (or "Error" if something failed)
- Session ID: Filled in
- Conversation JSON: Has the conversation history

---

## 🌐 Setting Up Real Notion Webhooks

Notion **doesn't have native webhooks yet** (as of Jan 2025). You have a few options:

### Option 1: Polling (Current Ralph Wiggum Approach)
- Keep the old `rwLOOP.sh` to poll for new tickets
- When found, call the webhook endpoint
- This is what you had before

### Option 2: Zapier/Make.com/n8n
- Use automation tool to watch Notion database
- When new page created → POST to your webhook
- Easiest for non-technical setup

### Option 3: Notion API Polling Service
- Create a simple Python service that polls Notion every 10s
- When new Pending ticket found → POST to webhook
- This is cleaner than bash polling

### Option 4: Database Triggers (Future)
- Wait for Notion to add native webhook support
- Currently in beta/private alpha

---

## 📝 Summary of Current State

### What Works:
✅ Webhook server receives POST requests
✅ Agent claims and processes pending tickets
✅ All hooks fire during execution
✅ Conversation saved to Notion
✅ Status updates work

### What Doesn't Work (Yet):
❌ Webhook doesn't create tickets
❌ Webhook doesn't process the specific ticket that triggered it
❌ Notion doesn't have native webhooks to trigger it

### What You Need to Do:
1. **Manually create a Pending ticket in Notion**
2. **Trigger the webhook** (via curl or external service)
3. **Agent will claim and process the ticket**

---

## 🛠️ Want Me to Implement Ticket-Specific Processing?

If you want the webhook to process **exactly the ticket that triggered it** (not just any pending ticket), I can:

1. Create `run_agent_for_specific_ticket(config, ticket_id)`
2. Update webhook to pass the specific ticket_id
3. Skip the "claiming" logic for webhook-triggered tickets
4. Add tests for this new flow

Let me know if you want this! It's a small change (about 10 minutes).

---

## 🔍 Debug: Check What Happened

Run this to see if agent tried to claim a ticket:

```bash
# Check if there are any Pending tickets
uv run python -c "
from notion_client import Client
import os
from dotenv import load_dotenv
load_dotenv()

client = Client(auth=os.getenv('NOTION_TOKEN'))
db = client.databases.query(
    database_id=os.getenv('NOTION_DB_ID'),
    filter={'property': 'Status', 'status': {'equals': 'Pending'}}
)

print(f'Pending tickets: {len(db[\"results\"])}')
for page in db['results']:
    title = page['properties']['Name']['title'][0]['plain_text']
    print(f'  - {title}')
"
```

If it says "Pending tickets: 0", that's why the webhook didn't process anything!
