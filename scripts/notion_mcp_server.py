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
INCLUDE_METADATA = os.environ.get("INCLUDE_METADATA", "false").lower() == "true"

# Ensure directories exist
os.makedirs(TICKET_DIR, exist_ok=True)

def extract_metadata(conv_file_path):
    """Extract metadata from conversation file for Notion display."""
    if not INCLUDE_METADATA or not os.path.exists(conv_file_path):
        return None

    try:
        with open(conv_file_path, 'r') as f:
            conv_data = json.load(f)

        metadata = {
            "tool_calls": [],
            "files_changed": set(),
            "commands": [],
            "conversation_summary": []
        }

        # Parse conversation messages
        messages = conv_data.get("messages", [])

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", [])

            # Extract tool uses from assistant messages
            if role == "assistant":
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tool_input = item.get("input", {})

                        # Track tool call
                        metadata["tool_calls"].append({
                            "name": tool_name,
                            "input": tool_input
                        })

                        # Track file changes
                        if tool_name in ["Edit", "Write"]:
                            file_path = tool_input.get("file_path", "")
                            if file_path:
                                metadata["files_changed"].add(file_path)

                        # Track bash commands
                        if tool_name == "Bash":
                            command = tool_input.get("command", "")
                            if command:
                                metadata["commands"].append(command)

            # Build conversation summary
            if role in ["user", "assistant"]:
                text_content = ""
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_content = item.get("text", "")[:200]  # First 200 chars
                    elif isinstance(item, str):
                        text_content = item[:200]

                if text_content:
                    metadata["conversation_summary"].append({
                        "role": role,
                        "text": text_content
                    })

        metadata["files_changed"] = list(metadata["files_changed"])
        return metadata

    except Exception as e:
        import sys
        print(f"[DEBUG] Error extracting metadata: {e}", file=sys.stderr)
        return None

def create_metadata_blocks(metadata):
    """Create Notion blocks for metadata display."""
    if not metadata:
        return []

    blocks = []

    # Tool Calls toggle
    if metadata["tool_calls"]:
        tool_lines = []
        for i, tool in enumerate(metadata["tool_calls"], 1):
            tool_name = tool["name"]
            tool_input = tool["input"]
            # Summarize input
            summary = ""
            if tool_name in ["Edit", "Write", "Read"]:
                summary = f"→ {tool_input.get('file_path', 'unknown')}"
            elif tool_name == "Bash":
                cmd = tool_input.get('command', '')[:60]
                summary = f"→ {cmd}{'...' if len(tool_input.get('command', '')) > 60 else ''}"
            else:
                summary = f"→ {str(tool_input)[:60]}..."

            tool_lines.append(f"{i}. {tool_name} {summary}")

        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": f"🔧 Tools Used ({len(metadata['tool_calls'])})"}}],
                "children": [{
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line}}]}
                } for line in tool_lines]
            }
        })

    # Files Changed toggle
    if metadata["files_changed"]:
        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": f"📝 Files Changed ({len(metadata['files_changed'])})"}}],
                "children": [{
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f}}]}
                } for f in metadata["files_changed"]]
            }
        })

    # Commands toggle
    if metadata["commands"]:
        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": f"💻 Commands ({len(metadata['commands'])})"}}],
                "children": [{
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": cmd}}],
                        "language": "bash"
                    }
                } for cmd in metadata["commands"]]
            }
        })

    # Conversation summary toggle
    if metadata["conversation_summary"]:
        conv_blocks = []
        for msg in metadata["conversation_summary"]:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            conv_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"{role_emoji} {msg['text']}"}}]}
            })

        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": f"💬 Conversation Summary ({len(metadata['conversation_summary'])} messages)"}}],
                "children": conv_blocks
            }
        })

    return blocks

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

        print(f"[DEBUG] Multi-turn detected for ticket {ticket}", file=sys.stderr)

        try:
            # Get current page content
            print(f"[DEBUG] Retrieving page properties...", file=sys.stderr)
            page = notion.pages.retrieve(page_id=page_id)

            # Get current turn count
            turn_count_prop = page["properties"].get("Turn Count", {})
            current_turn = turn_count_prop.get("number", 1) if turn_count_prop else 1
            new_turn = current_turn + 1
            print(f"[DEBUG] Current turn: {current_turn}, new turn: {new_turn}", file=sys.stderr)

            # Simplified approach: Just append new turn blocks at the end
            print(f"[DEBUG] Appending new turn blocks...", file=sys.stderr)
            new_turn_blocks = [
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"🔄 TURN {new_turn}"}}]}
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

            # Add metadata blocks if enabled
            metadata = extract_metadata(conv_file)
            if metadata:
                print(f"[DEBUG] Adding metadata blocks to turn {new_turn}", file=sys.stderr)
                metadata_blocks = create_metadata_blocks(metadata)
                new_turn_blocks.extend(metadata_blocks)

            # Append blocks to end of page
            append_result = notion.blocks.children.append(
                block_id=page_id,
                children=new_turn_blocks
            )
            print(f"[DEBUG] Blocks appended successfully", file=sys.stderr)

            # Update properties
            print(f"[DEBUG] Updating page properties...", file=sys.stderr)
            update_result = notion.pages.update(
                page_id=page_id,
                properties={
                    "Turn Count": {"number": new_turn},
                    "Status": {"status": {"name": "Requesting User Input"}}
                }
            )
            print(f"[DEBUG] Properties updated successfully", file=sys.stderr)
            print(f"[DEBUG] New status: {update_result['properties']['Status']}", file=sys.stderr)

            print(f"[DEBUG] Updated existing ticket {ticket} to turn {new_turn}", file=sys.stderr)

        except Exception as e:
            print(f"[ERROR] Failed to update multi-turn ticket: {e}", file=sys.stderr)
            print(f"[ERROR] Exception type: {type(e).__name__}", file=sys.stderr)
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr)
            # Fall back to returning an error to Claude
            response = {
                "status": "ERROR",
                "ticket": ticket,
                "message": f"Failed to update ticket: {str(e)}"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

    else:
        # First turn: Create new ticket
        ticket = str(uuid.uuid4())
        print(f"[DEBUG] Creating new ticket {ticket}", file=sys.stderr)

        try:
            # Save question and conversation reference
            with open(f"{TICKET_DIR}/{ticket}.question", "w") as f:
                f.write(question)
            with open(f"{TICKET_DIR}/{ticket}.conversation", "w") as f:
                f.write(conv_file)

            print(f"[DEBUG] Creating Notion page...", file=sys.stderr)

            # Build children blocks
            children_blocks = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🔄 TURN 1"}}]}
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

            # Add metadata blocks if enabled
            metadata = extract_metadata(conv_file)
            if metadata:
                print(f"[DEBUG] Adding metadata blocks to new ticket", file=sys.stderr)
                metadata_blocks = create_metadata_blocks(metadata)
                children_blocks.extend(metadata_blocks)

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
                children=children_blocks
            )

            page_id = page["id"]
            print(f"[DEBUG] Notion page created with ID: {page_id}", file=sys.stderr)

            # Save page ID locally
            with open(f"{TICKET_DIR}/{ticket}.page", "w") as f:
                f.write(page_id)

            print(f"[DEBUG] Created new ticket {ticket} successfully", file=sys.stderr)

        except Exception as e:
            print(f"[ERROR] Failed to create new ticket: {e}", file=sys.stderr)
            print(f"[ERROR] Exception type: {type(e).__name__}", file=sys.stderr)
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr)
            # Fall back to returning an error to Claude
            response = {
                "status": "ERROR",
                "message": f"Failed to create ticket: {str(e)}"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

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
