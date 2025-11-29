# Notion Database Setup - REQUIRED STEP

## Current Issue

Your integration token cannot access the database. You need to **share the database with your integration** in Notion.

Error: `Could not find database with ID: $NOTION_DB_ID`

---

## How to Fix This

### Step 1: Open Your Notion Database

Go to: https://notion.so/$NOTION_DB_ID

(This is the database ID found in your .env file)

### Step 2: Share Database with Integration

1. **Click the "..." menu** (three dots) in the top-right corner of the database page
2. **Click "Add connections"** or "Connect to"
3. **Find your integration** in the list
   - Look for the integration associated with token: `$NOTIONTOKEN`
4. **Grant access** by clicking on it

### Step 3: Verify Access

After sharing, run this command to verify:

```bash
uv run python check_pending_tickets.py
```

You should now see either:
- "Found a pending ticket!" (if you have one)
- "No pending tickets found!" (but without the permission error)

---

## Step 4: Create a Test Ticket

Once access is granted, create a test ticket in Notion:

1. **Open your Notion database**
2. **Click "+ New"** to create a new page
3. **Fill in the fields**:
   ```
   Name/Title: Test Agent Task
   Status: Pending
   Description: List all Python files in the src/ directory
   ```
4. **Save the page**

---

## Step 5: Test the Webhook

Start the webhook server:
```bash
uv run uvicorn src.webhook_server:app --reload
```

In another terminal, trigger the webhook:
```bash
curl -X POST http://localhost:8000/webhook/notion \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "test-page-id",
    "database_id": "$NOTION_DB_ID",
    "event_type": "page_created"
  }'
```

Expected response:
```json
{
  "job_id": "job-abc12345",
  "status": "queued",
  "ticket_id": "test-page-id"
}
```

---

## Step 6: Verify Agent Execution

Check the webhook server logs - you should see:
```
Processing ticket: Test Agent Task
  Ticket ID: <actual-notion-page-id>
  Session ID: <generated-session-id>
Starting agent execution for session: <session-id>
Agent execution completed for ticket: <ticket-id>
```

Check your Notion database - the ticket should now show:
- **Status**: "Completed" (or "Error" if something failed)
- **Session ID**: Filled in with a UUID
- **Conversation JSON**: Contains the conversation history

---

## Troubleshooting

### "Could not find database"
- Make sure you shared the database with your integration (Step 2)
- Verify the NOTION_DB_ID in .env matches the database URL

### "No pending tickets found"
- Create a ticket with Status = "Pending" (Step 4)
- Check that the Status property exists and uses the exact value "Pending"

### "Integration not found"
- Go to https://www.notion.so/my-integrations
- Find or create an integration
- Copy the token to NOTION_TOKEN in .env
- Make sure the integration has "Read content", "Update content", and "Insert content" permissions

---

## Database Schema Requirements

Your Notion database should have these properties:

| Property Name | Type | Required | Notes |
|--------------|------|----------|-------|
| Name | Title | Yes | Ticket title |
| Status | Status | Yes | Must have "Pending", "Agent Working", "Completed", "Error" |
| Session ID | Text | Yes | Auto-filled by agent |
| Conversation JSON | Text | Yes | Stores conversation history |
| Description | Text | No | Task description |
| Turn Count | Number | No | Tracks conversation progress |


## What Happens Next

Once you complete these steps:

1. ✅ Integration has access to database
2. ✅ Test ticket created with Status = "Pending"
3. ✅ Webhook triggered
4. ✅ Agent claims the pending ticket
5. ✅ Agent executes the task using Claude SDK
6. ✅ Conversation saved to Notion
7. ✅ Status updated to "Completed"

You'll have a fully working webhook → agent → Notion workflow!
