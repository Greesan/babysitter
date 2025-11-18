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

        # Query for non-Done tickets
        response = notion.databases.query(
            database_id=notion_db,
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
