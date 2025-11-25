#!/usr/bin/env -S uv run --project /home/grees/greesCoding/claude-projects/babysitterPOC python
import os
import sys
import uuid
import json
import asyncio
import subprocess
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent
import tiktoken

# Import shared utilities
from utils.logging import setup_logging
from utils.notion_client import get_notion_client

# Get environment variables
TICKET_DIR = os.environ.get("CLAUDE_TICKET_DIR", "./tickets")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_TICKET_DB = os.environ.get("NOTION_TICKET_DB")
CLAUDE_SESSION_ID = os.environ.get("CLAUDE_SESSION_ID", "")
INCLUDE_METADATA = os.environ.get("INCLUDE_METADATA", "false").lower() == "true"

# Ensure directories exist
os.makedirs(TICKET_DIR, exist_ok=True)

# Setup logging using shared utility
logger = setup_logging("notion_mcp_server")

def extract_metadata(conv_file_path):
    """Extract metadata from conversation file for Notion display."""
    # Check INCLUDE_METADATA at runtime to allow tests to override
    include_metadata = os.environ.get("INCLUDE_METADATA", "false").lower() == "true"
    if not include_metadata:
        logger.debug("Metadata disabled (INCLUDE_METADATA=false)")
        return None

    # IMPORTANT: The conversation file might be a temporary file that gets deleted quickly.
    # We need to read it immediately and optionally save a copy for debugging.
    if not os.path.exists(conv_file_path):
        logger.warning(f"Conversation file not found: {conv_file_path}")
        logger.warning("Metadata extraction skipped - file doesn't exist")
        return None

    try:
        with open(conv_file_path, 'r') as f:
            conv_data = json.load(f)

        # Save a copy for future reads (since temp file gets deleted)
        debug_dir = os.path.join(TICKET_DIR, "conversations")
        os.makedirs(debug_dir, exist_ok=True)
        import shutil
        saved_path = os.path.join(debug_dir, f"{CLAUDE_SESSION_ID}.json")
        shutil.copy(conv_file_path, saved_path)
        logger.debug(f"Saved conversation copy to {saved_path}")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in conversation file: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error reading conversation file: {e}", exc_info=True)
        return None

    try:
        # Initialize tiktoken encoder for Claude
        try:
            encoding = tiktoken.encoding_for_model("gpt-4")  # Claude uses similar tokenization
        except Exception as e:
            logger.warning(f"Could not initialize tiktoken: {e}")
            encoding = None

        metadata = {
            "tool_calls": [],
            "files_changed": set(),
            "commands": [],
            "conversation_summary": [],
            "token_usage": {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0},
            "execution_time": {"started_at": None, "completed_at": None, "duration_seconds": 0},
            "tool_timeline": [],
            "git_changes": {"files_modified": 0, "lines_added": 0, "lines_deleted": 0, "diff": ""}
        }

        # Parse conversation messages
        messages = conv_data.get("messages", [])

        # Track timing
        first_timestamp = None
        last_timestamp = None

        for msg_idx, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", [])

            # Try to get timestamp from message metadata (if available)
            timestamp = msg.get("timestamp") or msg.get("created_at")
            if timestamp:
                if not first_timestamp:
                    first_timestamp = timestamp
                last_timestamp = timestamp

            # Count tokens for this message
            if encoding:
                for item in content:
                    text = ""
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                    elif isinstance(item, str):
                        text = item

                    if text:
                        try:
                            token_count = len(encoding.encode(text))
                            if role == "user":
                                metadata["token_usage"]["input_tokens"] += token_count
                            else:
                                metadata["token_usage"]["output_tokens"] += token_count
                            metadata["token_usage"]["total_tokens"] += token_count
                        except Exception as e:
                            logger.debug(f"Token counting error: {e}")

            # Extract tool uses from assistant messages
            if role == "assistant":
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tool_input = item.get("input", {})
                        tool_id = item.get("id", "")

                        # Track tool call with timestamp
                        tool_call_entry = {
                            "name": tool_name,
                            "input": tool_input,
                            "timestamp": timestamp or f"msg_{msg_idx}"
                        }
                        metadata["tool_calls"].append(tool_call_entry)

                        # Add to timeline
                        metadata["tool_timeline"].append({
                            "tool": tool_name,
                            "timestamp": timestamp or f"msg_{msg_idx}",
                            "summary": summarize_tool_call(tool_name, tool_input)
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

        # Calculate execution time
        if first_timestamp and last_timestamp:
            try:
                # Try to parse ISO timestamps
                start = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                end = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                duration = (end - start).total_seconds()
                metadata["execution_time"] = {
                    "started_at": first_timestamp,
                    "completed_at": last_timestamp,
                    "duration_seconds": duration
                }
            except Exception as e:
                logger.debug(f"Could not parse timestamps: {e}")

        # Get git diff (if in a git repo)
        try:
            conv_dir = os.path.dirname(conv_file_path)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # Check if we're in a git repo
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                # Get diff stats
                diff_stat = subprocess.run(
                    ["git", "diff", "--stat", "HEAD"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if diff_stat.returncode == 0 and diff_stat.stdout.strip():
                    # Parse diff stats
                    lines = diff_stat.stdout.strip().split('\n')
                    if lines:
                        # Last line has summary: "X files changed, Y insertions(+), Z deletions(-)"
                        summary_line = lines[-1]
                        metadata["git_changes"]["files_modified"] = len(lines) - 1

                        # Parse additions/deletions
                        if "insertion" in summary_line:
                            parts = summary_line.split(',')
                            for part in parts:
                                if "insertion" in part:
                                    metadata["git_changes"]["lines_added"] = int(part.strip().split()[0])
                                elif "deletion" in part:
                                    metadata["git_changes"]["lines_deleted"] = int(part.strip().split()[0])

                        # Get actual diff (limited to 2000 chars for Notion)
                        diff_output = subprocess.run(
                            ["git", "diff", "HEAD"],
                            cwd=project_root,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if diff_output.returncode == 0:
                            metadata["git_changes"]["diff"] = diff_output.stdout[:2000]

        except Exception as e:
            logger.debug(f"Could not get git diff: {e}")

        # Calculate estimated cost (using Claude Sonnet 4.5 pricing)
        # $3 per million input tokens, $15 per million output tokens
        input_cost = (metadata["token_usage"]["input_tokens"] / 1_000_000) * 3.0
        output_cost = (metadata["token_usage"]["output_tokens"] / 1_000_000) * 15.0
        metadata["token_usage"]["estimated_cost_usd"] = round(input_cost + output_cost, 4)

        metadata["files_changed"] = list(metadata["files_changed"])
        return metadata

    except Exception as e:
        logger.error(f"Error extracting metadata: {e}", exc_info=True)
        return None


def summarize_tool_call(tool_name, tool_input):
    """Create a brief summary of a tool call for timeline display."""
    if tool_name in ["Edit", "Write", "Read"]:
        file_path = tool_input.get("file_path", "unknown")
        return f"{file_path}"
    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")[:40]
        return f"{cmd}{'...' if len(tool_input.get('command', '')) > 40 else ''}"
    elif tool_name == "Grep":
        pattern = tool_input.get("pattern", "")[:30]
        return f"pattern: {pattern}"
    elif tool_name == "Glob":
        pattern = tool_input.get("pattern", "")[:30]
        return f"pattern: {pattern}"
    else:
        return f"{str(tool_input)[:40]}..."

def create_metadata_blocks(metadata):
    """Create Notion blocks for metadata display."""
    if not metadata:
        return []

    blocks = []

    # Token Usage & Cost (PROMINENT - at the top)
    token_info = metadata.get("token_usage", {})
    if token_info.get("total_tokens", 0) > 0:
        cost_text = f"${token_info.get('estimated_cost_usd', 0):.4f}"
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"💰 {token_info['total_tokens']:,} tokens | {cost_text} | ⬆️ {token_info['input_tokens']:,} in | ⬇️ {token_info['output_tokens']:,} out"}}],
                "icon": {"emoji": "💰"},
                "color": "blue_background"
            }
        })

    # Execution Time & Performance
    exec_info = metadata.get("execution_time", {})
    if exec_info.get("duration_seconds", 0) > 0:
        duration = exec_info["duration_seconds"]
        if duration < 60:
            duration_str = f"{duration:.1f}s"
        elif duration < 3600:
            duration_str = f"{duration/60:.1f}m"
        else:
            duration_str = f"{duration/3600:.1f}h"

        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"⏱️ Duration: {duration_str}"}}],
                "icon": {"emoji": "⏱️"},
                "color": "green_background"
            }
        })

    # Git Changes
    git_info = metadata.get("git_changes", {})
    if git_info.get("files_modified", 0) > 0 or git_info.get("diff", ""):
        git_summary = f"📊 {git_info.get('files_modified', 0)} files | "
        git_summary += f"+{git_info.get('lines_added', 0)} -{git_info.get('lines_deleted', 0)} lines"

        git_children = []

        # Add diff if available
        if git_info.get("diff"):
            git_children.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": git_info["diff"]}}],
                    "language": "diff"
                }
            })

        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": git_summary}}],
                "children": git_children if git_children else [{
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Run 'git diff' to see changes"}}]}
                }]
            }
        })

    # Tool Timeline
    timeline = metadata.get("tool_timeline", [])
    if timeline:
        timeline_children = []
        for entry in timeline:
            tool_name = entry["tool"]
            timestamp = entry.get("timestamp", "")
            summary = entry.get("summary", "")

            # Format timestamp if it's ISO format
            time_str = ""
            if isinstance(timestamp, str) and 'T' in timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = str(timestamp)
            else:
                time_str = str(timestamp)

            timeline_children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": f"[{time_str}] {tool_name} → {summary}"}}]}
            })

        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": f"📊 Tool Timeline ({len(timeline)} calls)"}}],
                "children": timeline_children
            }
        })

    # Tool Calls toggle (detailed view)
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
    """Handle tool calls.

    Note: We create a new Notion Client per request for simplicity and
    async safety. The underlying httpx library maintains a connection pool,
    so TCP connections are reused despite creating new Client objects.
    This stateless approach avoids issues with token expiry, connection
    staleness, and shared mutable state in async contexts.
    """
    logger.debug(f"Tool called: {name}")
    logger.debug(f"NOTION_TOKEN length: {len(NOTION_TOKEN) if NOTION_TOKEN else 'None'}")
    logger.debug(f"NOTION_TOKEN repr: {repr(NOTION_TOKEN[:20] if NOTION_TOKEN else None)}")

    if name != "ask_human":
        raise ValueError(f"Unknown tool: {name}")

    question = arguments["question"]
    conv_file = arguments["conversation_file"]

    # Connect to Notion
    try:
        logger.debug("Creating Notion client...")
        notion = get_notion_client()
        logger.debug("Notion client created successfully")
    except Exception as e:
        logger.error(f"Error creating Notion client: {e}", exc_info=True)
        raise

    # Check for existing ticket with this Session ID
    existing_ticket = None
    existing_page_id = None

    if CLAUDE_SESSION_ID:
        logger.debug(f"Searching for existing ticket with session ID: {CLAUDE_SESSION_ID}")
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
                            logger.debug(f"Found existing ticket: {existing_ticket}")
                            break
                    except Exception as e:
                        logger.debug(f"Error checking ticket {ticket_id}: {e}")
                        continue

    if existing_ticket and existing_page_id:
        # Multi-turn: Update existing ticket
        ticket = existing_ticket
        page_id = existing_page_id

        logger.debug(f"Multi-turn detected for ticket {ticket}")

        try:
            # Get current page content
            logger.debug("Retrieving page properties...")
            page = notion.pages.retrieve(page_id=page_id)

            # Get current turn count
            turn_count_prop = page["properties"].get("Turn Count", {})
            current_turn = turn_count_prop.get("number", 1) if turn_count_prop else 1
            new_turn = current_turn + 1
            logger.debug(f"Current turn: {current_turn}, new turn: {new_turn}")

            # Simplified approach: Just append new turn blocks at the end
            logger.debug("Appending new turn blocks...")
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
                logger.debug(f"Adding metadata blocks to turn {new_turn}")
                metadata_blocks = create_metadata_blocks(metadata)
                new_turn_blocks.extend(metadata_blocks)

            # Append blocks to end of page
            append_result = notion.blocks.children.append(
                block_id=page_id,
                children=new_turn_blocks
            )
            logger.debug("Blocks appended successfully")

            # Update properties
            logger.debug("Updating page properties...")
            update_result = notion.pages.update(
                page_id=page_id,
                properties={
                    "Turn Count": {"number": new_turn},
                    "Status": {"status": {"name": "Requesting User Input"}}
                }
            )
            logger.debug("Properties updated successfully")
            logger.debug(f"New status: {update_result['properties']['Status']}")

            logger.info(f"Updated existing ticket {ticket} to turn {new_turn}")

        except Exception as e:
            logger.error(f"Failed to update multi-turn ticket: {e}", exc_info=True)
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
        logger.debug(f"Creating new ticket {ticket}")

        try:
            # Save conversation reference
            with open(f"{TICKET_DIR}/{ticket}.conversation", "w") as f:
                f.write(conv_file)

            logger.debug("Creating Notion page...")

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
                logger.debug("Adding metadata blocks to new ticket")
                metadata_blocks = create_metadata_blocks(metadata)
                children_blocks.extend(metadata_blocks)

            # Create Notion page with "Agent Planning" status
            page = notion.pages.create(
                parent={"database_id": NOTION_TICKET_DB},
                properties={
                    "Name": {"title": [{"text": {"content": f"Ticket {ticket}"}}]},
                    "Status": {"status": {"name": "Agent Planning"}},
                    "Ticket": {"rich_text": [{"text": {"content": ticket}}]},
                    "Session ID": {"rich_text": [{"text": {"content": CLAUDE_SESSION_ID}}]},
                    "Turn Count": {"number": 1}
                },
                children=children_blocks
            )

            page_id = page["id"]
            logger.debug(f"Notion page created with ID: {page_id}")

            # Update status to "Requesting User Input"
            logger.debug("Updating page status to 'Requesting User Input'...")
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Status": {"status": {"name": "Requesting User Input"}}
                }
            )
            logger.debug("Status updated successfully")

            # Save page ID locally
            with open(f"{TICKET_DIR}/{ticket}.page", "w") as f:
                f.write(page_id)

            logger.info(f"Created new ticket {ticket} successfully")

        except Exception as e:
            logger.error(f"Failed to create new ticket: {e}", exc_info=True)
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
