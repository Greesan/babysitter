#!/usr/bin/env python3
"""
Direct test of agent execution to see errors clearly.
"""
import asyncio
import os
from dotenv import load_dotenv
from src.agent import run_agent_for_ticket, AgentConfig

load_dotenv()

async def main():
    """Run agent for a pending ticket."""
    notion_token = os.getenv("NOTION_TOKEN", "")
    notion_db_id = os.getenv("NOTION_DB_ID", "")

    if not notion_token or not notion_db_id:
        print("Error: Missing NOTION_TOKEN or NOTION_DB_ID")
        return

    config = AgentConfig(
        notion_token=notion_token,
        notion_db_id=notion_db_id,
        model="sonnet",
        max_turns=50,
    )

    print("Starting agent execution...")
    try:
        result = await run_agent_for_ticket(config)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
