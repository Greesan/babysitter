#!/usr/bin/env python3
"""
Debug WebSocket ping/pong behavior.
"""
import asyncio
import json
from websockets import connect


async def test_immediate_ping():
    """Test sending ping immediately after connecting."""
    print("\n" + "="*60)
    print("TEST: Immediate Ping After Connect")
    print("="*60 + "\n")

    uri = "ws://localhost:8000/ws"
    extra_headers = {"Origin": "http://localhost:5173"}

    try:
        async with connect(uri, additional_headers=extra_headers) as websocket:
            print("✅ Connected")

            # Send ping immediately
            ping_msg = {"type": "ping"}
            print(f"\n📤 Sending: {json.dumps(ping_msg)}")
            await websocket.send(json.dumps(ping_msg))

            # Wait for response
            print("⏳ Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ Received: {response}")
                resp_data = json.loads(response)

                if resp_data.get("type") == "pong":
                    print("✅ Got pong response!")
                    return True
                else:
                    print(f"❌ Unexpected response type: {resp_data.get('type')}")
                    return False

            except asyncio.TimeoutError:
                print("❌ Timeout waiting for response")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ping_with_delay():
    """Test sending ping after a small delay."""
    print("\n" + "="*60)
    print("TEST: Ping With Small Delay")
    print("="*60 + "\n")

    uri = "ws://localhost:8000/ws"
    extra_headers = {"Origin": "http://localhost:5173"}

    try:
        async with connect(uri, additional_headers=extra_headers) as websocket:
            print("✅ Connected")

            # Wait a moment
            await asyncio.sleep(0.1)

            # Send ping
            ping_msg = {"type": "ping"}
            print(f"\n📤 Sending: {json.dumps(ping_msg)}")
            await websocket.send(json.dumps(ping_msg))

            # Wait for response
            print("⏳ Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ Received: {response}")
                resp_data = json.loads(response)

                if resp_data.get("type") == "pong":
                    print("✅ Got pong response!")
                    return True
                else:
                    print(f"❌ Unexpected response type: {resp_data.get('type')}")
                    return False

            except asyncio.TimeoutError:
                print("❌ Timeout waiting for response")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run debug tests."""
    print("\n" + "="*60)
    print("WebSocket Ping/Pong Debug Suite")
    print("="*60)

    result1 = await test_immediate_ping()
    result2 = await test_ping_with_delay()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Immediate Ping: {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"Delayed Ping:   {'✅ PASSED' if result2 else '❌ FAILED'}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
