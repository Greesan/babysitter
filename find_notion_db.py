#!/usr/bin/env python3
"""
Find your Notion database ID.
"""
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

notion_token = os.getenv("NOTION_TOKEN")

if not notion_token:
    print("❌ NOTION_TOKEN not found in .env")
    exit(1)

client = Client(auth=notion_token)

print("🔍 Searching for Notion databases...\n")

try:
    # Search for data sources (Notion databases)
    response = client.search(filter={"property": "object", "value": "data_source"})

    if not response.get("results"):
        print("❌ No databases found with this integration token")
        print("\n📝 Make sure:")
        print("   1. Your integration has access to the database")
        print("   2. You've shared the database with the integration")
        exit(1)

    print(f"✅ Found {len(response['results'])} database(s):\n")

    for i, db in enumerate(response["results"], 1):
        title = db.get("title", [{}])[0].get("plain_text", "Untitled")
        db_id = db["id"]

        print(f"{i}. {title}")
        print(f"   ID: {db_id}")
        print(f"   URL: https://notion.so/{db_id.replace('-', '')}")
        print()

    print("\n📝 Add to your .env file:")
    print(f"NOTION_DB_ID={response['results'][0]['id']}")

except Exception as e:
    print(f"❌ Error: {e}")
