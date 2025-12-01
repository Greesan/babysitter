#!/usr/bin/env python3
"""
Simple WebSocket test with proper headers.
"""
import asyncio
import json
from websockets import connect


async def test_websocket():
    """Test WebSocket connection with proper headers."""
    uri = "ws://localhost:8000/ws"

    # Add origin header to match CORS settings
    extra_headers = {
        "Origin": "http://localhost:5173"
    }

    print(f"🔌 Connecting to {uri}...")
    print(f"   Headers: {extra_headers}")

    try:
        async with connect(uri, additional_headers=extra_headers) as websocket:
            print("✅ Connected successfully!")

            # Keep connection alive for a bit and see if we receive anything
            print("\n⏳ Listening for messages for 5 seconds...")

            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received: {message}")
            except asyncio.TimeoutError:
                print("⏰ No messages received (this is expected - server just keeps connection alive)")

            print("\n✅ WebSocket connection working!")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_websocket())
    exit(0 if success else 1)
