#!/usr/bin/env python3
"""
Multi-Window Simulator Manager
Launch and manage multiple simulator instances simultaneously
"""

import subprocess
import json
import time
import os
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class SimulatorInstance:
    """Configuration for single simulator instance"""
    name: str
    fps: int = 120
    width: int = 80
    height: int = 20
    rpc_port: int = 0  # 0 = auto
    uart_port: int = 0  # 0 = auto
    websocket_port: int = 0  # 0 = disabled
    x_offset: int = 0
    y_offset: int = 0
    auto_size: bool = False
    export_metrics: str = ""
    process: Optional[subprocess.Popen] = None
    pid: int = 0
    actual_rpc_port: int = 0
    actual_uart_port: int = 0


class MultiWindowManager:
    """Manage multiple simulator instances"""
    
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = workspace_dir
        self.instances: List[SimulatorInstance] = []
        self.session_file = os.path.join(workspace_dir, "multi_sim_session.json")
    
    def add_instance(self, instance: SimulatorInstance):
        """Add instance to manager"""
        self.instances.append(instance)
    
    def find_free_port(self, start: int = 8765) -> int:
        """Find free TCP port"""
        import socket
        for port in range(start, start + 100):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', port))
                sock.close()
                return port
            except OSError:
                continue
        return 0
    
    def launch_instance(self, instance: SimulatorInstance) -> bool:
        """Launch single simulator instance"""
        # Auto-assign ports if needed
        if instance.rpc_port == 0:
            instance.actual_rpc_port = self.find_free_port(8765)
        else:
            instance.actual_rpc_port = instance.rpc_port
        
        if instance.uart_port == 0:
            instance.actual_uart_port = self.find_free_port(instance.actual_rpc_port + 1)
        else:
            instance.actual_uart_port = instance.uart_port
        
        # Build command
        cmd = [
            sys.executable,
            os.path.join(self.workspace_dir, "sim_run.py"),
            "--fps", str(instance.fps),
            "--width", str(instance.width),
            "--height", str(instance.height),
            "--rpc-port", str(instance.actual_rpc_port),
            "--uart-port", str(instance.actual_uart_port)
        ]
        
        if instance.websocket_port > 0:
            cmd.extend(["--websocket-port", str(instance.websocket_port)])
        
        if instance.auto_size:
            cmd.append("--auto-size")
        
        if instance.export_metrics:
            metrics_file = f"{instance.name}_{instance.export_metrics}"
            cmd.extend(["--export-metrics", metrics_file])
        
        # Launch in new window (Windows Terminal or PowerShell)
        try:
            if os.name == 'nt':
                # Windows
                if os.system('where wt.exe >nul 2>&1') == 0:
                    # Windows Terminal available
                    full_cmd = ['wt.exe', 'new-tab', '--title', instance.name] + cmd
                else:
                    # Fallback to PowerShell
                    full_cmd = ['powershell', '-NoExit', '-Command'] + [' '.join(cmd)]
                
                process = subprocess.Popen(
                    full_cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if 'wt.exe' not in full_cmd else 0
                )
            else:
                # Linux/Mac - use xterm or gnome-terminal
                full_cmd = ['xterm', '-title', instance.name, '-e'] + cmd
                process = subprocess.Popen(full_cmd)
            
            instance.process = process
            instance.pid = process.pid
            
            print(f"✅ Launched '{instance.name}' (PID: {instance.pid}, RPC: {instance.actual_rpc_port}, UART: {instance.actual_uart_port})")
            
            # Wait a bit for simulator to start and write ports file
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to launch '{instance.name}': {e}")
            return False
    
    def launch_all(self) -> int:
        """Launch all instances"""
        print(f"🚀 Launching {len(self.instances)} simulator instances...\n")
        
        success_count = 0
        for instance in self.instances:
            if self.launch_instance(instance):
                success_count += 1
                time.sleep(0.5)  # Stagger launches
        
        print(f"\n✅ {success_count}/{len(self.instances)} instances launched")
        
        # Save session
        self.save_session()
        
        return success_count
    
    def stop_all(self):
        """Stop all running instances"""
        print("\n⏹️ Stopping all instances...")
        
        for instance in self.instances:
            if instance.process:
                try:
                    instance.process.terminate()
                    instance.process.wait(timeout=2)
                    print(f"✅ Stopped '{instance.name}'")
                except Exception as e:
                    print(f"⚠️ Failed to stop '{instance.name}': {e}")
                    try:
                        instance.process.kill()
                    except Exception:
                        pass
    
    def save_session(self):
        """Save current session to file"""
        session_data = {
            "instances": [
                {
                    "name": inst.name,
                    "fps": inst.fps,
                    "width": inst.width,
                    "height": inst.height,
                    "rpc_port": inst.actual_rpc_port,
                    "uart_port": inst.actual_uart_port,
                    "websocket_port": inst.websocket_port,
                    "pid": inst.pid
                }
                for inst in self.instances
            ]
        }
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
            print(f"💾 Session saved to {self.session_file}")
        except Exception as e:
            print(f"⚠️ Failed to save session: {e}")
    
    def load_session(self) -> bool:
        """Load session from file"""
        if not os.path.exists(self.session_file):
            return False
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            print(f"📂 Loaded session from {self.session_file}")
            print(f"Found {len(session_data['instances'])} instances")
            
            return True
        except Exception as e:
            print(f"⚠️ Failed to load session: {e}")
            return False
    
    def list_instances(self):
        """List all managed instances"""
        print("\n📋 Simulator Instances:")
        print("=" * 80)
        
        for i, inst in enumerate(self.instances, 1):
            status = "🟢 Running" if inst.process and inst.process.poll() is None else "🔴 Stopped"
            print(f"{i}. {inst.name}")
            print(f"   Status: {status}")
            print(f"   Size: {inst.width}×{inst.height} @ {inst.fps} FPS")
            print(f"   RPC: {inst.actual_rpc_port}, UART: {inst.actual_uart_port}")
            if inst.websocket_port:
                print(f"   WebSocket: {inst.websocket_port}")
            print()


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Window Simulator Manager')
    parser.add_argument('--preset', choices=['dev', 'demo', 'test'], help='Launch preset configuration')
    parser.add_argument('--list', action='store_true', help='List running instances')
    
    args = parser.parse_args()
    
    manager = MultiWindowManager()
    
    if args.preset == 'dev':
        # Development preset: 2 instances
        print("🔧 Development Preset: Main + Test")
        
        manager.add_instance(SimulatorInstance(
            name="Main",
            fps=120,
            width=100,
            height=24,
            rpc_port=8765,
            uart_port=7777,
            websocket_port=9999,
            export_metrics="metrics.csv"
        ))
        
        manager.add_instance(SimulatorInstance(
            name="Test",
            fps=60,
            width=80,
            height=20,
            rpc_port=8766,
            uart_port=7778
        ))
    
    elif args.preset == 'demo':
        # Demo preset: 3 different sizes
        print("🎨 Demo Preset: Small, Medium, Large")
        
        manager.add_instance(SimulatorInstance(
            name="Small",
            fps=60,
            width=60,
            height=16,
            rpc_port=8765
        ))
        
        manager.add_instance(SimulatorInstance(
            name="Medium",
            fps=90,
            width=80,
            height=20,
            rpc_port=8766
        ))
        
        manager.add_instance(SimulatorInstance(
            name="Large",
            fps=120,
            width=100,
            height=24,
            rpc_port=8767,
            websocket_port=9999
        ))
    
    elif args.preset == 'test':
        # Test preset: 4 instances for automated testing
        print("🧪 Test Preset: 4 Test Instances")
        
        for i in range(4):
            manager.add_instance(SimulatorInstance(
                name=f"Test_{i+1}",
                fps=120,
                width=80,
                height=20,
                export_metrics=f"test_{i+1}_metrics.csv"
            ))
    
    else:
        print("Usage: python multi_window_manager.py --preset [dev|demo|test]")
        return 1
    
    # Launch all instances
    count = manager.launch_all()
    
    if count > 0:
        print("\n📊 Instance Overview:")
        manager.list_instances()
        
        print("\n💡 Tips:")
        print("  - Use test_simulator.py <port> to control each instance")
        print("  - Check multi_sim_session.json for session details")
        print("  - Press Ctrl+C to stop all instances")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            manager.stop_all()
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
