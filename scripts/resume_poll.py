#!/usr/bin/env python3
import os, subprocess
from notion_client import Client

TICKET_DIR = os.environ.get("CLAUDE_TICKET_DIR", "./tickets")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
notion = Client(auth=os.environ["NOTION_TOKEN"])

for f in os.listdir(TICKET_DIR):
    if not f.endswith(".page"):
        continue
    ticket = f.split(".")[0]
    page_id = open(f"{TICKET_DIR}/{ticket}.page").read().strip()
    conv_file = open(f"{TICKET_DIR}/{ticket}.conversation").read().strip()

    # Get page properties to retrieve Session ID
    try:
        page = notion.pages.retrieve(page_id=page_id)
    except Exception as e:
        print(f"Warning: Could not retrieve page {ticket}: {e}")
        # Archive stale ticket file
        archive_dir = f"{TICKET_DIR}/archive"
        os.makedirs(archive_dir, exist_ok=True)
        for ext in [".page", ".question", ".conversation"]:
            src = f"{TICKET_DIR}/{ticket}{ext}"
            if os.path.exists(src):
                os.rename(src, f"{archive_dir}/{ticket}{ext}")
        print(f"  Archived stale ticket files for {ticket}")
        continue

    # Check if page is archived
    if page.get("archived", False):
        print(f"Skipping archived page {ticket}")
        # Archive local ticket files
        archive_dir = f"{TICKET_DIR}/archive"
        os.makedirs(archive_dir, exist_ok=True)
        for ext in [".page", ".question", ".conversation"]:
            src = f"{TICKET_DIR}/{ticket}{ext}"
            if os.path.exists(src):
                os.rename(src, f"{archive_dir}/{ticket}{ext}")
        print(f"  Archived local ticket files for {ticket}")
        continue

    session_id_prop = page["properties"].get("Session ID", {})
    session_id = ""
    if session_id_prop.get("rich_text"):
        session_id = session_id_prop["rich_text"][0]["text"]["content"]

    if not session_id:
        print(f"Warning: No Session ID found for ticket {ticket}, skipping")
        continue

    # Read human response from Notion blocks
    try:
        blocks = notion.blocks.children.list(block_id=page_id)["results"]
    except Exception as e:
        print(f"Warning: Could not read blocks for ticket {ticket}: {e}")
        continue
    human_answer = ""
    checkbox_ready = False
    found = False

    for block in blocks:
        if block["type"] == "heading_3" and any("Human Response" in t["text"]["content"] for t in block["heading_3"].get("rich_text", [])):
            found = True
            continue
        if found and block["type"] == "paragraph":
            human_answer += "\n".join(t["text"]["content"] for t in block["paragraph"].get("rich_text", [])) + "\n"
        if found and block["type"] == "to_do":
            checkbox_ready = block["to_do"].get("checked", False)

    # Only resume if both answer exists AND checkbox is checked
    if human_answer.strip() and checkbox_ready:
        print(f"Resuming Claude for ticket {ticket} with session ID {session_id}")
        try:
            subprocess.run(
                ["claude", "-p", "--resume", session_id, "--mcp-config", "mcp-config.json", "--dangerously-skip-permissions"],
                input=human_answer.strip().encode(),
                check=True,
                cwd=PROJECT_ROOT  # Run from project root to find mcp-config.json
            )
            os.rename(f"{TICKET_DIR}/{ticket}.page", f"{TICKET_DIR}/{ticket}.done")
            print(f"Ticket {ticket} resumed and marked done.")
        except subprocess.CalledProcessError as e:
            print(f"Error resuming ticket {ticket}: {e}")
