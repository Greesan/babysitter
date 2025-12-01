"""
UserPromptSubmit hook for Agent SDK.
Handles agent requests for user input by updating Notion and returning user response.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from src.notion_helper import (
    update_ticket_status,
    append_conversation_message,
)


def get_websocket_manager():
    """Import WebSocket manager lazily to avoid circular imports."""
    try:
        from src.webhook_server import get_websocket_manager
        return get_websocket_manager()
    except ImportError:
        return None


def get_pending_responses():
    """Import pending responses dict lazily to avoid circular imports."""
    try:
        from src.webhook_server import get_pending_responses
        return get_pending_responses()
    except ImportError:
        return {}


async def wait_for_user_response(
    notion_client: Any,
    ticket_id: str,
    session_id: str,
    timeout: float = 60  # Reduced from 300s to 60s
) -> Optional[str]:
    """
    Wait for user response via WebSocket or Notion polling (async version).

    First checks WebSocket pending_responses dict.
    If not available, falls back to async polling Notion.

    Args:
        notion_client: Notion client instance
        ticket_id: Notion page ID of the ticket
        session_id: Agent session ID
        timeout: Maximum time to wait in seconds (default 60s)

    Returns:
        User's response string, or None if timeout
    """
    pending_responses = get_pending_responses()
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < timeout:
        # Check WebSocket pending_responses first
        if session_id in pending_responses:
            response = pending_responses.pop(session_id)
            return response

        # Fallback: Poll Notion for user response
        try:
            # Run Notion API call in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            page = await loop.run_in_executor(
                None,
                notion_client.pages.retrieve,
                ticket_id
            )

            if "User Response" in page.get("properties", {}):
                response_prop = page["properties"]["User Response"]
                if response_prop.get("rich_text"):
                    response_text = response_prop["rich_text"][0]["plain_text"]
                    if response_text and response_text.strip():
                        return response_text
        except Exception as e:
            print(f"Error polling Notion for user response: {e}")

        # Async sleep - doesn't block event loop
        await asyncio.sleep(1)

    # Timeout reached
    return None


def user_prompt_submit_hook(context: Any, prompt: str) -> str:
    """
    Hook called when agent needs user input.

    Updates Notion ticket status to "Requesting User Input",
    saves the question to conversation JSON, broadcasts via WebSocket,
    and returns user's response.

    Args:
        context: ClaudeSDKClient instance with _notion_client, _current_ticket_id, _current_turn
        prompt: The question being asked by the agent

    Returns:
        User's response string
    """
    # Handle missing ticket_id gracefully
    if not hasattr(context, "_current_ticket_id") or not context._current_ticket_id:
        print("Warning: No ticket_id found, skipping Notion updates")
        return "[Simulated user response - no ticket context]"

    notion_client = context._notion_client
    ticket_id = context._current_ticket_id
    session_id = getattr(context, "_session_id", None)
    current_turn = getattr(context, "_current_turn", 0)

    # Update ticket status to "Requesting User Input"
    update_ticket_status(notion_client, ticket_id, "Requesting User Input")

    # Add question to conversation
    question_entry = {
        "role": "assistant",
        "content": prompt,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "turn": current_turn,
        "agent_question": prompt,
    }

    # Append message directly to Notion blocks (no load needed)
    append_conversation_message(notion_client, ticket_id, question_entry)

    # Increment turn count
    context._current_turn = current_turn + 1

    # Don't broadcast the initial prompt - only broadcast real questions
    is_initial_prompt = prompt.startswith("Execute the following task:")

    # Broadcast agent question via WebSocket (skip initial prompt)
    ws_manager = get_websocket_manager()
    if ws_manager and session_id and not is_initial_prompt:
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ws_manager.broadcast({
                    "type": "agent_message",
                    "session_id": session_id,
                    "ticket_id": ticket_id,
                    "content": prompt,
                    "timestamp": question_entry["timestamp"],
                    "turn": current_turn,
                    "message_type": "question"
                }))
            except RuntimeError:
                asyncio.ensure_future(ws_manager.broadcast({
                    "type": "agent_message",
                    "session_id": session_id,
                    "ticket_id": ticket_id,
                    "content": prompt,
                    "timestamp": question_entry["timestamp"],
                    "turn": current_turn,
                    "message_type": "question"
                }))
        except Exception as e:
            print(f"Error broadcasting agent question: {e}")
            import traceback
            traceback.print_exc()

    # For testing: Auto-respond to keep agent moving
    # TODO: Re-enable user input waiting once WebSocket event routing is implemented
    print(f"Agent asked: {prompt}")
    user_response = "Yes, please proceed with that."

    # Uncomment below to enable actual user input waiting:
    # user_response = asyncio.run(wait_for_user_response(
    #     notion_client, ticket_id, session_id, timeout=60
    # ))

    # Update status back to "Agent Working" after receiving response
    update_ticket_status(notion_client, ticket_id, "Agent Working")

    # Return response or simulated response if timeout
    if user_response:
        return user_response
    else:
        return "[Timeout - no user response received]"
