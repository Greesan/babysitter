"""
Pytest configuration and shared fixtures for Agent SDK tests.
"""
import os
import pytest
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables
load_dotenv()


@pytest.fixture
def notion_token():
    """Get Notion API token from environment."""
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        pytest.skip("NOTION_TOKEN not set in environment")
    return token


@pytest.fixture
def notion_test_db():
    """Get test Notion database ID from environment."""
    db_id = os.environ.get("NOTION_TEST_DB")
    if not db_id:
        # Fall back to production DB for now (user will set up test DB)
        db_id = os.environ.get("NOTION_TICKET_DB")
        if not db_id:
            pytest.skip("NOTION_TEST_DB or NOTION_TICKET_DB not set")
    return db_id


@pytest.fixture
def notion_client(notion_token):
    """Create Notion client instance."""
    return Client(auth=notion_token)


@pytest.fixture
def test_ticket(notion_client, notion_test_db):
    """Create a test ticket and clean it up after the test."""
    # Create test ticket
    response = notion_client.pages.create(
        parent={"database_id": notion_test_db},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {"content": "Test Ticket - Agent SDK"}
                    }
                ]
            },
            "Status": {
                "status": {"name": "Pending"}
            }
        }
    )

    ticket_id = response["id"]

    yield ticket_id

    # Cleanup: Archive the test ticket
    try:
        notion_client.pages.update(
            page_id=ticket_id,
            archived=True
        )
    except Exception:
        pass  # Ignore cleanup errors
