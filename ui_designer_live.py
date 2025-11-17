#!/usr/bin/env python3
"""
Live Preview Server for UI Designer
Auto-refreshes browser when design JSON changes
"""
import os
import sys
import time
import json
import asyncio
import webbrowser
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import websockets
from websockets.server import serve

# Simple in-memory client registry
clients = set()

class DesignFileHandler(FileSystemEventHandler):
    """Watches for JSON file changes and triggers reload."""
    def __init__(self, json_path: str, html_path: str, ws_port: int):
        self.json_path = Path(json_path).resolve()
        self.html_path = Path(html_path).resolve()
        self.last_modified = 0
        self.ws_port = ws_port
        
    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path).resolve()
        if path == self.json_path:
            # Debounce rapid file writes
            mtime = path.stat().st_mtime
            if mtime - self.last_modified < 0.1:
                return
            self.last_modified = mtime
            print(f"[{time.strftime('%H:%M:%S')}] Detected change: {path.name}")
            self._regenerate_html()
            asyncio.run(self._notify_clients())
    
    def _regenerate_html(self):
        """Re-export HTML from JSON and re-inject live script."""
        try:
            import subprocess
            preview_script = Path(__file__).parent / 'ui_designer_preview.py'
            cmd = [
                sys.executable, str(preview_script),
                '--headless-preview',
                '--in-json', str(self.json_path),
                '--out-html', str(self.html_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                try:
                    content = create_live_html_template(self.html_path, self.ws_port)
                    self.html_path.write_text(content, encoding='utf-8')
                except Exception as inject_err:
                    print(f"  [WARN] Live script injection failed: {inject_err}")
                print(f"  [OK] Regenerated: {self.html_path.name}")
            else:
                print(f"  [ERROR] Export failed: {result.stderr[:200]}")
        except Exception as e:
            print(f"  [ERROR] Error regenerating HTML: {e}")
    
    async def _notify_clients(self):
        """Send reload signal to all connected browsers."""
        if clients:
            message = json.dumps({"type": "reload"})
            websockets.broadcast(clients, message)
            print(f"  -> Notified {len(clients)} client(s)")


async def websocket_handler(websocket):
    """Handle WebSocket connections from browser."""
    clients.add(websocket)
    client_addr = websocket.remote_address
    print(f"[{time.strftime('%H:%M:%S')}] Client connected: {client_addr[0]}:{client_addr[1]}")
    try:
        async for message in websocket:
            # Echo back for debugging
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.remove(websocket)
        print(f"[{time.strftime('%H:%M:%S')}] Client disconnected: {client_addr[0]}:{client_addr[1]}")


async def start_websocket_server(port: int):
    """Start WebSocket server for browser notifications."""
    async with serve(websocket_handler, "localhost", port):
        print(f"WebSocket server running on ws://localhost:{port}")
        await asyncio.Future()  # run forever


def create_live_html_template(original_html: Path, ws_port: int) -> str:
    """Inject WebSocket client into HTML."""
    try:
        content = original_html.read_text(encoding='utf-8')
    except:
        content = "<html><body><h1>Waiting for design...</h1></body></html>"
    
    ws_script = f"""
<script>
(function() {{
    const ws = new WebSocket('ws://localhost:{ws_port}');
    ws.onmessage = (event) => {{
        const data = JSON.parse(event.data);
        if (data.type === 'reload') {{
            console.log('Design updated, reloading...');
            location.reload();
        }}
    }};
    ws.onerror = () => console.warn('WebSocket connection failed');
    ws.onclose = () => console.log('WebSocket closed');
}})();
</script>
"""
    
    if '</body>' in content:
        content = content.replace('</body>', f'{ws_script}</body>')
    else:
        content += ws_script
    
    return content


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Live preview server for UI Designer')
    parser.add_argument('--json', required=True, help='Design JSON file to watch')
    parser.add_argument('--html', help='HTML output path (default: json_name.html)')
    parser.add_argument('--port', type=int, default=8080, help='HTTP server port (default: 8080)')
    parser.add_argument('--ws-port', type=int, default=8765, help='WebSocket port (default: 8765)')
    parser.add_argument('--no-browser', action='store_true', help='Don\'t auto-open browser')
    args = parser.parse_args()
    
    json_path = Path(args.json).resolve()
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)
    
    html_path = Path(args.html) if args.html else json_path.with_suffix('.live.html')
    html_path = html_path.resolve()
    
    print(f"""
====================================================================
 UI Designer Live Preview Server
====================================================================
 Watching: {json_path.name}
 Output:   {html_path.name}
 WS Port:  {args.ws_port}
====================================================================
""")
    
    # Initial HTML generation
    handler = DesignFileHandler(str(json_path), str(html_path), args.ws_port)
    handler._regenerate_html()
    
    # Start file watcher
    observer = Observer()
    observer.schedule(handler, path=str(json_path.parent), recursive=False)
    observer.start()
    
    # Open browser
    if not args.no_browser:
        url = f"file:///{html_path.as_posix()}"
        print(f"\nOpening browser: {url}\n")
        webbrowser.open(url)
    
    print("Press Ctrl+C to stop\n")
    
    try:
        # Run WebSocket server
        asyncio.run(start_websocket_server(args.ws_port))
    except KeyboardInterrupt:
        print("\n\n[OK] Shutting down...")
        observer.stop()
        observer.join()
        sys.exit(0)


if __name__ == '__main__':
    main()
