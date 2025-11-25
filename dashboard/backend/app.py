#!/usr/bin/env python3
"""
FastAPI backend for Ralph Wiggum Dashboard
Provides real-time monitoring of tickets and rwLOOP instances
"""
import os
import json
import asyncio
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Environment
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_TICKET_DB = os.environ.get("NOTION_TICKET_DB")
TICKET_DIR = os.environ.get("CLAUDE_TICKET_DIR", "./tickets")

app = FastAPI(title="Ralph Wiggum Dashboard API")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class TicketStatus(BaseModel):
    id: str
    page_id: str
    name: str
    status: str
    session_id: str
    turn_count: int
    last_updated: datetime
    is_active: bool  # Has local .page file

class LogEntry(BaseModel):
    timestamp: datetime
    level: str  # INFO, SUCCESS, WARN, ERROR
    ticket_id: Optional[str]
    message: str

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# API Endpoints

@app.get("/")
def root():
    return {"status": "ok", "service": "Ralph Wiggum Dashboard"}

@app.get("/api/tickets", response_model=List[TicketStatus])
async def get_tickets():
    """Get all tickets from Notion database"""
    notion = Client(auth=NOTION_TOKEN)

    # Get data source
    database = notion.databases.retrieve(database_id=NOTION_TICKET_DB)
    data_sources = database.get("data_sources", [])

    if not data_sources:
        return []

    data_source_id = data_sources[0]["id"]

    # Query all tickets
    response = notion.data_sources.query(
        data_source_id=data_source_id,
        sorts=[
            {"property": "Turn Count", "direction": "descending"}
        ]
    )

    tickets = []
    local_tickets = set()

    # Get local active tickets
    if os.path.exists(TICKET_DIR):
        local_tickets = {f.replace(".page", "") for f in os.listdir(TICKET_DIR) if f.endswith(".page")}

    for page in response.get("results", []):
        props = page["properties"]

        # Extract properties
        ticket_id = props.get("Ticket", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
        status = props.get("Status", {}).get("status", {}).get("name", "")
        session_id = props.get("Session ID", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")
        turn_count = props.get("Turn Count", {}).get("number", 0)
        name = props.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Unknown")

        tickets.append(TicketStatus(
            id=ticket_id,
            page_id=page["id"],
            name=name,
            status=status,
            session_id=session_id,
            turn_count=turn_count or 0,
            last_updated=datetime.fromisoformat(page["last_edited_time"].replace("Z", "+00:00")),
            is_active=ticket_id in local_tickets
        ))

    return tickets

@app.post("/api/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, status: str):
    """Update ticket status (e.g., from dashboard drag-drop)"""
    notion = Client(auth=NOTION_TOKEN)

    # Find page_id from local files
    page_id_file = f"{TICKET_DIR}/{ticket_id}.page"
    if not os.path.exists(page_id_file):
        return {"error": "Ticket not found locally"}

    with open(page_id_file, "r") as f:
        page_id = f.read().strip()

    # Update Notion
    notion.pages.update(
        page_id=page_id,
        properties={"Status": {"status": {"name": status}}}
    )

    # Broadcast update to WebSocket clients
    await manager.broadcast({
        "type": "status_change",
        "ticket_id": ticket_id,
        "status": status,
        "timestamp": datetime.now().isoformat()
    })

    return {"success": True, "ticket_id": ticket_id, "status": status}

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """Stream logs in real-time via WebSocket"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive (actual logs would come from rwLOOP.sh streaming)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    notion = Client(auth=NOTION_TOKEN)

    database = notion.databases.retrieve(database_id=NOTION_TICKET_DB)
    data_sources = database.get("data_sources", [])

    if not data_sources:
        return {"total": 0, "by_status": {}}

    data_source_id = data_sources[0]["id"]
    response = notion.data_sources.query(data_source_id=data_source_id)

    tickets = response.get("results", [])
    by_status = {}

    for page in tickets:
        status = page["properties"].get("Status", {}).get("status", {}).get("name", "Unknown")
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "total": len(tickets),
        "by_status": by_status,
        "active_loops": len([f for f in os.listdir(TICKET_DIR) if f.endswith(".page")]) if os.path.exists(TICKET_DIR) else 0
    }


# Helper to parse conversation data
def parse_conversation(conv_data):
    """Convert Anthropic conversation format to frontend format"""
    messages = []
    
    # Add initial system message if present (optional, maybe not needed for now)
    
    for msg in conv_data.get("messages", []):
        role = msg.get("role")
        content = msg.get("content", [])
        
        if role == "user":
            # User message
            text_content = ""
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_content += item.get("text", "")
                elif isinstance(item, str): # Handle simple string content if any
                    text_content += item
            
            if text_content:
                messages.append({
                    "role": "user_response",
                    "content": text_content,
                    "timestamp": datetime.now().strftime("%I:%M %p") # Placeholder timestamp
                })
                
        elif role == "assistant":
            # Assistant message can be text or tool use
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        messages.append({
                            "role": "agent_question",
                            "content": item.get("text", ""),
                            "timestamp": datetime.now().strftime("%I:%M %p")
                        })
                    elif item.get("type") == "tool_use":
                        messages.append({
                            "role": "tool_call",
                            "tool_name": item.get("name"),
                            "id": item.get("id"), # Keep ID to match with results
                            "status": "running", # Will be updated if result found
                            "title": f"Running {item.get('name')}",
                            "output_type": "code", # Default to code view
                            "content": f"Input: {json.dumps(item.get('input'), indent=2)}"
                        })

    # Second pass: Match tool results (which come as user messages with type tool_result)
    # This is tricky because in Anthropic API, tool_result is a user message.
    # But in our frontend, we want to show the result nested under the tool call.
    # We need to iterate again or do it in one pass with lookahead/lookbehind? 
    # Actually, let's look at the structure again.
    # The conversation file is a list of messages.
    # User: "do x"
    # Assistant: tool_use (id: 123)
    # User: tool_result (tool_use_id: 123)
    
    # We need to find the tool_result and update the corresponding tool_call in our list.
    # Since we flattened the list above, we can iterate through the original messages again to find results
    # and update the 'messages' list we just built.
    
    # Optimization: Build a map of tool_use_id -> message_index
    tool_map = {}
    for i, m in enumerate(messages):
        if m.get("role") == "tool_call" and m.get("id"):
            tool_map[m["id"]] = i
            
    # Now scan for results
    for msg in conv_data.get("messages", []):
        if msg.get("role") == "user":
            for item in msg.get("content", []):
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    tool_use_id = item.get("tool_use_id")
                    if tool_use_id in tool_map:
                        idx = tool_map[tool_use_id]
                        # Update the tool call message
                        messages[idx]["status"] = "completed"
                        
                        # Format output
                        output = item.get("content", "")
                        if isinstance(output, list): # Sometimes content is a list of text blocks
                             output = "".join([x.get("text", "") for x in output if x.get("type") == "text"])
                        
                        # If output is very long or looks like terminal output, set type
                        messages[idx]["output_type"] = "terminal" 
                        messages[idx]["content"] += f"\n\n> Output:\n{output}"

    return messages

@app.get("/api/tickets/{ticket_id}/conversation")
async def get_ticket_conversation(ticket_id: str):
    """Get conversation history for a ticket"""
    
    # 1. Check for .conversation file
    conv_ref_file = os.path.join(TICKET_DIR, f"{ticket_id}.conversation")
    
    if not os.path.exists(conv_ref_file):
        # Fallback: Check if it's a direct conversation file (legacy or different setup)
        # Or maybe the ticket_id IS the filename?
        # Let's try to find the file.
        return {"error": "Conversation reference not found", "path": conv_ref_file}

    try:
        # 2. Read the path from the .conversation file
        with open(conv_ref_file, "r") as f:
            real_conv_path = f.read().strip()
            
        # 3. Read the actual JSON data
        if not os.path.exists(real_conv_path):
             return {"error": f"Conversation file not found at {real_conv_path}"}
             
        with open(real_conv_path, "r") as f:
            conv_data = json.load(f)
            
        # 4. Parse and transform
        frontend_messages = parse_conversation(conv_data)
        
        return frontend_messages
        
    except Exception as e:
        print(f"Error reading conversation: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
