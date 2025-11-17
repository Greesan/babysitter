#!/usr/bin/env python3
import os, sys, uuid, json
from notion_client import Client

QUESTION = sys.argv[1]

# Generate a unique ticket ID and JSON file for this conversation
TICKET = str(uuid.uuid4())
TICKET_DIR = os.environ.get("CLAUDE_TICKET_DIR", "./tickets")
os.makedirs(TICKET_DIR, exist_ok=True)

CONV_FILE = os.path.join("./claude_conversations", f"{TICKET}.json")
os.makedirs(os.path.dirname(CONV_FILE), exist_ok=True)

# Save initial conversation reference
with open(f"{TICKET_DIR}/{TICKET}.conversation", "w") as f:
    f.write(CONV_FILE)

# Connect to Notion
notion = Client(auth=os.environ["NOTION_TOKEN"])
parent_db = os.environ["NOTION_TICKET_DB"]
session_id = os.environ.get("CLAUDE_SESSION_ID", "")

page = notion.pages.create(
    parent={"database_id": parent_db},
    properties={
        "Name": {"title": [{"text": {"content": f"Ticket {TICKET}"}}]},
        "Status": {"status": {"name": "Pending"}},
        "Ticket": {"rich_text": [{"text": {"content": TICKET}}]},
        "Session ID": {"rich_text": [{"text": {"content": session_id}}]}
    },
    children=[
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Claude Question"}}]}},
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"type": "text", "text": {"content": QUESTION}}]}},
        {"object": "block", "type": "heading_3",
         "heading_3": {"rich_text": [{"type": "text", "text": {"content": "Human Response"}}]}},
        {"object": "block", "type": "paragraph",
         "paragraph": {"rich_text": [{"type": "text", "text": {"content": ""}}]}},
        {"object": "block", "type": "to_do",
         "to_do": {"rich_text": [{"type": "text", "text": {"content": "Ready to submit (check when done)"}}],
                   "checked": False}}
    ]
)

# Save page ID
with open(f"{TICKET_DIR}/{TICKET}.page", "w") as f:
    f.write(page["id"])

# Tell Claude to suspend
print(json.dumps({
    "status": "SUSPEND",
    "ticket": TICKET,
    "conv_file": CONV_FILE
}))