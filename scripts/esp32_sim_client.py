#!/usr/bin/env python3
"""
ESP32 Simulator Client Library
Simple Python library for controlling the ESP32 UI Simulator via RPC
"""

import socket
import json
import time
from typing import Tuple, Optional


class ESP32SimulatorClient:
    """Client for controlling ESP32 UI Simulator via RPC protocol"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        """
        Initialize client connection
        
        Args:
            host: Simulator host address (default: 127.0.0.1)
            port: RPC port (default: 8765)
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        Connect to simulator
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from simulator"""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
            self.connected = False
    
    def _send_rpc(self, message: dict) -> bool:
        """
        Send RPC message to simulator
        
        Args:
            message: JSON-serializable dictionary
            
        Returns:
            True if send successful
        """
        if not self.connected or not self.socket:
            return False
        
        try:
            data = json.dumps(message) + "\n"
            self.socket.sendall(data.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            self.connected = False
            return False
    
    def set_bg_rgb(self, r: int, g: int, b: int) -> bool:
        """
        Set background color using RGB values
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
            
        Returns:
            True if successful
        """
        return self._send_rpc({
            "method": "set_bg",
            "rgb": [r, g, b]
        })
    
    def set_bg_rgb565(self, value: int) -> bool:
        """
        Set background color using RGB565 value
        
        Args:
            value: RGB565 color value (0x0000-0xFFFF)
            
        Returns:
            True if successful
        """
        return self._send_rpc({
            "method": "set_bg",
            "rgb565": value
        })
    
    def set_bg_hex(self, hex_color: str) -> bool:
        """
        Set background color using hex string
        
        Args:
            hex_color: Hex color string (e.g., "FF0000" or "#FF0000")
            
        Returns:
            True if successful
        """
        hex_color = hex_color.lstrip('#')
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return self.set_bg_rgb(r, g, b)
        except Exception:
            return False
    
    def button_press(self, button: str) -> bool:
        """
        Press button
        
        Args:
            button: Button ID ('A', 'B', or 'C')
            
        Returns:
            True if successful
        """
        return self._send_rpc({
            "method": "btn",
            "id": button.upper(),
            "pressed": True
        })
    
    def button_release(self, button: str) -> bool:
        """
        Release button
        
        Args:
            button: Button ID ('A', 'B', or 'C')
            
        Returns:
            True if successful
        """
        return self._send_rpc({
            "method": "btn",
            "id": button.upper(),
            "pressed": False
        })
    
    def button_click(self, button: str, duration: float = 0.1) -> bool:
        """
        Click button (press and release with delay)
        
        Args:
            button: Button ID ('A', 'B', or 'C')
            duration: Press duration in seconds (default: 0.1)
            
        Returns:
            True if successful
        """
        if not self.button_press(button):
            return False
        time.sleep(duration)
        return self.button_release(button)
    
    def set_scene(self, scene: int) -> bool:
        """
        Change scene
        
        Args:
            scene: Scene number (0=HOME, 1=SETTINGS, 2=CUSTOM)
            
        Returns:
            True if successful
        """
        return self._send_rpc({
            "method": "scene",
            "value": max(0, min(2, scene))
        })
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Convenience functions for quick one-off commands

def quick_connect(port: int = 8765) -> Optional[ESP32SimulatorClient]:
    """
    Quick connect to simulator running on localhost
    
    Args:
        port: RPC port (default: 8765)
        
    Returns:
        Connected client or None if failed
    """
    client = ESP32SimulatorClient(port=port)
    if client.connect():
        return client
    return None


def send_command(port: int, command: str, *args) -> bool:
    """
    Send single command to simulator
    
    Args:
        port: RPC port
        command: Command name (set_bg, btn, scene)
        *args: Command arguments
        
    Returns:
        True if successful
    """
    with ESP32SimulatorClient(port=port) as client:
        if not client.connected:
            return False
        
        if command == "set_bg":
            if len(args) == 3:
                return client.set_bg_rgb(int(args[0]), int(args[1]), int(args[2]))
            elif len(args) == 1:
                return client.set_bg_hex(str(args[0]))
        elif command == "btn":
            if len(args) >= 1:
                btn_id = str(args[0])
                action = str(args[1]).lower() if len(args) > 1 else "click"
                if action == "press":
                    return client.button_press(btn_id)
                elif action == "release":
                    return client.button_release(btn_id)
                else:
                    return client.button_click(btn_id)
        elif command == "scene":
            if len(args) >= 1:
                return client.set_scene(int(args[0]))
    
    return False


# Example usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("ESP32 Simulator Client Library")
        print("\nUsage:")
        print("  python esp32_sim_client.py <port> <command> [args...]")
        print("\nCommands:")
        print("  set_bg <r> <g> <b>     - Set RGB background")
        print("  set_bg <hex>           - Set hex background (e.g., FF0000)")
        print("  btn <A|B|C> [action]   - Button action (press/release/click)")
        print("  scene <0|1|2>          - Change scene")
        print("\nExamples:")
        print("  python esp32_sim_client.py 8765 set_bg 255 0 0")
        print("  python esp32_sim_client.py 8765 set_bg FF0000")
        print("  python esp32_sim_client.py 8765 btn A click")
        print("  python esp32_sim_client.py 8765 scene 1")
        print("\nContext manager example:")
        print("  with ESP32SimulatorClient(port=8765) as client:")
        print("      client.set_bg_rgb(255, 0, 0)")
        print("      client.button_click('A')")
        sys.exit(1)
    
    port = int(sys.argv[1])
    command = sys.argv[2]
    args = sys.argv[3:]
    
    success = send_command(port, command, *args)
    sys.exit(0 if success else 1)
