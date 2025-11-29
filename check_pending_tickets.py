#!/usr/bin/env python3
"""
Quick script to check if there are pending tickets in your Notion database.
"""
import os
from dotenv import load_dotenv
from src.notion_helper import claim_pending_ticket
from notion_client import Client

load_dotenv()

def main():
    print("🔍 Checking for pending tickets in Notion...\n")

    notion_token = os.getenv("NOTION_TOKEN")
    notion_db_id = os.getenv("NOTION_DB_ID")

    if not notion_token or not notion_db_id:
        print("❌ Error: NOTION_TOKEN or NOTION_DB_ID not set in .env")
        return

    client = Client(auth=notion_token)

    # Try to claim a pending ticket (this is what the webhook does)
    print(f"Database ID: {notion_db_id}\n")

    result = claim_pending_ticket(client, notion_db_id)

    if result:
        print("✅ Found a pending ticket!")
        print(f"   Ticket ID: {result['ticket_id']}")
        print(f"   Name: {result['ticket_name']}")
        print(f"   Session ID: {result['session_id']}")
        print(f"\n   Status has been set to 'Agent Planning'")
        print(f"   (Reset it to 'Pending' if you want to test again)")
    else:
        print("❌ No pending tickets found!\n")
        print("📝 To test the agent, you need to:")
        print("   1. Go to your Notion database")
        print("   2. Create a new page/ticket")
        print("   3. Set Status to 'Pending'")
        print("   4. Add a task description")
        print("\nExample ticket:")
        print("   Title: Test Agent Task")
        print("   Status: Pending")
        print("   Description: List all Python files in src/")

if __name__ == "__main__":
    main()
