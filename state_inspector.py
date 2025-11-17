#!/usr/bin/env python3
"""
Real-time State Inspector and Debugger for ESP32 Simulator
Monitor UIState, events, timing, and internal metrics
"""

import socket
import json
import time
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


@dataclass
class StateSnapshot:
    """Snapshot of simulator state"""
    timestamp: float
    scene: int
    bg_color: int
    button_states: Dict[str, bool]
    fps: float
    frame_count: int
    event_queue_size: int
    render_time_ms: float
    custom_data: Dict[str, Any] = field(default_factory=dict)


class StateInspector:
    """Real-time state inspector with history"""
    
    def __init__(self, host: str = 'localhost', port: int = 5556):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.connected = False
        
        # State history
        self.snapshots: deque = deque(maxlen=1000)
        self.events: deque = deque(maxlen=100)
        
        # Statistics
        self.stats = {
            'total_events': 0,
            'total_frames': 0,
            'avg_fps': 0.0,
            'avg_render_ms': 0.0,
            'peak_render_ms': 0.0,
        }
    
    def connect(self) -> bool:
        """Connect to simulator RPC port"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            print(f"✓ Connected to simulator at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from simulator"""
        if self.sock:
            self.sock.close()
            self.sock = None
        self.connected = False
    
    def send_command(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Send JSON-RPC command and get response"""
        if not self.connected:
            return None
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        
        try:
            self.sock.sendall(json.dumps(request).encode() + b'\n')
            
            # Read response
            response_data = b''
            while b'\n' not in response_data:
                chunk = self.sock.recv(4096)
                if not chunk:
                    return None
                response_data += chunk
            
            response = json.loads(response_data.decode())
            return response.get('result')
        
        except Exception as e:
            print(f"✗ Command failed: {e}")
            return None
    
    def get_state(self) -> Optional[StateSnapshot]:
        """Get current simulator state"""
        result = self.send_command("get_state")
        
        if result:
            snapshot = StateSnapshot(
                timestamp=time.time(),
                scene=result.get('scene', 0),
                bg_color=result.get('bg_color', 0),
                button_states=result.get('buttons', {}),
                fps=result.get('fps', 0.0),
                frame_count=result.get('frame_count', 0),
                event_queue_size=result.get('event_queue_size', 0),
                render_time_ms=result.get('render_time_ms', 0.0),
                custom_data=result.get('custom', {})
            )
            
            self.snapshots.append(snapshot)
            self.update_statistics(snapshot)
            
            return snapshot
        
        return None
    
    def update_statistics(self, snapshot: StateSnapshot):
        """Update running statistics"""
        self.stats['total_frames'] += 1
        
        # Running average FPS
        alpha = 0.1  # Smoothing factor
        self.stats['avg_fps'] = (1 - alpha) * self.stats['avg_fps'] + alpha * snapshot.fps
        
        # Running average render time
        self.stats['avg_render_ms'] = (1 - alpha) * self.stats['avg_render_ms'] + alpha * snapshot.render_time_ms
        
        # Peak render time
        if snapshot.render_time_ms > self.stats['peak_render_ms']:
            self.stats['peak_render_ms'] = snapshot.render_time_ms
    
    def log_event(self, event_type: str, data: Dict):
        """Log simulator event"""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'data': data
        }
        self.events.append(event)
        self.stats['total_events'] += 1
    
    def get_recent_snapshots(self, count: int = 10) -> List[StateSnapshot]:
        """Get recent state snapshots"""
        return list(self.snapshots)[-count:]
    
    def get_recent_events(self, count: int = 20) -> List[Dict]:
        """Get recent events"""
        return list(self.events)[-count:]
    
    def export_to_json(self, filename: str):
        """Export state history to JSON"""
        data = {
            'snapshots': [
                {
                    'timestamp': s.timestamp,
                    'scene': s.scene,
                    'bg_color': f"0x{s.bg_color:04x}",
                    'button_states': s.button_states,
                    'fps': s.fps,
                    'frame_count': s.frame_count,
                    'event_queue_size': s.event_queue_size,
                    'render_time_ms': s.render_time_ms,
                    'custom': s.custom_data
                }
                for s in self.snapshots
            ],
            'events': list(self.events),
            'statistics': self.stats
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📊 State history exported: {filename}")
    
    def print_current_state(self):
        """Print current state to console"""
        if not self.snapshots:
            print("No state data available")
            return
        
        snapshot = self.snapshots[-1]
        
        print("\n" + "="*60)
        print("CURRENT STATE")
        print("="*60)
        print(f"Time:        {datetime.fromtimestamp(snapshot.timestamp).strftime('%H:%M:%S.%f')[:-3]}")
        print(f"Scene:       {snapshot.scene}")
        print(f"Background:  0x{snapshot.bg_color:04x}")
        print(f"Buttons:     {snapshot.button_states}")
        print(f"FPS:         {snapshot.fps:.1f}")
        print(f"Frame:       {snapshot.frame_count}")
        print(f"Queue size:  {snapshot.event_queue_size}")
        print(f"Render time: {snapshot.render_time_ms:.2f} ms")
        
        if snapshot.custom_data:
            print("\nCustom data:")
            for key, value in snapshot.custom_data.items():
                print(f"  {key}: {value}")
        
        print("\n" + "="*60)
        print("STATISTICS")
        print("="*60)
        print(f"Total frames:    {self.stats['total_frames']}")
        print(f"Total events:    {self.stats['total_events']}")
        print(f"Average FPS:     {self.stats['avg_fps']:.1f}")
        print(f"Avg render:      {self.stats['avg_render_ms']:.2f} ms")
        print(f"Peak render:     {self.stats['peak_render_ms']:.2f} ms")
        print("="*60 + "\n")
    
    def print_recent_events(self, count: int = 10):
        """Print recent events"""
        events = self.get_recent_events(count)
        
        if not events:
            print("No events recorded")
            return
        
        print("\n" + "="*60)
        print(f"RECENT EVENTS (last {len(events)})")
        print("="*60)
        
        for event in events:
            timestamp = datetime.fromtimestamp(event['timestamp']).strftime('%H:%M:%S.%f')[:-3]
            print(f"[{timestamp}] {event['type']}")
            for key, value in event['data'].items():
                print(f"  {key}: {value}")
        
        print("="*60 + "\n")
    
    def monitor_loop(self, interval: float = 1.0):
        """Continuous monitoring loop"""
        print("🔍 State Inspector - Monitoring Mode")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                snapshot = self.get_state()
                
                if snapshot:
                    # Clear screen (optional)
                    # print("\033[2J\033[H")
                    
                    self.print_current_state()
                    time.sleep(interval)
                else:
                    print("⚠ Failed to get state, retrying...")
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n✓ Monitoring stopped")


def create_cli_interface():
    """CLI interface for state inspector"""
    print("╔═══════════════════════════════════════╗")
    print("║   ESP32 State Inspector               ║")
    print("╚═══════════════════════════════════════╝")
    print()
    
    # Parse command line
    host = 'localhost'
    port = 5556
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    inspector = StateInspector(host, port)
    
    print(f"Connecting to {host}:{port}...")
    if not inspector.connect():
        print("Failed to connect. Make sure simulator is running with RPC enabled.")
        return
    
    print("\nCommands:")
    print("  state     - Show current state")
    print("  events    - Show recent events")
    print("  stats     - Show statistics")
    print("  monitor   - Start continuous monitoring")
    print("  export <file> - Export history to JSON")
    print("  quit      - Exit")
    print()
    
    while True:
        try:
            cmd = input("> ").strip().split()
            
            if not cmd:
                continue
            
            action = cmd[0].lower()
            
            if action == 'quit':
                break
            
            elif action == 'state':
                inspector.get_state()
                inspector.print_current_state()
            
            elif action == 'events':
                count = int(cmd[1]) if len(cmd) > 1 else 10
                inspector.print_recent_events(count)
            
            elif action == 'stats':
                print("\n" + "="*60)
                print("STATISTICS")
                print("="*60)
                for key, value in inspector.stats.items():
                    print(f"{key:20s}: {value}")
                print("="*60 + "\n")
            
            elif action == 'monitor':
                interval = float(cmd[1]) if len(cmd) > 1 else 1.0
                inspector.monitor_loop(interval)
            
            elif action == 'export':
                if len(cmd) < 2:
                    print("Usage: export <filename>")
                    continue
                inspector.export_to_json(cmd[1])
            
            else:
                print(f"Unknown command: {action}")
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    inspector.disconnect()
    print("Disconnected.")


if __name__ == '__main__':
    create_cli_interface()
