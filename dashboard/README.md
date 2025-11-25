# Ralph Wiggum Dashboard

Real-time web dashboard for monitoring autonomous coding agents managed by the Ralph Wiggum loop.

## Architecture

```
Notion Database (Source of Truth)
        ↕
rwLOOP instances (One per ticket)
        ↕
Dashboard Backend (FastAPI)
        ↕
Dashboard Frontend (React)
```

## Features

- **Kanban Board**: Visual representation of tickets by status
- **Live Stats**: Total tickets, active loops, in-progress, waiting
- **Ticket Cards**: Shows session ID, turn count, last updated
- **Quick Links**: Jump to Notion pages directly
- **Auto-refresh**: Polls every 3 seconds for updates

## Setup

### Backend

```bash
cd dashboard/backend

# Install dependencies
pip install fastapi uvicorn notion-client

# Run server (from project root to access .env)
cd ../..
python dashboard/backend/app.py
# Server runs on http://localhost:8000
```

### Frontend

```bash
cd dashboard/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# Opens at http://localhost:5173
```

## API Endpoints

- `GET /api/tickets` - List all tickets
- `POST /api/tickets/{id}/status?status=<status>` - Update ticket status
- `GET /api/stats` - Dashboard statistics
- `WS /ws/logs` - WebSocket for real-time logs (future)

## Status Flow

1. **Planning** - Claude exploring codebase
2. **Agent at Work** - Claude actively working
3. **Requesting User Input** - Waiting for human response
4. **Done** - Completed (human-verified)

## Future Enhancements

- [ ] Real-time log streaming via WebSocket
- [ ] Token usage tracking
- [ ] File change diff viewer
- [ ] Tool call timeline
- [ ] Drag-drop status changes
- [ ] Multiple rwLOOP instance management
- [ ] Notion webhook integration (real-time instead of polling)

## Environment Variables

Ensure these are set (loaded from project root `.env`):

```
NOTION_TOKEN=secret_...
NOTION_TICKET_DB=<database-id>
CLAUDE_TICKET_DIR=./tickets
```

## Using Google AI Studio to Generate UI

You can use Google AI Studio (Gemini) to generate additional UI components:

```
Prompt: "Create a React component for a ticket timeline showing:
- Status changes over time
- Tool calls (Read, Write, Edit, Bash)
- Files modified
- Turn transitions
Use Tailwind CSS for styling."
```

Then paste the generated code into new components.
