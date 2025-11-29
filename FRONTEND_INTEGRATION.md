# Frontend Integration - Complete! 🎉

The Agent SDK now has a fully integrated web frontend with real-time WebSocket communication.

## Features

✅ **Real-time WebSocket connection** - See agent activity live
✅ **Agent questions displayed** - Agent asks questions through the UI
✅ **User responses via WebSocket** - Answer agent questions instantly
✅ **Tool call visualization** - See tool executions with collapsible output
✅ **Session tracking** - Shows current session ID
✅ **Connection status** - Visual indicator of WebSocket connection
✅ **Terminal-style UI** - Beautiful Matrix/green terminal theme

---

## Quick Start

### 1. Start the Webhook Server

```bash
uv run uvicorn src.webhook_server:app --reload
```

The server will start on `http://localhost:8000`

### 2. Open the Frontend

Open your browser and go to:
```
http://localhost:8000
```

You should see the terminal-style interface with a green "Connected" status indicator.

### 3. Create a Pending Ticket in Notion

Go to your Notion "Tickets" database and create a ticket:
- **Name**: "Test task: List all Python files in src/"
- **Status**: "Pending"

### 4. Trigger the Agent

Option A: Via API (simulating Notion webhook):
```bash
curl -X POST http://localhost:8000/webhook/notion \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "test-page",
    "database_id": "2abab0827928802ba679fa8a3db75645",
    "event_type": "page_created"
  }'
```

Option B: Via frontend (click the + button)

### 5. Watch Real-Time Updates

You'll see in the frontend:
1. **"Agent started processing ticket..."** - Initial message
2. **Tool calls** - Collapsible boxes showing tool execution
3. **Agent questions** - If the agent needs input
4. **Your responses** - Send via the text input
5. **"Task completed"** - When done

---

## How It Works

### WebSocket Message Flow

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND → BACKEND                                         │
├─────────────────────────────────────────────────────────────┤
│  1. Browser connects to ws://localhost:8000/ws              │
│  2. User types response and hits "Send"                     │
│  3. Frontend sends:                                         │
│     {                                                       │
│       "type": "user_response",                             │
│       "session_id": "session-123",                         │
│       "response": "Yes, please proceed"                    │
│     }                                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  BACKEND → FRONTEND                                         │
├─────────────────────────────────────────────────────────────┤
│  1. Agent starts → broadcast "agent_started"                │
│  2. Agent uses tool → broadcast "tool_call"                 │
│  3. Agent asks question → broadcast "agent_question"        │
│  4. Agent completes → broadcast "agent_complete"            │
│  5. Error occurs → broadcast "agent_error"                  │
└─────────────────────────────────────────────────────────────┘
```

### Hook Integration

**UserPromptSubmit Hook** (`src/hooks/user_prompt.py`):
- Broadcasts agent question via WebSocket
- Waits for user response from WebSocket (or Notion fallback)
- Returns response to agent

**PostToolUse Hook** (`src/hooks/post_tool_use.py`):
- Broadcasts tool execution via WebSocket
- Shows tool name and truncated output

**Agent.py**:
- Broadcasts "agent_started" when claiming ticket
- Broadcasts "agent_complete" or "agent_error" when done

---

## Message Types

### Frontend Sends to Backend

```javascript
// User response to agent question
{
  type: 'user_response',
  session_id: 'session-abc123',
  response: 'Yes, please continue'
}

// Heartbeat ping
{
  type: 'ping'
}
```

### Backend Sends to Frontend

```javascript
// Agent started processing
{
  type: 'agent_started',
  ticket_id: 'ticket-123',
  ticket_name: 'My task',
  session_id: 'session-abc',
  timestamp: '2025-01-28T10:00:00Z'
}

// Agent asking a question
{
  type: 'agent_question',
  content: 'Should I proceed with this change?',
  session_id: 'session-abc',
  ticket_id: 'ticket-123',
  timestamp: '2025-01-28T10:01:00Z'
}

// Tool execution
{
  type: 'tool_call',
  tool_name: 'bash',
  title: 'Tool: bash',
  content: '$ ls\nfile1.py\nfile2.py',
  output_type: 'terminal',
  session_id: 'session-abc',
  timestamp: '2025-01-28T10:02:00Z'
}

// Agent completed
{
  type: 'agent_complete',
  job_id: 'job-xyz',
  ticket_id: 'ticket-123',
  status: 'completed'
}

// Agent error
{
  type: 'agent_error',
  job_id: 'job-xyz',
  error: 'Something went wrong'
}

// Acknowledgment of user response
{
  type: 'ack',
  session_id: 'session-abc',
  status: 'received'
}
```

---

## UI Components

### Connection Status Indicator
- **Green pulsing dot**: Connected
- **Yellow pulsing dot**: Connecting...
- **Red dot**: Disconnected/Error

### Session ID Display
Shows current active session in top-right of input box

### Message Blocks

1. **Agent Questions** (Green border, left-aligned)
   - Agent asking for user input
   - Clear "AGENT" label

2. **User Responses** (Green background, right-aligned)
   - Shows with "$" prompt prefix
   - Clear "YOU" label

3. **Tool Calls** (Collapsible, full-width)
   - Click to expand/collapse
   - Shows tool output in monospace font
   - Truncated if too long

---

## Notion Integration

### Dual Storage Pattern

Both **Notion** and **Frontend** see the same data:

```
User asks question via Notion
    ↓
Agent processes
    ↓
Agent asks clarifying question
    ↓
Question saved to Notion → ALSO → Broadcast via WebSocket
    ↓                                     ↓
User can answer in Notion         User can answer in Frontend
    ↓                                     ↓
Response saved to Notion ← OR ← Response via WebSocket
    ↓
Agent continues
```

### Fallback Mechanism

The `wait_for_user_response()` function checks **both**:
1. **First**: WebSocket `pending_responses` dict (instant)
2. **Fallback**: Notion "User Response" property (1s polling)

This means you can answer from either Notion or the frontend!

---

## File Structure

```
babysitterPOC/
├── frontend/
│   └── index.html          # Main frontend UI
├── src/
│   ├── agent.py            # Broadcasts agent_started
│   ├── webhook_server.py   # WebSocket server + routes
│   └── hooks/
│       ├── user_prompt.py  # Broadcasts agent_question
│       └── post_tool_use.py # Broadcasts tool_call
```

---

## Customization

### Change WebSocket URL

Edit `frontend/index.html`:
```javascript
const WS_URL = 'ws://your-server:8000/ws';
```

### Change Theme Colors

The UI uses Tailwind CSS with emerald/green theme.
Edit the `<style>` section in `index.html` to change colors.

### Add Custom Message Types

1. Add handler in `handleWebSocketMessage()` (frontend)
2. Add broadcast in appropriate hook (backend)

---

## Troubleshooting

### "Connecting..." never changes to "Connected"
- Check that webhook server is running: `uv run uvicorn src.webhook_server:app --reload`
- Check browser console for WebSocket errors
- Verify no firewall blocking port 8000

### Agent questions not appearing
- Check server logs for errors
- Verify hooks are registered in `agent.py`
- Check WebSocket connection status

### User responses not reaching agent
- Check `pending_responses` dict is being populated
- Verify `session_id` matches between frontend and backend
- Check server logs for WebSocket message receipt

### Frontend not loading
- Verify `frontend/index.html` exists
- Check server logs for file path errors
- Try accessing `http://localhost:8000/health` to verify server is up

---

## Next Steps

### Production Deployment

For production, you'll want to:

1. **Use Redis** for `pending_responses` instead of in-memory dict
2. **Add authentication** to WebSocket connections
3. **Implement proper task queue** (Celery, RQ) instead of `asyncio.create_task`
4. **Add rate limiting** to prevent abuse
5. **Use HTTPS/WSS** for encrypted connections
6. **Add logging** and monitoring
7. **Implement reconnection** logic in frontend

### Features to Add

- **Multi-user support** - Multiple users on different tickets
- **Ticket creation from UI** - Create tickets without Notion
- **Conversation history** - Load past conversations
- **File uploads** - Attach files to questions
- **Markdown rendering** - Rich text in responses
- **Code syntax highlighting** - Better code display
- **Typing indicators** - Show when agent is "thinking"

---

## Summary

You now have a **fully integrated frontend** that:

✅ Connects to Agent SDK via WebSocket
✅ Shows real-time agent activity
✅ Handles user input/output
✅ Works alongside Notion (dual interface)
✅ Looks beautiful with terminal theme

The integration is **complete** and **ready to use**!

Start the server, open the browser, create a ticket, and watch the agent work in real-time. 🚀
