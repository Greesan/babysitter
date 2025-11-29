"""
PostToolUse hook for Agent SDK.
Tracks tool usage metadata after each tool execution.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from src.notion_helper import (
    save_conversation_state,
    load_conversation_state,
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

    # Load existing conversation
    conversation = load_conversation_state(notion_client, ticket_id)

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

    # Append to conversation
    conversation.append(tool_entry)

    # Save updated conversation
    save_conversation_state(notion_client, ticket_id, conversation)

    # Increment turn count
    context._current_turn = current_turn + 1

    # TODO: Re-enable WebSocket broadcast once async handling is fixed
    print(f"Tool executed: {tool_event.get('tool_name', 'unknown')}")
