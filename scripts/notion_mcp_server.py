#!/usr/bin/env -S uv run --project /home/grees/greesCoding/claude-projects/babysitterPOC python
import os
import uuid
import json
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from notion_client import Client

# Get environment variables
TICKET_DIR = os.environ.get("CLAUDE_TICKET_DIR", "./tickets")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_TICKET_DB = os.environ.get("NOTION_TICKET_DB")
CLAUDE_SESSION_ID = os.environ.get("CLAUDE_SESSION_ID", "")

# Ensure directories exist
os.makedirs(TICKET_DIR, exist_ok=True)

# Create MCP server
app = Server("notion-ticket-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="ask_human",
            description="Create a Notion ticket to ask a human for help. Use this when you need human input, clarification, or decision-making. The conversation will suspend until a human responds in Notion.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or request for the human"
                    },
                    "conversation_file": {
                        "type": "string",
                        "description": "Path to the conversation file to resume later"
                    }
                },
                "required": ["question", "conversation_file"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    import sys
    print(f"[DEBUG] Tool called: {name}", file=sys.stderr)
    print(f"[DEBUG] NOTION_TOKEN length: {len(NOTION_TOKEN) if NOTION_TOKEN else 'None'}", file=sys.stderr)
    print(f"[DEBUG] NOTION_TOKEN repr: {repr(NOTION_TOKEN[:20] if NOTION_TOKEN else None)}", file=sys.stderr)

    if name != "ask_human":
        raise ValueError(f"Unknown tool: {name}")

    question = arguments["question"]
    conv_file = arguments["conversation_file"]

    # Create a unique ticket
    ticket = str(uuid.uuid4())

    # Save question and conversation reference
    with open(f"{TICKET_DIR}/{ticket}.question", "w") as f:
        f.write(question)
    with open(f"{TICKET_DIR}/{ticket}.conversation", "w") as f:
        f.write(conv_file)

    # Connect to Notion
    try:
        print(f"[DEBUG] Creating Notion client...", file=sys.stderr)
        notion = Client(auth=NOTION_TOKEN)
        print(f"[DEBUG] Notion client created successfully", file=sys.stderr)
    except Exception as e:
        print(f"[DEBUG] Error creating Notion client: {e}", file=sys.stderr)
        print(f"[DEBUG] Error type: {type(e).__name__}", file=sys.stderr)
        raise

    # Create Notion page
    page = notion.pages.create(
        parent={"database_id": NOTION_TICKET_DB},
        properties={
            "Name": {"title": [{"text": {"content": f"Ticket {ticket}"}}]},
            "Status": {"status": {"name": "Pending"}},
            "Ticket": {"rich_text": [{"text": {"content": ticket}}]},
            "Session ID": {"rich_text": [{"text": {"content": CLAUDE_SESSION_ID}}]}
        },
        children=[
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Claude Question"}}]}
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": question}}]}
            },
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": "Human Response"}}]}
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": ""}}]}
            },
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": "Ready to submit (check when done)"}}],
                    "checked": False
                }
            }
        ]
    )

    # Save page ID locally
    with open(f"{TICKET_DIR}/{ticket}.page", "w") as f:
        f.write(page["id"])

    # Return response
    response = {
        "status": "SUSPEND",
        "ticket": ticket,
        "message": f"Created Notion ticket {ticket}. Waiting for human response..."
    }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]

async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
