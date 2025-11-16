#!/usr/bin/env python3
"""
ESP32 Hardware Bridge
Bidirectional sync between simulator and real ESP32 hardware
"""

import serial  # type: ignore
import socket
import json
import time
import threading
import queue
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class BridgeConfig:
    """Configuration for hardware bridge"""
    # Serial port settings
    serial_port: str = "COM3"
    baud_rate: int = 115200
    
    # Simulator connection
    sim_host: str = "127.0.0.1"
    sim_rpc_port: int = 8765
    
    # Bridge settings
    auto_reconnect: bool = True
    sync_interval: float = 0.1  # 100ms
    bidirectional: bool = True
    healthcheck_interval: float = 5.0
    reconnect_initial_delay: float = 0.5
    reconnect_max_delay: float = 8.0


class ESP32HardwareBridge:
    """Bridge between simulator and real ESP32 hardware"""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.serial_conn: Optional[serial.Serial] = None
        self.sim_socket: Optional[socket.socket] = None
        self.running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._last_activity_ts: float = 0.0
        
        # Event queues
        self.hw_to_sim_queue: queue.Queue = queue.Queue()
        self.sim_to_hw_queue: queue.Queue = queue.Queue()
        
        # State tracking
        self.last_hw_state: Dict[str, Any] = {}
        self.last_sim_state: Dict[str, Any] = {}
    
    def connect_serial(self) -> bool:
        """Connect to ESP32 via serial"""
        try:
            self.serial_conn = serial.Serial(
                port=self.config.serial_port,
                baudrate=self.config.baud_rate,
                timeout=0.1
            )
            print(f"✅ Connected to ESP32 on {self.config.serial_port}")
            return True
        except Exception as e:
            print(f"❌ Serial connection failed: {e}")
            return False
    
    def connect_simulator(self) -> bool:
        """Connect to simulator RPC"""
        try:
            self.sim_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sim_socket.connect((self.config.sim_host, self.config.sim_rpc_port))
            print(f"✅ Connected to simulator on {self.config.sim_host}:{self.config.sim_rpc_port}")
            return True
        except Exception as e:
            print(f"❌ Simulator connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect all connections"""
        if self.serial_conn:
            self.serial_conn.close()
            self.serial_conn = None
        
        if self.sim_socket:
            self.sim_socket.close()
            self.sim_socket = None
        
        print("🔌 Disconnected")
    
    def send_to_simulator(self, message: Dict[str, Any]) -> bool:
        """Send RPC message to simulator"""
        if not self.sim_socket:
            return False
        
        try:
            data = json.dumps(message) + "\n"
            self.sim_socket.sendall(data.encode('utf-8'))
            return True
        except Exception as e:
            print(f"⚠️ Failed to send to simulator: {e}")
            # Mark socket dead to trigger reconnect
            try:
                if self.sim_socket:
                    self.sim_socket.close()
            finally:
                self.sim_socket = None
            return False
    
    def send_to_hardware(self, command: str) -> bool:
        """Send command to ESP32"""
        if not self.serial_conn:
            return False
        
        try:
            self.serial_conn.write(f"{command}\n".encode('utf-8'))
            return True
        except Exception as e:
            print(f"⚠️ Failed to send to hardware: {e}")
            # Mark serial dead to trigger reconnect
            try:
                if self.serial_conn:
                    self.serial_conn.close()
            finally:
                self.serial_conn = None
            return False
    
    def read_from_hardware(self) -> Optional[str]:
        """Read line from ESP32"""
        if not self.serial_conn:
            return None
        
        try:
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                return line if line else None
            return None
        except Exception:
            return None
    
    def parse_hardware_message(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse message from ESP32 and convert to RPC format"""
        # Protocol: "STATE bg=0x0821 scene=0 btnA=0 btnB=0 btnC=0"
        if line.startswith("STATE"):
            parts = line.split()
            state = {}
            
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    
                    if key == 'bg':
                        # Convert hex to RGB565
                        state['bg'] = int(value, 16)
                    elif key == 'scene':
                        state['scene'] = int(value)
                    elif key.startswith('btn'):
                        btn_id = key[-1].upper()
                        pressed = bool(int(value))
                        state[f'btn{btn_id}'] = pressed
            
            return state
        
        # Button events: "BTN A 1" or "BTN A 0"
        elif line.startswith("BTN"):
            parts = line.split()
            if len(parts) == 3:
                btn_id = parts[1].upper()
                pressed = bool(int(parts[2]))
                return {
                    "method": "btn",
                    "id": btn_id,
                    "pressed": pressed
                }
        
        # Background color: "BG 0xFF0000" or "BG ff0000"
        elif line.startswith("BG"):
            parts = line.split()
            if len(parts) == 2:
                hex_color = parts[1].lstrip('#0x')
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return {
                    "method": "set_bg",
                    "rgb": [r, g, b]
                }
        
        # Scene change: "SCENE 1"
        elif line.startswith("SCENE"):
            parts = line.split()
            if len(parts) == 2:
                return {
                    "method": "scene",
                    "value": int(parts[1])
                }
        
        return None
    
    def hardware_reader_thread(self):
        """Thread to read from hardware and enqueue to simulator queue"""
        while self.running:
            if not self.serial_conn:
                time.sleep(0.1)
                continue
            line = self.read_from_hardware()
            if line:
                print(f"📥 HW → {line}")
                message = self.parse_hardware_message(line)
                if message:
                    self.hw_to_sim_queue.put(message)
                    self._last_activity_ts = time.time()
            time.sleep(0.01)  # 10ms poll
    
    def simulator_sender_thread(self):
        """Thread to send queued messages to simulator with retry"""
        backoff = self.config.reconnect_initial_delay
        while self.running:
            try:
                msg = self.hw_to_sim_queue.get(timeout=0.2)
            except queue.Empty:
                # Health-check ping
                now = time.time()
                if self.sim_socket and (now - self._last_activity_ts) > self.config.healthcheck_interval:
                    self.send_to_simulator({"method": "ping"})
                    self._last_activity_ts = now
                continue
            # Ensure simulator connected
            if not self.sim_socket:
                if not self.config.auto_reconnect:
                    continue
                if self.connect_simulator():
                    backoff = self.config.reconnect_initial_delay
                else:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, self.config.reconnect_max_delay)
                    self.hw_to_sim_queue.put(msg)
                    continue
            if not self.send_to_simulator(msg):
                # Failed send; requeue and try reconnect
                self.hw_to_sim_queue.put(msg)
                if self.config.auto_reconnect:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, self.config.reconnect_max_delay)
                continue
            backoff = self.config.reconnect_initial_delay
    
    def start(self) -> bool:
        """Start the bridge"""
        print("🌉 Starting ESP32 Hardware Bridge...")
        # Initial connections (best-effort)
        self.connect_serial()
        self.connect_simulator()
        self.running = True
        
        # Reader from hardware → queue
        threading.Thread(target=self.hardware_reader_thread, daemon=True).start()
        # Sender queue → simulator
        threading.Thread(target=self.simulator_sender_thread, daemon=True).start()
        
        # Optional future: sim→hw monitor could enqueue to sim_to_hw_queue and have similar sender
        print("🚀 Bridge running! Press Ctrl+C to stop...")
        return True
    
    def stop(self):
        """Stop the bridge"""
        print("\n⏹️ Stopping bridge...")
        self.running = False
        time.sleep(0.2)
        self.disconnect()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ESP32 Hardware Bridge')
    parser.add_argument('--serial-port', default='COM3', help='Serial port (e.g., COM3 or /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--sim-host', default='127.0.0.1', help='Simulator host')
    parser.add_argument('--sim-port', type=int, default=8765, help='Simulator RPC port')
    parser.add_argument('--no-bidirectional', action='store_true', help='Disable sim→hw sync')
    
    args = parser.parse_args()
    
    config = BridgeConfig(
        serial_port=args.serial_port,
        baud_rate=args.baud,
        sim_host=args.sim_host,
        sim_rpc_port=args.sim_port,
        bidirectional=not args.no_bidirectional
    )
    
    bridge = ESP32HardwareBridge(config)
    
    if bridge.start():
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            bridge.stop()
    else:
        print("❌ Bridge failed to start")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
