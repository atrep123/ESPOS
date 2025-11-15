# ESP32OS

Developer workspace for ESP32 firmware and a fast terminal UI simulator.

## UI Simulator – Quick Start (Windows PowerShell)

- New window with auto-selected ports:

```powershell
./run_sim.ps1 -AutoPorts -Fps 144
```

- Same window (debug-friendly):

```powershell
./run_sim.ps1 -SameWindow -AutoPorts -Fps 144
```

- RPC control example (change background to red on chosen port):

```powershell
python .\simctl.py 8765 set_bg 255 0 0
```

For full simulator docs, options, RPC/UART usage, and troubleshooting see:

- `SIMULATOR_README.md`

## Project Layout

- `src/` firmware sources
- `sim_run.py` Python-based simulator (no C toolchain required)
- `run_sim.ps1` Windows launcher with `-AutoPorts` and `-SameWindow`
- `simctl.py` simple RPC client
