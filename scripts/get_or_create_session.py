#!/usr/bin/env python3
"""
Get or create a session ID for the Ralph Wiggum loop.
- Checks Notion for active tickets (Status != "Done")
- If found: Returns session ID from newest active ticket
- If not found: Generates new UUID and returns it
"""
import os
import sys
import uuid
from notion_client import Client

def main():
    # Load environment
    notion_token = os.environ.get("NOTION_TOKEN")
    notion_db = os.environ.get("NOTION_TICKET_DB")

    if not notion_token or not notion_db:
        print("Error: NOTION_TOKEN and NOTION_TICKET_DB must be set", file=sys.stderr)
        sys.exit(1)

    # Query Notion for active tickets
    try:
        notion = Client(auth=notion_token)

        # Get data source ID from database (databases.query deprecated as of 2025-09-03)
        database = notion.databases.retrieve(database_id=notion_db)
        data_sources = database.get("data_sources", [])

        if not data_sources:
            print(f"Warning: No data sources found in database", file=sys.stderr)
            new_session = str(uuid.uuid4())
            print(f"CREATING new session: {new_session}", file=sys.stderr)
            print(new_session)
            return

        data_source_id = data_sources[0]["id"]  # Use first data source for single-source DBs

        # FIRST: Check for Pending tickets to claim
        response = notion.data_sources.query(
            data_source_id=data_source_id,
            filter={
                "property": "Status",
                "status": {
                    "equals": "Pending"
                }
            },
            sorts=[
                {
                    "property": "Created time",
                    "direction": "ascending"
                }
            ]
        )

        pending_results = response.get("results", [])

        if pending_results:
            # Found Pending ticket - claim it immediately
            pending_ticket = pending_results[0]
            page_id = pending_ticket["id"]

            print(f"Found Pending ticket, claiming it...", file=sys.stderr)

            # Claim by setting status to "Agent Planning"
            notion.pages.update(
                page_id=page_id,
                properties={"Status": {"status": {"name": "Agent Planning"}}}
            )

            session_id_prop = pending_ticket["properties"].get("Session ID", {})
            if session_id_prop.get("rich_text"):
                session_id = session_id_prop["rich_text"][0]["text"]["content"]
            else:
                # No session ID yet, create one and update
                session_id = str(uuid.uuid4())
                notion.pages.update(
                    page_id=page_id,
                    properties={"Session ID": {"rich_text": [{"text": {"content": session_id}}]}}
                )

            ticket_name = pending_ticket["properties"].get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "unknown")

            print(f"CLAIMED Pending ticket: {session_id}", file=sys.stderr)
            print(f"  Ticket: {ticket_name}", file=sys.stderr)
            print(f"  Status changed: Pending → Agent Planning", file=sys.stderr)
            print(session_id)  # Output to stdout for capture
            return

        # SECOND: No Pending tickets, check for active tickets we're already working on
        response = notion.data_sources.query(
            data_source_id=data_source_id,
            filter={
                "property": "Status",
                "status": {
                    "does_not_equal": "Done"
                }
            },
            sorts=[
                {
                    "property": "Turn Count",
                    "direction": "descending"
                }
            ]
        )

        results = response.get("results", [])

        if results:
            # Found active ticket(s) - use newest (first result after sort)
            newest_ticket = results[0]
            session_id_prop = newest_ticket["properties"].get("Session ID", {})

            if session_id_prop.get("rich_text"):
                session_id = session_id_prop["rich_text"][0]["text"]["content"]
                ticket_name = newest_ticket["properties"].get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "unknown")

                print(f"REUSING existing session: {session_id}", file=sys.stderr)
                print(f"  Ticket: {ticket_name}", file=sys.stderr)
                print(f"  Active tickets found: {len(results)}", file=sys.stderr)
                print(session_id)  # Output to stdout for capture
                return

        # No active tickets found - create new session
        new_session = str(uuid.uuid4())
        print(f"CREATING new session: {new_session}", file=sys.stderr)
        print(f"  No active tickets found", file=sys.stderr)
        print(new_session)  # Output to stdout for capture

    except Exception as e:
        print(f"Error querying Notion: {e}", file=sys.stderr)
        print(f"Generating fallback session ID", file=sys.stderr)
        print(str(uuid.uuid4()))  # Fallback
        sys.exit(1)

if __name__ == "__main__":
    main()
