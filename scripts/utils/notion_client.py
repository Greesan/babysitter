"""Notion client utilities for consistent client creation."""

import os
from notion_client import Client


def get_notion_client():
    """Get configured Notion client.

    Returns:
        Client: Authenticated Notion client

    Raises:
        ValueError: If NOTION_TOKEN environment variable is not set
    """
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN environment variable is not set")
    return Client(auth=token)
