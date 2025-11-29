"""
Agent SDK runner for autonomous ticket processing.
Integrates with Notion for task management and conversation persistence.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from notion_client import Client
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import HookMatcher

from src.notion_helper import (
    claim_pending_ticket,
    get_ticket_context,
    update_ticket_status,
    save_conversation_state,
)
from src.hooks.user_prompt import user_prompt_submit_hook
from src.hooks.post_tool_use import post_tool_use_hook
from src.hooks.session_start import session_start_hook


@dataclass
class AgentConfig:
    """Configuration for the agent."""

    notion_token: str
    notion_db_id: str
    model: str = "sonnet"
    max_turns: int = 50
    timeout_seconds: int = 600


def initialize_agent(config: AgentConfig) -> ClaudeSDKClient:
    """
    Initialize Claude SDK client with configuration and hooks.

    Args:
        config: Agent configuration

    Returns:
        Configured ClaudeSDKClient instance with hooks registered
    """
    # Create Notion client for the agent to use
    notion_client = Client(auth=config.notion_token)

    # Store client reference globally so hooks can access it
    # This is a workaround since HookContext doesn't provide client access
    _agent_client_ref = {"client": None}

    # Create hook wrappers that adapt our hooks to SDK signature
    # SDK signature: async def hook(input_data: dict, tool_use_id: str | None, context: HookContext) -> dict
    async def user_prompt_wrapper(input_data, tool_use_id, hook_context):
        """Wrapper for UserPromptSubmit hook."""
        # input_data contains 'prompt' key
        prompt = input_data.get("prompt", "")

        # Get client from our global reference
        client_instance = _agent_client_ref.get("client")
        if not client_instance:
            return {"response": "[No client available]"}

        # Call our custom hook
        response = user_prompt_submit_hook(context=client_instance, prompt=prompt)

        # Return in SDK format
        return {"response": response}

    async def post_tool_wrapper(input_data, tool_use_id, hook_context):
        """Wrapper for PostToolUse hook."""
        # input_data contains tool execution data
        tool_event = {
            "tool_name": input_data.get("tool_name", "unknown"),
            "tool_input": input_data.get("tool_input", {}),
            "tool_output": input_data.get("tool_response"),  # SDK uses 'tool_response', not 'tool_output'
        }
        if "error" in input_data:
            tool_event["error"] = input_data["error"]

        # Get client from our global reference
        client_instance = _agent_client_ref.get("client")
        if not client_instance:
            return {}

        # Call our custom hook
        post_tool_use_hook(context=client_instance, tool_event=tool_event)

        # Return empty dict
        return {}

    # Configure hooks
    hooks = {
        "UserPromptSubmit": [HookMatcher(hooks=[user_prompt_wrapper])],
        "PostToolUse": [HookMatcher(hooks=[post_tool_wrapper])],
    }

    # Create agent options with hooks
    options = ClaudeAgentOptions(
        model=config.model,
        max_turns=config.max_turns,
        hooks=hooks,
    )

    # Initialize Claude SDK client
    client = ClaudeSDKClient(options=options)

    # Store notion client reference for hooks to use
    client._notion_client = notion_client
    client._notion_db_id = config.notion_db_id

    # Store client in our global reference so hooks can access it
    _agent_client_ref["client"] = client

    return client


async def run_agent_for_ticket(config: AgentConfig) -> Optional[Dict[str, Any]]:
    """
    Claim a pending ticket and run the agent to process it.

    Args:
        config: Agent configuration

    Returns:
        Dict with execution results, or None if no tickets to process
    """
    # Create Notion client
    notion_client = Client(auth=config.notion_token)

    # Claim a pending ticket
    claimed_ticket = claim_pending_ticket(notion_client, config.notion_db_id)

    if not claimed_ticket:
        print("No pending tickets found")
        return None

    ticket_id = claimed_ticket["ticket_id"]
    session_id = claimed_ticket["session_id"]
    ticket_name = claimed_ticket["ticket_name"]

    print(f"Processing ticket: {ticket_name}")
    print(f"  Ticket ID: {ticket_id}")
    print(f"  Session ID: {session_id}")

    # Load ticket context
    context = get_ticket_context(notion_client, ticket_id)

    if not context:
        print(f"Error: Could not load context for ticket {ticket_id}")
        return None

    # Initialize agent
    client = initialize_agent(config)

    # Store ticket info in client for hooks to access
    client._current_ticket_id = ticket_id
    client._session_id = session_id  # Used by hooks for WebSocket broadcast
    client._current_turn = context["turn_count"]

    # Broadcast agent started via WebSocket
    try:
        from src.webhook_server import get_websocket_manager
        ws_manager = get_websocket_manager()
        if ws_manager:
            import asyncio
            from datetime import datetime, timezone
            await ws_manager.broadcast({
                "type": "agent_started",
                "ticket_id": ticket_id,
                "ticket_name": ticket_name,
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        print(f"Error broadcasting agent_started: {e}")

    # Call session_start hook to initialize session state
    conversation_history = session_start_hook(context=client)

    # Create initial prompt from ticket
    initial_prompt = f"""You are working on the following task:

{ticket_name}

Please analyze this task and begin working on it. If you need clarification or input from the user, ask questions.
"""

    try:
        # Connect the client first
        print(f"Connecting Claude SDK client...")
        await client.connect()

        # Start the agent with the prompt
        print(f"Starting agent execution for session: {session_id}")
        await client.query(prompt=initial_prompt, session_id=session_id)

        # Agent execution completed (hooks were called during execution)
        print(f"Agent execution completed for ticket: {ticket_id}")

        # Update ticket status to completed
        update_ticket_status(notion_client, ticket_id, "Completed")

        return {
            "ticket_id": ticket_id,
            "session_id": session_id,
            "ticket_name": ticket_name,
            "status": "completed",
            "conversation_loaded": len(conversation_history) > 0,
        }

    except Exception as e:
        print(f"Error during agent execution: {e}")
        # Update ticket status to error
        update_ticket_status(notion_client, ticket_id, "Error")

        return {
            "ticket_id": ticket_id,
            "session_id": session_id,
            "ticket_name": ticket_name,
            "status": "error",
            "error": str(e),
            "conversation_loaded": len(conversation_history) > 0,
        }
