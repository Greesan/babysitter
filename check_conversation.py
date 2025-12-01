#!/usr/bin/env python3
"""Check conversation for a specific ticket."""
import os
import sys
from dotenv import load_dotenv
from src.notion_helper import load_conversation_state
from notion_client import Client

load_dotenv()

if len(sys.argv) < 2:
    print("Usage: python check_conversation.py <ticket_id>")
    exit(1)

ticket_id = sys.argv[1]

notion_token = os.getenv("NOTION_TOKEN", "")
if not notion_token:
    print("Error: Missing NOTION_TOKEN")
    exit(1)

client = Client(auth=notion_token)

print(f"Loading conversation for ticket: {ticket_id}\n")

conversation = load_conversation_state(client, ticket_id)

print(f"Found {len(conversation)} messages:\n")

for i, msg in enumerate(conversation, 1):
    role = msg.get("role", "unknown")
    content = msg.get("content", "")
    timestamp = msg.get("timestamp", "")
    turn = msg.get("turn", "")

    print(f"[{i}] {role} (turn {turn}) @ {timestamp}")

    # Print the full message for debugging
    import json
    print(json.dumps(msg, indent=2))
    print()
