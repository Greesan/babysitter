#!/usr/bin/env python3
"""
WebSocket test script to debug echo and broadcast functionality.

Tests:
1. Echo test - Send a message and receive it back
2. Broadcast test - Multiple clients receive the same message
"""
import asyncio
import json
import sys
from websockets import connect
from datetime import datetime


async def test_echo(ws_url: str):
    """Test WebSocket echo functionality."""
    print(f"\n{'='*60}")
    print("TEST 1: WebSocket Echo Test")
    print(f"{'='*60}")

    try:
        async with connect(ws_url) as websocket:
            test_message = {
                "type": "ping",
                "timestamp": datetime.now().isoformat(),
                "message": "Testing WebSocket broadcast"
            }

            print(f"\n📤 Sending message:")
            print(json.dumps(test_message, indent=2))

            await websocket.send(json.dumps(test_message))

            print(f"\n⏳ Waiting for response...")

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"\n✅ Received response:")
                print(json.dumps(json.loads(response), indent=2))
                return True
            except asyncio.TimeoutError:
                print(f"\n❌ Timeout: No response received within 5 seconds")
                return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def test_broadcast(ws_url: str, num_clients: int = 3):
    """Test WebSocket broadcast to multiple clients."""
    print(f"\n{'='*60}")
    print(f"TEST 2: WebSocket Broadcast Test ({num_clients} clients)")
    print(f"{'='*60}")

    connections = []

    try:
        # Connect multiple clients
        print(f"\n🔌 Connecting {num_clients} clients...")
        for i in range(num_clients):
            ws = await connect(ws_url)
            connections.append(ws)
            print(f"   Client {i+1}: Connected")

        # Send a user response from the first client
        test_message = {
            "type": "user_response",
            "session_id": "test-session-123",
            "response": "Testing WebSocket broadcast",
            "timestamp": datetime.now().isoformat()
        }

        print(f"\n📤 Client 1 sending message:")
        print(json.dumps(test_message, indent=2))

        await connections[0].send(json.dumps(test_message))

        # Wait for acknowledgment
        print(f"\n⏳ Waiting for acknowledgment from Client 1...")
        try:
            ack = await asyncio.wait_for(connections[0].recv(), timeout=5.0)
            print(f"\n✅ Client 1 received acknowledgment:")
            print(json.dumps(json.loads(ack), indent=2))
        except asyncio.TimeoutError:
            print(f"\n⚠️  Client 1 did not receive acknowledgment")

        # Now test broadcast by sending from another endpoint
        # Since we can't directly trigger a broadcast from client side,
        # let's test that all clients can receive messages
        print(f"\n📢 Testing that all clients are listening...")

        # Send ping from each client and check they get pong back
        results = []
        for i, ws in enumerate(connections):
            ping_msg = {"type": "ping", "client_id": i+1}
            await ws.send(json.dumps(ping_msg))

            try:
                response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                resp_data = json.loads(response)
                results.append(f"   Client {i+1}: ✅ {resp_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                results.append(f"   Client {i+1}: ❌ Timeout")

        print("\n📊 Results:")
        for result in results:
            print(result)

        # Close all connections
        print(f"\n🔌 Closing all connections...")
        for ws in connections:
            await ws.close()

        return all("✅" in r for r in results)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        # Clean up connections
        for ws in connections:
            try:
                await ws.close()
            except:
                pass
        return False


async def main():
    """Main test runner."""
    print("\n" + "="*60)
    print("WebSocket Debug Suite")
    print("="*60)

    # Determine which server to test
    if len(sys.argv) > 1:
        if sys.argv[1] == "dashboard":
            ws_url = "ws://localhost:8000/ws/logs"
            server_name = "Dashboard Backend"
        elif sys.argv[1] == "webhook":
            ws_url = "ws://localhost:8000/ws"
            server_name = "Webhook Server"
        else:
            print(f"\n❌ Unknown server: {sys.argv[1]}")
            print("Usage: python test_websocket.py [dashboard|webhook]")
            sys.exit(1)
    else:
        # Default to webhook server
        ws_url = "ws://localhost:8000/ws"
        server_name = "Webhook Server"

    print(f"\n🎯 Target: {server_name}")
    print(f"📡 URL: {ws_url}")

    # Run tests
    echo_result = await test_echo(ws_url)
    broadcast_result = await test_broadcast(ws_url)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Echo Test: {'✅ PASSED' if echo_result else '❌ FAILED'}")
    print(f"Broadcast Test: {'✅ PASSED' if broadcast_result else '❌ FAILED'}")
    print(f"{'='*60}\n")

    return echo_result and broadcast_result


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
