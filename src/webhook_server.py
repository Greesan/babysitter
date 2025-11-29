"""
FastAPI webhook server for Agent SDK integration.

Provides:
- POST /webhook/notion - Receives Notion database webhook events
- POST /tickets/create - Create new tickets from frontend
- WebSocket /ws - Real-time communication with integrateThis UI
- GET / - Serves the frontend UI
"""
import uuid
import asyncio
from typing import Dict, Any, List, Set
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os
from pathlib import Path
from dotenv import load_dotenv

from src.agent import run_agent_for_ticket, AgentConfig

# Load environment variables
load_dotenv()


# FastAPI app
app = FastAPI(title="Agent SDK Webhook Server")


# Models
class NotionWebhookPayload(BaseModel):
    """Notion webhook payload model."""
    page_id: str = Field(..., description="Notion page ID")
    database_id: str = Field(..., description="Notion database ID")
    event_type: str = Field(..., description="Event type (page_created, page_updated, etc.)")


class CreateTicketPayload(BaseModel):
    """Payload for creating a new ticket."""
    ticket_name: str = Field(..., description="Name/title of the ticket")
    description: str | None = Field(None, description="Optional description")


class JobResponse(BaseModel):
    """Response model for job tracking."""
    job_id: str
    status: str
    ticket_id: str | None = None


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client."""
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")


# Global connection manager
manager = ConnectionManager()

# Store pending user responses (in production, use Redis or similar)
pending_responses: Dict[str, str] = {}


def get_websocket_manager() -> ConnectionManager:
    """Get the global WebSocket manager instance."""
    return manager


def get_pending_responses() -> Dict[str, str]:
    """Get the pending user responses dict."""
    return pending_responses


# Background task to run agent
async def run_agent_background(job_id: str, ticket_id: str, database_id: str):
    """
    Run agent in background.

    In production, this should use a proper task queue like Celery or RQ.
    """
    try:
        # Get config from environment
        notion_token = os.getenv("NOTION_TOKEN", "")
        notion_db_id = database_id

        config = AgentConfig(
            notion_token=notion_token,
            notion_db_id=notion_db_id,
            model="sonnet",
            max_turns=50,
        )

        # Run agent (now async)
        result = await run_agent_for_ticket(config)

        # Broadcast completion to WebSocket clients
        if result:
            await manager.broadcast({
                "type": "agent_complete",
                "job_id": job_id,
                "ticket_id": result.get("ticket_id"),
                "status": result.get("status"),
            })

    except Exception as e:
        print(f"Error running agent for job {job_id}: {e}")
        # Broadcast error
        await manager.broadcast({
            "type": "agent_error",
            "job_id": job_id,
            "error": str(e),
        })


async def trigger_agent_execution(ticket_id: str, database_id: str) -> Dict[str, Any]:
    """
    Trigger agent execution for a ticket.

    Args:
        ticket_id: Notion page ID of the ticket
        database_id: Notion database ID

    Returns:
        Dict with job_id and status
    """
    # Generate job ID
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    # In production, queue this with Celery/RQ
    # For now, run in background with asyncio
    asyncio.create_task(run_agent_background(job_id, ticket_id, database_id))

    return {
        "job_id": job_id,
        "status": "queued",
        "ticket_id": ticket_id,
    }


# Routes
@app.post("/webhook/notion")
async def notion_webhook(
    payload: NotionWebhookPayload,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Receive Notion database webhook events.

    When a new ticket is created or updated, trigger agent execution.
    """
    try:
        # Validate payload
        page_id = payload.page_id
        database_id = payload.database_id
        event_type = payload.event_type

        # Trigger agent execution
        result = await trigger_agent_execution(page_id, database_id)

        return JSONResponse(
            status_code=200,
            content=result
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication with UI.

    Messages:
    - user_response: User's response to agent question
    - agent_question: Agent asking for user input (broadcast)
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "user_response":
                # Store user response for agent to retrieve
                session_id = data.get("session_id")
                response = data.get("response")

                if session_id and response:
                    pending_responses[session_id] = response

                    # Acknowledge receipt
                    await manager.send_personal_message(
                        {
                            "type": "ack",
                            "session_id": session_id,
                            "status": "received",
                        },
                        websocket
                    )

            elif message_type == "ping":
                # Heartbeat
                await manager.send_personal_message(
                    {"type": "pong"},
                    websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket disconnected")


@app.post("/tickets/create")
async def create_ticket(payload: CreateTicketPayload) -> JSONResponse:
    """
    Create a new ticket in Notion and trigger agent execution.

    This endpoint creates a ticket with Status="Pending" and immediately
    triggers the agent to process it.
    """
    try:
        from notion_client import Client

        notion_token = os.getenv("NOTION_TOKEN", "")
        notion_db_id = os.getenv("NOTION_DB_ID", "")

        if not notion_token or not notion_db_id:
            raise HTTPException(status_code=500, detail="Missing NOTION_TOKEN or NOTION_DB_ID")

        # Create Notion client
        notion_client = Client(auth=notion_token)

        # Create ticket properties
        properties = {
            "Name": {
                "title": [{"text": {"content": payload.ticket_name}}]
            },
            "Status": {
                "status": {"name": "Pending"}
            }
        }

        # Add description if provided
        if payload.description:
            # Store in page content as a paragraph block
            children = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": payload.description}}]
                    }
                }
            ]
        else:
            children = []

        # Create the page in Notion
        new_page = notion_client.pages.create(
            parent={"database_id": notion_db_id},
            properties=properties,
            children=children
        )

        ticket_id = new_page["id"]

        # Broadcast ticket creation
        await manager.broadcast({
            "type": "ticket_created",
            "ticket_id": ticket_id,
            "ticket_name": payload.ticket_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Trigger agent execution
        result = await trigger_agent_execution(ticket_id, notion_db_id)

        return JSONResponse(
            status_code=200,
            content={
                "ticket_id": ticket_id,
                "ticket_name": payload.ticket_name,
                **result
            }
        )

    except Exception as e:
        print(f"Error creating ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def serve_frontend():
    """Serve the frontend UI."""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"status": "ok", "service": "agent-sdk-webhook-server", "note": "Frontend not found"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "agent-sdk-webhook-server"}


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a background job."""
    # In production, query from task queue/database
    # For now, return placeholder
    return {
        "job_id": job_id,
        "status": "running",  # or "completed", "failed"
    }
