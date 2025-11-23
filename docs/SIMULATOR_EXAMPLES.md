# ESP32 UI Simulator - Examples

## Example 1: Basic Usage with Config File

```powershell
# Create custom config
$config = @{
    fps = 120
    width = 100
    height = 24
    "rpc-port" = 8765
    "uart-port" = 7777
    "full-redraw-interval" = 300
} | ConvertTo-Json

$config | Out-File -Encoding UTF8 my_sim_config.json

# Run with config
python sim_run.py --config my_sim_config.json
```

## Example 2: Auto-sized UI with Metrics Export

```powershell
# Auto-detect terminal size and export performance metrics
python sim_run.py --auto-size --export-metrics metrics.csv --fps 120
```

## Example 3: WebSocket Remote Viewer

```powershell
# Terminal 1: Start simulator with WebSocket server
python sim_run.py --websocket-port 9999 --rpc-port 8765

# Open ui_sim/remote_viewer.html in browser
# Browser will connect to ws://localhost:9999
```

## Example 4: Record and Playback Session

```powershell
# Record a session
python sim_run.py --record session.json --rpc-port 8765

# ... interact with simulator or send RPC commands ...

# Later: Playback the recorded session
python sim_run.py --playback session.json
```

## Example 5: Using Python Client Library

```python
from esp32_sim_client import ESP32SimulatorClient

# Context manager usage
with ESP32SimulatorClient(port=8765) as client:
    # Set red background
    client.set_bg_rgb(255, 0, 0)
    
    # Click button A
    client.button_click('A')
    
    # Change to settings scene
    client.set_scene(1)
    
    # Set hex color
    client.set_bg_hex('00FF00')
```

## Example 6: Using C Client Library

```c
#include "esp32_sim_client.h"

int main() {
    esp32_sim_init();
    
    esp32_sim_client_t client;
    if (esp32_sim_connect(&client, "127.0.0.1", 8765)) {
        // Set background to red
        esp32_sim_set_bg_rgb(&client, 255, 0, 0);
        
        // Click button A
        esp32_sim_button_click(&client, 'A', 100);
        
        // Change scene
        esp32_sim_set_scene(&client, 1);
        
        esp32_sim_disconnect(&client);
    }
    
    esp32_sim_cleanup();
    return 0;
}
```

## Example 7: Scripted Testing

```jsonc
// test_script.json
[
  {"at_ms": 0, "method": "set_bg", "rgb": [255, 0, 0]},
  {"at_ms": 500, "method": "btn", "id": "A", "pressed": true},
  {"at_ms": 600, "method": "btn", "id": "A", "pressed": false},
  {"at_ms": 1000, "method": "scene", "value": 1},
  {"at_ms": 1500, "method": "set_bg", "rgb": [0, 255, 0]},
  {"at_ms": 2000, "method": "btn", "id": "B", "pressed": true},
  {"at_ms": 2100, "method": "btn", "id": "B", "pressed": false}
]
```

```powershell
# Run script
python sim_run.py --script test_script.json --fps 60
```

## Example 8: High-Performance Testing

```powershell
# Maximum performance with metrics export
python sim_run.py `
    --fps 240 `
    --no-diff `
    --full-redraw-interval 0 `
    --export-metrics perf_test.csv `
    --rpc-port 8765

# Analyze metrics in Excel or Python
python -c "import pandas as pd; df = pd.read_csv('perf_test.csv'); print(df.describe())"
```

## Example 9: PowerShell Launcher with All Features

```powershell
# Full-featured launch
.\run_sim.ps1 `
    -Fps 120 `
    -AutoPorts `
    -AutoSize `
    -ExportMetrics "metrics.csv" `
    -WebSocketPort 9999 `
    -Record "session.json" `
    -SameWindow
```

## Example 10: Automated Integration Test

```python
import time
from esp32_sim_client import ESP32SimulatorClient

def run_integration_test():
    with ESP32SimulatorClient(port=8765) as client:
        if not client.connected:
            print("Failed to connect to simulator")
            return False
        
        # Test 1: Background colors
        test_colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
        ]
        
        for r, g, b in test_colors:
            client.set_bg_rgb(r, g, b)
            time.sleep(0.2)
        
        # Test 2: Button sequences
        for btn in ['A', 'B', 'C']:
            client.button_click(btn, 0.1)
            time.sleep(0.2)
        
        # Test 3: Scene transitions
        for scene in [0, 1, 2, 0]:
            client.set_scene(scene)
            time.sleep(0.3)
        
        print("Integration test passed!")
        return True

if __name__ == '__main__':
    # Start simulator first:
    # python sim_run.py --rpc-port 8765
    
    run_integration_test()
```

## Example 11: COM Port Bridge (Hardware-in-the-Loop)

```powershell
# Install pyserial
pip install pyserial

# Connect simulator to real ESP32 via COM port
python sim_run.py --com-port COM3 --baud 115200 --fps 60

# ESP32 can now send commands like:
# Serial.println("set_bg ff0000");
```

## Example 12: Multi-Instance Testing

```powershell
# Terminal 1: Instance A
python sim_run.py --rpc-port 8765 --uart-port 7777 --width 80 --height 20

# Terminal 2: Instance B
python sim_run.py --rpc-port 8766 --uart-port 7778 --width 100 --height 24

# Terminal 3: Control both
python esp32_sim_client.py 8765 set_bg FF0000
python esp32_sim_client.py 8766 set_bg 00FF00
```

## Performance Tips

1. **High FPS with minimal CPU**: Use `--full-redraw-interval 300` (default)
2. **Debugging flickering**: Use `--no-diff` to force full redraw
3. **Terminal size issues**: Use `--auto-size` for automatic detection
4. **Remote monitoring**: Use `--websocket-port 9999` with web viewer
5. **Profiling**: Use `--export-metrics` and analyze CSV in Excel/Python
