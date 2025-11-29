"""
Notion helper functions for Agent SDK integration.
Handles ticket queries, conversation state persistence, and status updates.
"""
import json
from typing import Optional, Dict, List, Any
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


def save_conversation_state(
    notion_client: Client, ticket_id: str, conversation: List[Dict[str, Any]]
) -> bool:
    """
    Save conversation state to Notion as JSON.

    Args:
        notion_client: Notion API client
        ticket_id: Notion page ID
        conversation: List of message dicts with role, content, timestamp, turn

    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert conversation to JSON string
        conversation_json = json.dumps(conversation)

        # Calculate turn count (max turn number in conversation)
        turn_count = 0
        if conversation:
            turn_count = max(msg.get("turn", 0) for msg in conversation)

        # Update Notion page with conversation JSON and turn count
        notion_client.pages.update(
            page_id=ticket_id,
            properties={
                "Conversation JSON": {
                    "rich_text": [{"text": {"content": conversation_json}}]
                },
                "Turn Count": {"number": turn_count},
            },
        )

        return True

    except Exception as e:
        print(f"Error saving conversation state: {e}")
        return False


def load_conversation_state(
    notion_client: Client, ticket_id: str
) -> List[Dict[str, Any]]:
    """
    Load conversation state from Notion JSON property.

    Args:
        notion_client: Notion API client
        ticket_id: Notion page ID

    Returns:
        List of message dicts, or empty list if no conversation exists
    """
    try:
        page = notion_client.pages.retrieve(page_id=ticket_id)
        properties = page["properties"]

        # Check if Conversation JSON property exists
        if "Conversation JSON" not in properties:
            return []

        conversation_prop = properties["Conversation JSON"]

        # Check if property has content
        if not conversation_prop.get("rich_text"):
            return []

        # Parse JSON
        conversation_json = conversation_prop["rich_text"][0]["text"]["content"]
        conversation = json.loads(conversation_json)

        return conversation

    except (json.JSONDecodeError, KeyError, IndexError):
        return []
    except Exception as e:
        print(f"Error loading conversation state: {e}")
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
