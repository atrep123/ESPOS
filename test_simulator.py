#!/usr/bin/env python3
"""Quick integration test for ESP32 Simulator"""

import time
import sys
import os

import pytest

# Add project root to path so esp32_sim_client can be imported
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from esp32_sim_client import ESP32SimulatorClient


def test_simulator(port: int = 8765) -> None:
    print(f"🧪 Testing simulator on port {port}...")
    
    with ESP32SimulatorClient(port=port) as client:
        if not client.connected:
            print("❌ Failed to connect to simulator")
            print(f"   Make sure simulator is running with: python sim_run.py --rpc-port {port}")
            pytest.skip(f"Simulator is not running on port {port}")
        
        print("✅ Connected to simulator")
        
        # Test 1: Background colors
        print("\n📊 Test 1: Background colors")
        colors = [
            ("Red", 255, 0, 0),
            ("Green", 0, 255, 0),
            ("Blue", 0, 0, 255),
            ("Yellow", 255, 255, 0),
            ("Magenta", 255, 0, 255),
            ("Cyan", 0, 255, 255),
        ]
        
        for name, r, g, b in colors:
            print(f"  Setting {name}...")
            client.set_bg_rgb(r, g, b)
            time.sleep(0.3)
        
        print("✅ Color test passed")
        
        # Test 2: Buttons
        print("\n📊 Test 2: Button clicks")
        for btn in ['A', 'B', 'C']:
            print(f"  Clicking button {btn}...")
            client.button_click(btn, 0.15)
            time.sleep(0.2)
        
        print("✅ Button test passed")
        
        # Test 3: Scenes
        print("\n📊 Test 3: Scene transitions")
        scene_names = ["HOME", "SETTINGS", "CUSTOM"]
        for scene_id, scene_name in enumerate(scene_names):
            print(f"  Switching to {scene_name}...")
            client.set_scene(scene_id)
            time.sleep(0.4)
        
        print("✅ Scene test passed")
        
        # Test 4: Hex colors
        print("\n📊 Test 4: Hex color codes")
        hex_colors = ["FF0000", "00FF00", "0000FF", "FFFF00"]
        for hex_color in hex_colors:
            print(f"  Setting #{hex_color}...")
            client.set_bg_hex(hex_color)
            time.sleep(0.2)
        
        print("✅ Hex color test passed")
        
        # Return to default
        client.set_bg_rgb(8, 8, 8)
        client.set_scene(0)
        
        print("\n🎉 All tests passed!")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    
    print("=" * 60)
    print("ESP32 Simulator Integration Test")
    print("=" * 60)
    
    success = test_simulator(port)
    sys.exit(0 if success else 1)
