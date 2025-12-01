"""
Notion helper functions for Agent SDK integration.
Handles ticket queries, conversation state persistence, and status updates.
"""
import json
from typing import Optional, Dict, List, Any, Union
from notion_client import Client
from notion_client.errors import APIResponseError


def get_ticket_context(
    notion_client: Client, ticket_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch ticket context from Notion.

    Args:
        notion_client: Notion API client
        ticket_id: Notion page ID of the ticket

    Returns:
        Dict with ticket_name, status, session_id, conversation, turn_count
        or None if ticket not found
    """
    try:
        page = notion_client.pages.retrieve(page_id=ticket_id)

        properties = page["properties"]

        # Extract ticket name
        ticket_name = "Unknown"
        if "Name" in properties and properties["Name"].get("title"):
            ticket_name = properties["Name"]["title"][0]["text"]["content"]

        # Extract status
        status = "Pending"
        if "Status" in properties and properties["Status"].get("status"):
            status = properties["Status"]["status"]["name"]

        # Extract session ID
        session_id = None
        if "Session ID" in properties and properties["Session ID"].get("rich_text"):
            session_id = properties["Session ID"]["rich_text"][0]["text"]["content"]

        # Extract turn count
        turn_count = 0
        if "Turn Count" in properties and properties["Turn Count"].get("number") is not None:
            turn_count = properties["Turn Count"]["number"]

        # Load conversation from JSON property
        conversation = load_conversation_state(notion_client, ticket_id)

        return {
            "ticket_name": ticket_name,
            "status": status,
            "session_id": session_id,
            "conversation": conversation,
            "turn_count": turn_count,
        }

    except APIResponseError as e:
        # Handle both object_not_found and validation errors
        if e.code in ("object_not_found", "validation_error"):
            return None
        raise


def _dict_to_blocks(data: Union[Dict, List, Any], max_depth: int = 10, current_depth: int = 0) -> List[Dict]:
    """
    Recursively convert dict/list to nested Notion toggle blocks.

    Args:
        data: Dictionary, list, or primitive value to convert
        max_depth: Maximum nesting depth to prevent infinite recursion
        current_depth: Current recursion depth

    Returns:
        List of Notion block objects
    """
    if current_depth >= max_depth:
        # Reached max depth - return as paragraph
        return [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": str(data)[:2000]}}]  # Notion limit
            }
        }]

    if isinstance(data, dict):
        blocks = []
        for key, value in data.items():
            if isinstance(value, (dict, list)) and value:  # Non-empty nested structure
                # Create toggle block with nested children
                children = _dict_to_blocks(value, max_depth, current_depth + 1)
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"text": {"content": str(key)[:2000]}}],
                        "children": children
                    }
                })
            else:
                # Leaf value - create paragraph
                value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": f"{key}: {value_str[:1900]}"}}]
                    }
                })
        return blocks

    elif isinstance(data, list):
        # Convert list items to blocks
        blocks = []
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)) and item:
                children = _dict_to_blocks(item, max_depth, current_depth + 1)
                blocks.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"text": {"content": f"[{i}]"}}],
                        "children": children
                    }
                })
            else:
                item_str = json.dumps(item) if isinstance(item, (dict, list)) else str(item)
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": f"[{i}]: {item_str[:1900]}"}}]
                    }
                })
        return blocks

    else:
        # Primitive value - return as paragraph
        return [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": str(data)[:2000]}}]
            }
        }]


def append_conversation_message(
    notion_client: Client, ticket_id: str, message: Dict[str, Any]
) -> bool:
    """
    Append a single message to the conversation as nested toggle blocks.

    Args:
        notion_client: Notion API client
        ticket_id: Notion page ID
        message: Message dict to append

    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert message to nested blocks
        message_blocks = _dict_to_blocks({"message": message})

        # Append to page
        notion_client.blocks.children.append(
            block_id=ticket_id,
            children=message_blocks
        )

        # Update turn count
        turn = message.get("turn", 0)
        notion_client.pages.update(
            page_id=ticket_id,
            properties={"Turn Count": {"number": turn}}
        )

        return True

    except Exception as e:
        print(f"Error appending conversation message: {e}")
        return False


def save_conversation_state(
    notion_client: Client, ticket_id: str, conversation: List[Dict[str, Any]]
) -> bool:
    """
    Save conversation state by appending only new messages as blocks.

    NOTE: This is now append-only. Use append_conversation_message() instead
    for single message appends. This function is kept for backward compatibility
    and will append all messages in the list.

    Args:
        notion_client: Notion API client
        ticket_id: Notion page ID
        conversation: List of message dicts with role, content, timestamp, turn

    Returns:
        True if successful, False otherwise
    """
    try:
        # For now, just append the last message in the conversation
        # This maintains compatibility with existing code that calls save_conversation_state
        if conversation:
            last_message = conversation[-1]
            return append_conversation_message(notion_client, ticket_id, last_message)
        return True

    except Exception as e:
        print(f"Error saving conversation state: {e}")
        return False


def _blocks_to_dict(blocks: List[Dict], notion_client: Client) -> Union[Dict, List, str]:
    """
    Recursively parse Notion toggle blocks back to dict/list.

    Args:
        blocks: List of Notion block objects
        notion_client: Notion client for fetching nested children

    Returns:
        Parsed dict, list, or string value
    """
    if not blocks:
        return {}

    # Determine if this is a dict-like or list-like structure
    # List-like if all keys are "[0]", "[1]", etc.
    is_list = all(
        block.get("type") in ("toggle", "paragraph") and
        _get_block_text(block).strip().startswith("[") and
        "]" in _get_block_text(block).split(":")[0]
        for block in blocks
    )

    if is_list:
        # Parse as list
        result = []
        for block in blocks:
            block_type = block.get("type")
            text = _get_block_text(block)

            if block_type == "toggle":
                # Nested structure - recursively fetch children
                children_response = notion_client.blocks.children.list(block_id=block["id"])
                children = children_response.get("results", [])
                result.append(_blocks_to_dict(children, notion_client))
            elif block_type == "paragraph":
                # Leaf value - parse "[index]: value"
                if ": " in text:
                    _, value_str = text.split(": ", 1)
                    result.append(_parse_value(value_str))
                else:
                    result.append(text)
        return result
    else:
        # Parse as dict
        result = {}
        for block in blocks:
            block_type = block.get("type")
            text = _get_block_text(block)

            if block_type == "toggle":
                # Key is the toggle heading, value is nested structure
                key = text.strip()
                children_response = notion_client.blocks.children.list(block_id=block["id"])
                children = children_response.get("results", [])
                result[key] = _blocks_to_dict(children, notion_client)
            elif block_type == "paragraph":
                # Leaf value - parse "key: value"
                if ": " in text:
                    key, value_str = text.split(": ", 1)
                    result[key] = _parse_value(value_str)
                else:
                    # Just a text paragraph
                    result[text] = text
        return result


def _get_block_text(block: Dict) -> str:
    """Extract plain text from a Notion block."""
    block_type = block.get("type")
    if block_type == "toggle":
        rich_text = block.get("toggle", {}).get("rich_text", [])
    elif block_type == "paragraph":
        rich_text = block.get("paragraph", {}).get("rich_text", [])
    else:
        return ""

    if rich_text and len(rich_text) > 0:
        return rich_text[0].get("plain_text", "")
    return ""


def _parse_value(value_str: str) -> Any:
    """Parse a string value to appropriate Python type."""
    try:
        # Try parsing as JSON first (handles dicts, lists, numbers, bools, null)
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        # Return as string
        return value_str


def load_conversation_state(
    notion_client: Client, ticket_id: str
) -> List[Dict[str, Any]]:
    """
    Load conversation state from Notion blocks (new) or JSON property (legacy).

    Args:
        notion_client: Notion API client
        ticket_id: Notion page ID

    Returns:
        List of message dicts, or empty list if no conversation exists
    """
    try:
        # First, try loading from blocks (new format)
        blocks_response = notion_client.blocks.children.list(block_id=ticket_id)
        blocks = blocks_response.get("results", [])

        if blocks:
            # Parse blocks recursively - each top-level toggle is a separate message
            # Structure: Each message is wrapped as {"message": {...}}
            conversation = []

            for block in blocks:
                if block.get("type") == "toggle":
                    # Fetch children for this toggle
                    children_response = notion_client.blocks.children.list(block_id=block["id"])
                    children = children_response.get("results", [])

                    # Parse this message's nested structure
                    parsed_message = _blocks_to_dict(children, notion_client)

                    # Extract the actual message dict
                    if isinstance(parsed_message, dict):
                        # If it has a "message" key, unwrap it
                        if "message" in parsed_message:
                            conversation.append(parsed_message["message"])
                        else:
                            # Otherwise use the dict as-is
                            conversation.append(parsed_message)

            if conversation:
                return conversation

        # Fallback: Try loading from JSON property (legacy format)
        page = notion_client.pages.retrieve(page_id=ticket_id)
        properties = page["properties"]

        if "Conversation JSON" not in properties:
            return []

        conversation_prop = properties["Conversation JSON"]

        if not conversation_prop.get("rich_text"):
            return []

        conversation_json = conversation_prop["rich_text"][0]["text"]["content"]
        conversation = json.loads(conversation_json)

        return conversation

    except (json.JSONDecodeError, KeyError, IndexError):
        return []
    except Exception as e:
        print(f"Error loading conversation state: {e}")
        import traceback
        traceback.print_exc()
        return []


def update_ticket_status(
    notion_client: Client, ticket_id: str, status: str
) -> bool:
    """
    Update ticket status in Notion.

    Args:
        notion_client: Notion API client
        ticket_id: Notion page ID
        status: New status value

    Returns:
        True if successful, False otherwise
    """
    try:
        notion_client.pages.update(
            page_id=ticket_id, properties={"Status": {"status": {"name": status}}}
        )
        return True

    except APIResponseError as e:
        # Invalid status will cause validation error
        if "status" in str(e).lower():
            return False
        raise
    except Exception as e:
        print(f"Error updating ticket status: {e}")
        return False


def claim_pending_ticket(
    notion_client: Client, database_id: str
) -> Optional[Dict[str, Any]]:
    """
    Find and claim the oldest pending ticket.

    Args:
        notion_client: Notion API client
        database_id: Notion database ID to query

    Returns:
        Dict with ticket_id, session_id, ticket_name if found, None otherwise
    """
    try:
        # Get database to access data sources
        database = notion_client.databases.retrieve(database_id=database_id)
        data_sources = database.get("data_sources", [])

        if not data_sources:
            return None

        data_source_id = data_sources[0]["id"]

        # Query for pending tickets (oldest first)
        response = notion_client.data_sources.query(
            data_source_id=data_source_id,
            filter={"property": "Status", "status": {"equals": "Pending"}},
            sorts=[{"property": "Created time", "direction": "ascending"}],
        )

        results = response.get("results", [])

        if not results:
            return None

        # Get oldest pending ticket
        pending_ticket = results[0]
        ticket_id = pending_ticket["id"]

        # Claim by setting status to "Agent Planning"
        notion_client.pages.update(
            page_id=ticket_id,
            properties={"Status": {"status": {"name": "Agent Planning"}}},
        )

        # Extract session ID (or generate if missing)
        session_id_prop = pending_ticket["properties"].get("Session ID", {})
        if session_id_prop.get("rich_text"):
            session_id = session_id_prop["rich_text"][0]["text"]["content"]
        else:
            # Generate new session ID
            import uuid

            session_id = str(uuid.uuid4())
            notion_client.pages.update(
                page_id=ticket_id,
                properties={
                    "Session ID": {"rich_text": [{"text": {"content": session_id}}]}
                },
            )

        # Extract ticket name
        ticket_name = "Unknown"
        name_prop = pending_ticket["properties"].get("Name", {})
        if name_prop.get("title"):
            ticket_name = name_prop["title"][0]["text"]["content"]

        return {
            "ticket_id": ticket_id,
            "session_id": session_id,
            "ticket_name": ticket_name,
        }

    except Exception as e:
        print(f"Error claiming pending ticket: {e}")
        return None
