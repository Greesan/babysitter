#!/usr/bin/env python3
"""Test blocks-based conversation storage."""
import os
from dotenv import load_dotenv
from notion_client import Client
from src.notion_helper import append_conversation_message, load_conversation_state

load_dotenv()

def main():
    """Test appending and loading messages with blocks."""
    notion_token = os.getenv("NOTION_TOKEN", "")

    if not notion_token:
        print("Error: Missing NOTION_TOKEN")
        return

    client = Client(auth=notion_token)

    # Create a test ticket
    notion_db_id = os.getenv("NOTION_DB_ID", "")

    print("Creating test ticket...")
    test_page = client.pages.create(
        parent={"database_id": notion_db_id},
        properties={
            "Name": {"title": [{"text": {"content": "Blocks Storage Test"}}]},
            "Status": {"status": {"name": "Pending"}}
        }
    )

    ticket_id = test_page["id"]
    print(f"Created ticket: {ticket_id}\n")

    # Test message 1: Simple assistant message
    message1 = {
        "role": "assistant",
        "content": "Testing blocks-based storage",
        "timestamp": "2025-11-29T22:30:00Z",
        "turn": 1
    }

    print("Appending message 1...")
    success = append_conversation_message(client, ticket_id, message1)
    print(f"Append result: {success}\n")

    # Test message 2: Tool use
    message2 = {
        "type": "tool_use",
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo Hello Blocks",
            "description": "Test command"
        },
        "tool_output": {
            "stdout": "Hello Blocks",
            "stderr": "",
            "interrupted": False
        },
        "timestamp": "2025-11-29T22:30:05Z",
        "turn": 2
    }

    print("Appending message 2 (tool use)...")
    success = append_conversation_message(client, ticket_id, message2)
    print(f"Append result: {success}\n")

    # Load conversation back
    print("Loading conversation...")
    conversation = load_conversation_state(client, ticket_id)

    print(f"Loaded {len(conversation)} messages:\n")

    import json
    for i, msg in enumerate(conversation, 1):
        print(f"Message {i}:")
        print(json.dumps(msg, indent=2))
        print()

    # Verify round-trip
    print("\n=== Verification ===")
    if len(conversation) >= 2:
        print(f"✅ Expected 2 messages, got {len(conversation)}")

        msg1 = conversation[0]
        if msg1.get("role") == "assistant" and msg1.get("turn") == 1:
            print("✅ Message 1 matches")
        else:
            print(f"❌ Message 1 mismatch: {msg1}")

        msg2 = conversation[1]
        if msg2.get("type") == "tool_use" and msg2.get("tool_name") == "Bash":
            print("✅ Message 2 matches")
        else:
            print(f"❌ Message 2 mismatch: {msg2}")
    else:
        print(f"❌ Expected 2 messages, got {len(conversation)}")

    print(f"\nTest ticket ID: {ticket_id}")
    print("You can view it in Notion to see the blocks structure!")

if __name__ == "__main__":
    main()
