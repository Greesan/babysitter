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

    # Connect to Notion
    try:
        print(f"[DEBUG] Creating Notion client...", file=sys.stderr)
        notion = Client(auth=NOTION_TOKEN)
        print(f"[DEBUG] Notion client created successfully", file=sys.stderr)
    except Exception as e:
        print(f"[DEBUG] Error creating Notion client: {e}", file=sys.stderr)
        print(f"[DEBUG] Error type: {type(e).__name__}", file=sys.stderr)
        raise

    # Check for existing ticket with this Session ID
    existing_ticket = None
    existing_page_id = None

    if CLAUDE_SESSION_ID:
        print(f"[DEBUG] Searching for existing ticket with session ID: {CLAUDE_SESSION_ID}", file=sys.stderr)
        # Search local ticket files first
        for filename in os.listdir(TICKET_DIR):
            if filename.endswith(".page"):
                ticket_id = filename.replace(".page", "")
                page_id_path = f"{TICKET_DIR}/{ticket_id}.page"
                if os.path.exists(page_id_path):
                    with open(page_id_path, "r") as f:
                        page_id = f.read().strip()
                    try:
                        page = notion.pages.retrieve(page_id=page_id)
                        page_session_id = page["properties"].get("Session ID", {}).get("rich_text", [])
                        if page_session_id and page_session_id[0]["text"]["content"] == CLAUDE_SESSION_ID:
                            existing_ticket = ticket_id
                            existing_page_id = page_id
                            print(f"[DEBUG] Found existing ticket: {existing_ticket}", file=sys.stderr)
                            break
                    except Exception as e:
                        print(f"[DEBUG] Error checking ticket {ticket_id}: {e}", file=sys.stderr)
                        continue

    if existing_ticket and existing_page_id:
        # Multi-turn: Update existing ticket
        ticket = existing_ticket
        page_id = existing_page_id

        # Get current page content
        page = notion.pages.retrieve(page_id=page_id)
        blocks = notion.blocks.children.list(block_id=page_id)["results"]

        # Get current turn count
        turn_count_prop = page["properties"].get("Turn Count", {})
        current_turn = turn_count_prop.get("number", 1) if turn_count_prop else 1
        new_turn = current_turn + 1

        # Find the current turn section (before "PREVIOUS TURNS" divider)
        current_turn_blocks = []
        history_divider_id = None
        found_divider = False

        for block in blocks:
            if block["type"] == "divider":
                history_divider_id = block["id"]
                found_divider = True
                break
            current_turn_blocks.append(block)

        # Extract last human response before creating toggle
        last_human_response = ""
        for block in reversed(current_turn_blocks):
            if block["type"] == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                if rich_text:
                    text = "".join([t["text"]["content"] for t in rich_text])
                    if text.strip():
                        last_human_response = text.strip()
                        break

        # Create toggle for previous turn
        toggle_title = f"Turn {current_turn}: Human said \"{last_human_response[:50]}{'...' if len(last_human_response) > 50 else ''}\""
        toggle_block = {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": toggle_title}}],
                "children": current_turn_blocks[1:]  # Skip the first heading
            }
        }

        # Delete old current turn blocks
        for block in current_turn_blocks:
            try:
                notion.blocks.delete(block_id=block["id"])
            except Exception as e:
                print(f"[DEBUG] Error deleting block: {e}", file=sys.stderr)

        # Add new blocks: current turn at top, then history
        new_blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"CURRENT TURN (Turn {new_turn})"}}]}
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Claude asks: {question}"}}]}
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

        if not found_divider:
            # First multi-turn, add divider and history heading
            new_blocks.extend([
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📚 PREVIOUS TURNS"}}]}
                }
            ])

        # Add toggle for previous turn
        new_blocks.append(toggle_block)

        # Append new blocks at the top
        notion.blocks.children.append(block_id=page_id, children=new_blocks, after=None)

        # Update properties
        notion.pages.update(
            page_id=page_id,
            properties={
                "Turn Count": {"number": new_turn},
                "Status": {"status": {"name": "Requesting User Input"}}
            }
        )

        print(f"[DEBUG] Updated existing ticket {ticket} to turn {new_turn}", file=sys.stderr)

    else:
        # First turn: Create new ticket
        ticket = str(uuid.uuid4())

        # Save question and conversation reference
        with open(f"{TICKET_DIR}/{ticket}.question", "w") as f:
            f.write(question)
        with open(f"{TICKET_DIR}/{ticket}.conversation", "w") as f:
            f.write(conv_file)

        # Create Notion page
        page = notion.pages.create(
            parent={"database_id": NOTION_TICKET_DB},
            properties={
                "Name": {"title": [{"text": {"content": f"Ticket {ticket}"}}]},
                "Status": {"status": {"name": "Requesting User Input"}},
                "Ticket": {"rich_text": [{"text": {"content": ticket}}]},
                "Session ID": {"rich_text": [{"text": {"content": CLAUDE_SESSION_ID}}]},
                "Turn Count": {"number": 1}
            },
            children=[
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": "CURRENT TURN (Turn 1)"}}]}
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Claude asks: {question}"}}]}
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

        page_id = page["id"]

        # Save page ID locally
        with open(f"{TICKET_DIR}/{ticket}.page", "w") as f:
            f.write(page_id)

        print(f"[DEBUG] Created new ticket {ticket}", file=sys.stderr)

    # Return response
    response = {
        "status": "SUSPEND",
        "ticket": ticket,
        "message": f"{'Updated' if existing_ticket else 'Created'} Notion ticket {ticket}. Waiting for human response..."
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
