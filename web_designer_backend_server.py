import asyncio
import json
import signal
import sys
import uuid

import websockets

PORT = 8000

sessions = {}  # project_id -> {websocket -> user_data}
project_designs = {}  # project_id -> design data
shutdown_event = None


async def handler(websocket):
    """Handle WebSocket connection for a project session"""
    try:
        # Compatibility: websockets 13+ does not pass path argument
        path = websocket.request.path

        # Parse project from path: /ws/projects/<project>
        if not path.startswith('/ws/projects/'):
            await websocket.send(json.dumps({'error': 'Invalid path'}))
            return
        project_id = path.split('/')[-1]
        print(f"[DEBUG] New connection to project: {project_id}")
        
        # Initialize project session if needed
        if project_id not in sessions:
            sessions[project_id] = {}
            project_designs[project_id] = {'widgets': []}
            print(f"[DEBUG] Created new project session: {project_id}")
        
        # Generate user ID for this connection
        user_id = str(uuid.uuid4())
        user_name = f"User-{user_id[:4]}"
        print(f"[DEBUG] User {user_name} ({user_id}) connecting")
        
        # Add to session
        sessions[project_id][websocket] = {
            'id': user_id,
            'name': user_name
        }
        
        # Send session_state to new client
        session_users = [{'id': data['id'], 'name': data['name']} 
                         for data in sessions[project_id].values()]
        
        session_state_msg = {
            'type': 'session_state',
            'user_id': user_id,
            'design': project_designs[project_id],
            'session': {
                'users': session_users
            }
        }
        print(f"[DEBUG] Sending session_state: {len(session_users)} users, {len(project_designs[project_id]['widgets'])} widgets")
        await websocket.send(json.dumps(session_state_msg))
        print("[DEBUG] Session state sent successfully")
        
        # Notify others about new user
        user_joined_msg = {
            'type': 'user_joined',
            'user': {'id': user_id, 'name': user_name}
        }
        for client in list(sessions[project_id].keys()):
            if client != websocket:
                try:
                    await client.send(json.dumps(user_joined_msg))
                except Exception as e:
                    print(f"[ERROR] Failed to send user_joined: {e}")
        
        try:
            async for message in websocket:
                # Parse and handle message
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    # Update design state for persistence
                    if msg_type == 'widget_add':
                        project_designs[project_id]['widgets'].append(data['widget'])
                    elif msg_type == 'widget_update':
                        # Update existing widget
                        for w in project_designs[project_id]['widgets']:
                            if w['id'] == data['widget_id']:
                                w.update(data.get('changes', {}))
                                break
                    elif msg_type == 'widget_delete':
                        # Remove widget
                        project_designs[project_id]['widgets'] = [
                            w for w in project_designs[project_id]['widgets']
                            if w['id'] != data['widget_id']
                        ]
                    
                except Exception as e:
                    print(f"[ERROR] Failed to parse message: {e}")
                
                # Broadcast to all clients in the same project
                for client in list(sessions[project_id].keys()):
                    if client != websocket:
                        try:
                            await client.send(message)
                        except Exception as e:
                            print(f"[ERROR] Failed to broadcast: {e}")
                            
        except websockets.exceptions.ConnectionClosed:
            print(f"[DEBUG] Connection closed for user {user_name}")
        finally:
            # Notify others about user leaving
            user_left_msg = {
                'type': 'user_left',
                'user_id': user_id
            }
            for client in list(sessions[project_id].keys()):
                if client != websocket:
                    try:
                        await client.send(json.dumps(user_left_msg))
                    except Exception as e:
                        print(f"[ERROR] Failed to send user_left: {e}")
            
            # Remove from session
            if websocket in sessions[project_id]:
                del sessions[project_id][websocket]
                print(f"[DEBUG] User {user_name} removed from session")
                
    except Exception as e:
        print(f"[ERROR] Handler exception: {e}")
        import traceback
        traceback.print_exc()


async def main():
    global shutdown_event
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        print("\nShutting down gracefully...")
        shutdown_event.set()
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"Backend server running on ws://localhost:{PORT}/ws/projects/<project>")
    sys.stdout.flush()
    
    # Retry logic for binding port
    max_retries = 5
    for i in range(max_retries):
        try:
            async with websockets.serve(handler, 'localhost', PORT, reuse_address=True):
                await shutdown_event.wait()
            break
        except OSError as e:
            if e.errno == 10048:  # Address already in use
                print(f"[WARNING] Port {PORT} is busy (attempt {i+1}/{max_retries}). Waiting 1s...")
                await asyncio.sleep(1)
            else:
                raise e
    else:
        print(f"[ERROR] Could not bind to port {PORT} after {max_retries} attempts.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

