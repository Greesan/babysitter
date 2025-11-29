"""
SessionStart hook for Agent SDK.
Initializes session state when agent starts.
"""
from typing import Any, List, Dict
from src.notion_helper import (
    update_ticket_status,
    load_conversation_state,
)


def session_start_hook(context: Any) -> List[Dict[str, Any]]:
    """
    Hook called when agent session starts.

    Updates ticket status to "Agent Working", loads existing conversation,
    and initializes turn counter.

    Args:
        context: ClaudeSDKClient instance with _notion_client, _current_ticket_id, _current_turn

    Returns:
        List of conversation history entries, or empty list if new session
    """
    # Handle missing ticket_id gracefully
    if not hasattr(context, "_current_ticket_id") or not context._current_ticket_id:
        print("Warning: No ticket_id found, skipping session initialization")
        return []

    notion_client = context._notion_client
    ticket_id = context._current_ticket_id

    # Update ticket status to "Agent Working"
    update_ticket_status(notion_client, ticket_id, "Agent Working")

    # Load existing conversation
    conversation = load_conversation_state(notion_client, ticket_id)

    # Initialize turn counter based on existing conversation
    if conversation:
        # Find the maximum turn number
        max_turn = max(entry.get("turn", 0) for entry in conversation)
        context._current_turn = max_turn + 1
    else:
        # New session, start at turn 0
        context._current_turn = 0

    return conversation
