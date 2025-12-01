#!/usr/bin/env python3
"""Check what tickets exist in Notion database."""
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

notion_token = os.getenv("NOTION_TOKEN", "")
notion_db_id = os.getenv("NOTION_DB_ID", "")

if not notion_token or not notion_db_id:
    print("Error: Missing NOTION_TOKEN or NOTION_DB_ID")
    exit(1)

client = Client(auth=notion_token)

# Query database for all tickets
print(f"Querying database: {notion_db_id}\n")

try:
    # Get database to access data sources
    database = client.databases.retrieve(database_id=notion_db_id)
    data_sources = database.get("data_sources", [])

    if not data_sources:
        print("Warning: No data sources found in database")
        exit(1)

    data_source_id = data_sources[0]["id"]

    # Query all tickets
    response = client.data_sources.query(data_source_id=data_source_id)

    print(f"Found {len(response['results'])} tickets:\n")

    for page in response["results"]:
        props = page["properties"]

        # Get name
        name = "Unknown"
        if "Name" in props and props["Name"].get("title"):
            name = props["Name"]["title"][0]["text"]["content"]

        # Get status
        status = "Unknown"
        if "Status" in props and props["Status"].get("status"):
            status = props["Status"]["status"]["name"]

        # Get session ID
        session_id = "None"
        if "Session ID" in props and props["Session ID"].get("rich_text"):
            session_id = props["Session ID"]["rich_text"][0]["text"]["content"]

        print(f"- {name}")
        print(f"  Status: {status}")
        print(f"  Session ID: {session_id}")
        print(f"  Page ID: {page['id']}")
        print()

except Exception as e:
    print(f"Error querying database: {e}")
    import traceback
    traceback.print_exc()
