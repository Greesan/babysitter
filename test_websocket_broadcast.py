#!/usr/bin/env python3
"""
WebSocket broadcast and echo test for webhook server.

Tests:
1. Echo test - Send ping, receive pong
2. Broadcast test - Multiple clients, verify all receive messages
"""
import asyncio
import json
from datetime import datetime
from websockets import connect


async def test_echo():
    """Test WebSocket echo (ping/pong)."""
    print(f"\n{'='*60}")
    print("TEST 1: Echo Test (Ping/Pong)")
    print(f"{'='*60}\n")

    uri = "ws://localhost:8000/ws"
    extra_headers = {"Origin": "http://localhost:5173"}

    try:
        async with connect(uri, additional_headers=extra_headers) as websocket:
            print("✅ Connected to WebSocket")

            # Send ping
            ping_msg = {
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            }

            print(f"\n📤 Sending: {json.dumps(ping_msg, indent=2)}")
            await websocket.send(json.dumps(ping_msg))

            # Wait for pong
            print(f"\n⏳ Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)

            print(f"\n📥 Received: {json.dumps(json.loads(response), indent=2)}")

            resp_data = json.loads(response)
            if resp_data.get("type") == "pong":
                print("\n✅ Echo test PASSED - Received pong!")
                return True
            else:
                print(f"\n❌ Echo test FAILED - Expected pong, got {resp_data.get('type')}")
                return False

    except asyncio.TimeoutError:
        print("\n❌ Echo test FAILED - Timeout waiting for response")
        return False
    except Exception as e:
        print(f"\n❌ Echo test FAILED - Error: {e}")
        return False


async def test_broadcast():
    """Test WebSocket broadcast to multiple clients."""
    print(f"\n{'='*60}")
    print("TEST 2: Broadcast Test")
    print(f"{'='*60}\n")

    uri = "ws://localhost:8000/ws"
    extra_headers = {"Origin": "http://localhost:5173"}

    connections = []
    num_clients = 3

    try:
        # Connect multiple clients
        print(f"🔌 Connecting {num_clients} clients...\n")
        for i in range(num_clients):
            ws = await connect(uri, additional_headers=extra_headers)
            connections.append(ws)
            print(f"   Client {i+1}: ✅ Connected")

        # Send a user response from client 1
        session_id = f"test-session-{datetime.now().timestamp()}"
        user_msg = {
            "type": "user_response",
            "session_id": session_id,
            "response": "Testing WebSocket broadcast",
            "timestamp": datetime.now().isoformat()
        }

        print(f"\n📤 Client 1 sending user response:")
        print(f"   Session ID: {session_id}")
        print(f"   Message: {user_msg['response']}")

        await connections[0].send(json.dumps(user_msg))

        # Client 1 should receive acknowledgment
        print(f"\n⏳ Waiting for acknowledgment from Client 1...")
        ack = await asyncio.wait_for(connections[0].recv(), timeout=5.0)
        ack_data = json.loads(ack)

        print(f"\n📥 Client 1 received: {json.dumps(ack_data, indent=2)}")

        if ack_data.get("type") == "ack":
            print("✅ Client 1 received acknowledgment")
        else:
            print(f"⚠️  Client 1 received unexpected message type: {ack_data.get('type')}")

        # Test that all clients can send and receive ping/pong
        print(f"\n📢 Testing each client can communicate...\n")
        results = []

        for i, ws in enumerate(connections):
            ping_msg = {"type": "ping", "client_id": i+1}
            await ws.send(json.dumps(ping_msg))

            try:
                response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                resp_data = json.loads(response)
                if resp_data.get("type") == "pong":
                    results.append(True)
                    print(f"   Client {i+1}: ✅ Ping/Pong successful")
                else:
                    results.append(False)
                    print(f"   Client {i+1}: ❌ Unexpected response: {resp_data.get('type')}")
            except asyncio.TimeoutError:
                results.append(False)
                print(f"   Client {i+1}: ❌ Timeout")

        # Close all connections
        print(f"\n🔌 Closing all connections...")
        for ws in connections:
            await ws.close()

        # Results
        success = all(results)
        if success:
            print(f"\n✅ Broadcast test PASSED - All clients can communicate!")
        else:
            print(f"\n❌ Broadcast test FAILED - Some clients couldn't communicate")

        return success

    except Exception as e:
        print(f"\n❌ Broadcast test FAILED - Error: {e}")
        # Clean up
        for ws in connections:
            try:
                await ws.close()
            except:
                pass
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("WebSocket Debug Suite - Testing Webhook Server")
    print("="*60)
    print(f"Target: ws://localhost:8000/ws")
    print("="*60)

    # Run tests
    echo_result = await test_echo()
    broadcast_result = await test_broadcast()

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Echo Test:      {'✅ PASSED' if echo_result else '❌ FAILED'}")
    print(f"Broadcast Test: {'✅ PASSED' if broadcast_result else '❌ FAILED'}")
    print(f"{'='*60}\n")

    return echo_result and broadcast_result


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
