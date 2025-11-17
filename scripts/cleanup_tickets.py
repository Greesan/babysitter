#!/usr/bin/env python3
"""
Cleanup utility for Notion tickets.

Usage:
  python cleanup_tickets.py --all          # Delete all pages in database
  python cleanup_tickets.py --pending      # Delete only Pending tickets
  python cleanup_tickets.py --local        # Clean up local ticket files
  python cleanup_tickets.py --both         # Clean both Notion and local
"""

import os
import sys
import argparse
from notion_client import Client

TICKET_DIR = os.environ.get("CLAUDE_TICKET_DIR", "./tickets")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_TICKET_DB = os.environ.get("NOTION_TICKET_DB")

notion = Client(auth=NOTION_TOKEN)

def query_database(filter_status=None):
    """Query the database for pages."""
    pages = []

    # First try local .page files
    for f in os.listdir(TICKET_DIR):
        if f.endswith(".page"):
            page_id = open(f"{TICKET_DIR}/{f}").read().strip()
            try:
                page = notion.pages.retrieve(page_id=page_id)
                if filter_status:
                    status = page["properties"].get("Status", {}).get("status", {}).get("name")
                    if status == filter_status:
                        pages.append((page_id, f))
                else:
                    pages.append((page_id, f))
            except Exception as e:
                print(f"Warning: Could not retrieve page {page_id}: {e}")

    # Also check archive directory
    archive_dir = f"{TICKET_DIR}/archive"
    if os.path.exists(archive_dir):
        for f in os.listdir(archive_dir):
            if f.endswith(".page"):
                page_id = open(f"{archive_dir}/{f}").read().strip()
                try:
                    page = notion.pages.retrieve(page_id=page_id)
                    if not page.get("archived", False):  # Only include non-archived pages
                        if filter_status:
                            status = page["properties"].get("Status", {}).get("status", {}).get("name")
                            if status == filter_status:
                                pages.append((page_id, f"archive/{f}"))
                        else:
                            pages.append((page_id, f"archive/{f}"))
                except Exception as e:
                    print(f"Warning: Could not retrieve page {page_id}: {e}")

    return pages

def delete_notion_pages(pages):
    """Archive (delete) pages in Notion."""
    count = 0
    for page_id, filename in pages:
        try:
            notion.pages.update(page_id=page_id, archived=True)
            print(f"✓ Archived Notion page: {page_id} ({filename})")
            count += 1
        except Exception as e:
            print(f"✗ Failed to archive {page_id}: {e}")
    return count

def clean_local_files():
    """Clean up local ticket files."""
    count = 0
    archive_dir = f"{TICKET_DIR}/archive"
    os.makedirs(archive_dir, exist_ok=True)

    for f in os.listdir(TICKET_DIR):
        if f.endswith((".page", ".question", ".conversation", ".done")):
            src = f"{TICKET_DIR}/{f}"
            dst = f"{archive_dir}/{f}"
            os.rename(src, dst)
            count += 1

    print(f"✓ Moved {count} local files to {archive_dir}")
    return count

def main():
    parser = argparse.ArgumentParser(description="Clean up Notion tickets")
    parser.add_argument("--all", action="store_true", help="Delete all tickets from Notion")
    parser.add_argument("--pending", action="store_true", help="Delete only Pending tickets")
    parser.add_argument("--local", action="store_true", help="Clean up local files only")
    parser.add_argument("--both", action="store_true", help="Clean both Notion and local")

    args = parser.parse_args()

    if not any([args.all, args.pending, args.local, args.both]):
        parser.print_help()
        sys.exit(1)

    # Clean Notion
    if args.all or args.both:
        print("Fetching all tickets from Notion...")
        pages = query_database()
        if pages:
            confirm = input(f"Delete {len(pages)} Notion pages? [y/N]: ")
            if confirm.lower() == 'y':
                deleted = delete_notion_pages(pages)
                print(f"\n✓ Deleted {deleted} Notion pages")
        else:
            print("No pages found to delete")

    elif args.pending:
        print("Fetching Pending tickets from Notion...")
        pages = query_database(filter_status="Pending")
        if pages:
            confirm = input(f"Delete {len(pages)} Pending Notion pages? [y/N]: ")
            if confirm.lower() == 'y':
                deleted = delete_notion_pages(pages)
                print(f"\n✓ Deleted {deleted} Pending pages")
        else:
            print("No Pending pages found")

    # Clean local
    if args.local or args.both:
        print("\nCleaning local ticket files...")
        clean_local_files()

    print("\n✓ Cleanup complete!")

if __name__ == "__main__":
    main()
