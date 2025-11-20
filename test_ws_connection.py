#!/usr/bin/env python3
"""Quick test of WebSocket backend server connection"""
import asyncio
import json

import websockets
import pytest

# This integration smoke test requires a running backend on localhost:8000.
# Skip during normal test runs to avoid async warnings and backend dependency.
pytest.skip("requires running WebSocket backend", allow_module_level=True)


async def test_connection():
    uri = "ws://localhost:8000/ws/projects/demo_project"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected!")
            
            # Wait for session_state message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"✓ Received: {data.get('type')}")
            print(f"  User ID: {data.get('user_id')}")
            print(f"  Users: {len(data.get('session', {}).get('users', []))}")
            print(f"  Widgets: {len(data.get('design', {}).get('widgets', []))}")
            
            # Send a test message
            test_msg = {
                'type': 'cursor',
                'x': 10,
                'y': 20
            }
            await websocket.send(json.dumps(test_msg))
            print("✓ Sent cursor update")
            
            print("\n✓ WebSocket backend is working correctly!")
            
    except asyncio.TimeoutError:
        print("✗ Timeout waiting for session_state message")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
