"""
PostToolUse hook for Agent SDK.
Tracks tool usage metadata after each tool execution.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from src.notion_helper import (
    append_conversation_message,
)


def get_websocket_manager():
    """Import WebSocket manager lazily to avoid circular imports."""
    try:
        from src.webhook_server import get_websocket_manager
        return get_websocket_manager()
    except ImportError:
        return None


def post_tool_use_hook(context: Any, tool_event: Dict[str, Any]) -> None:
    """
    Hook called after each tool use.

    Extracts tool metadata, saves to Notion conversation JSON,
    and broadcasts to WebSocket clients.

    Args:
        context: ClaudeSDKClient instance with _notion_client, _current_ticket_id, _current_turn
        tool_event: Dict with tool_name, tool_input, tool_output, and optionally error
    """
    # Handle missing ticket_id gracefully
    if not hasattr(context, "_current_ticket_id") or not context._current_ticket_id:
        print("Warning: No ticket_id found, skipping tool metadata tracking")
        return

    notion_client = context._notion_client
    ticket_id = context._current_ticket_id
    session_id = getattr(context, "_session_id", None)
    current_turn = getattr(context, "_current_turn", 0)

    # Create tool use entry
    tool_entry = {
        "type": "tool_use",
        "tool_name": tool_event.get("tool_name", "unknown"),
        "tool_input": tool_event.get("tool_input", {}),
        "tool_output": tool_event.get("tool_output"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "turn": current_turn,
    }

    # Add error if present
    if "error" in tool_event:
        tool_entry["error"] = tool_event["error"]

    # Append message directly to Notion blocks (no load needed)
    append_conversation_message(notion_client, ticket_id, tool_entry)

    # Increment turn count
    context._current_turn = current_turn + 1

    # Broadcast tool execution via WebSocket
    ws_manager = get_websocket_manager()
    if ws_manager and session_id:
        try:
            # Format tool output for display
            tool_output = tool_event.get("tool_output", {})
            if isinstance(tool_output, dict):
                output_str = tool_output.get("stdout", "")
                if tool_output.get("stderr"):
                    output_str += f"\n[stderr]\n{tool_output['stderr']}"
            else:
                output_str = str(tool_output)

            # Extract meaningful description from tool_input
            tool_input = tool_event.get("tool_input", {})
            tool_name = tool_event.get("tool_name", "unknown")

            # Create descriptive header for tool execution
            if tool_name == "Bash" and "command" in tool_input:
                tool_description = f"Bash: {tool_input['command'][:80]}"
            elif "description" in tool_input:
                tool_description = f"{tool_name}: {tool_input['description'][:80]}"
            else:
                tool_description = tool_name

            # Get the running event loop and schedule broadcast
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                print(f"Broadcasting tool_execution: {tool_description} to {len(ws_manager.active_connections)} connections")
                loop.create_task(ws_manager.broadcast({
                    "type": "tool_execution",
                    "session_id": session_id,
                    "ticket_id": ticket_id,
                    "tool_name": tool_name,
                    "tool_description": tool_description,
                    "tool_input": tool_input,
                    "tool_output": output_str,
                    "timestamp": tool_entry["timestamp"],
                    "turn": current_turn
                }))
            except RuntimeError:
                # No running loop - create task differently
                print(f"No running loop - using ensure_future for tool_execution broadcast")
                asyncio.ensure_future(ws_manager.broadcast({
                    "type": "tool_execution",
                    "session_id": session_id,
                    "ticket_id": ticket_id,
                    "tool_name": tool_name,
                    "tool_description": tool_description,
                    "tool_input": tool_input,
                    "tool_output": output_str,
                    "timestamp": tool_entry["timestamp"],
                    "turn": current_turn
                }))
        except Exception as e:
            print(f"Error broadcasting tool execution: {e}")
            import traceback
            traceback.print_exc()

    print(f"Tool executed: {tool_event.get('tool_name', 'unknown')}")
