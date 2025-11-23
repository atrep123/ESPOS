#!/usr/bin/env python3
"""
Analytics Dashboard for ESP32 Simulator
Web-based monitoring dashboard with real-time metrics and historical data
"""

import json
import time
import socket
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import deque
import http.server
import socketserver


@dataclass
class DashboardMetrics:
    """Dashboard metrics snapshot"""
    timestamp: float
    simulator_id: str
    fps: float
    frame_count: int
    scene: int
    bg_color: int
    button_states: Dict[str, bool]
    event_queue_size: int
    render_time_ms: float
    uptime_seconds: float


class MetricsCollector:
    """Collect metrics from multiple simulators"""
    
    def __init__(self):
        self.metrics: Dict[str, deque] = {}  # sim_id -> deque of metrics
        self.simulators: Dict[str, Dict] = {}  # sim_id -> connection info
        self.running = False
        self.collector_thread: Optional[threading.Thread] = None
    
    def add_simulator(self, sim_id: str, host: str, port: int):
        """Add simulator to monitor"""
        self.simulators[sim_id] = {
            'host': host,
            'port': port,
            'connected': False,
            'socket': None,
            'start_time': time.time()
        }
        self.metrics[sim_id] = deque(maxlen=1000)
    
    def collect_metrics_from_simulator(self, sim_id: str):
        """Collect metrics from one simulator"""
        sim = self.simulators.get(sim_id)
        if not sim:
            return
        
        try:
            # Connect if needed
            if not sim['connected']:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect((sim['host'], sim['port']))
                sim['socket'] = sock
                sim['connected'] = True
                sim['start_time'] = time.time()
            
            # Send get_state RPC
            request = {
                "jsonrpc": "2.0",
                "method": "get_state",
                "params": {},
                "id": 1
            }
            
            sim['socket'].sendall(json.dumps(request).encode() + b'\n')
            
            # Read response
            response_data = b''
            while b'\n' not in response_data:
                chunk = sim['socket'].recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed")
                response_data += chunk
            
            response = json.loads(response_data.decode())
            result = response.get('result', {})
            
            # Create metrics snapshot
            metrics = DashboardMetrics(
                timestamp=time.time(),
                simulator_id=sim_id,
                fps=result.get('fps', 0.0),
                frame_count=result.get('frame_count', 0),
                scene=result.get('scene', 0),
                bg_color=result.get('bg_color', 0),
                button_states=result.get('buttons', {}),
                event_queue_size=result.get('event_queue_size', 0),
                render_time_ms=result.get('render_time_ms', 0.0),
                uptime_seconds=time.time() - sim['start_time']
            )
            
            self.metrics[sim_id].append(metrics)
        
        except Exception as e:
            # Connection failed, mark as disconnected
            if sim['socket']:
                sim['socket'].close()
            sim['connected'] = False
    
    def collection_loop(self, interval: float = 1.0):
        """Continuous collection loop"""
        while self.running:
            for sim_id in self.simulators:
                self.collect_metrics_from_simulator(sim_id)
            time.sleep(interval)
    
    def start(self, interval: float = 1.0):
        """Start metrics collection"""
        self.running = True
        self.collector_thread = threading.Thread(
            target=self.collection_loop,
            args=(interval,),
            daemon=True
        )
        self.collector_thread.start()
    
    def stop(self):
        """Stop metrics collection"""
        self.running = False
        
        # Close all connections
        for sim in self.simulators.values():
            if sim['socket']:
                sim['socket'].close()
    
    def get_latest_metrics(self) -> Dict[str, Optional[DashboardMetrics]]:
        """Get latest metrics for all simulators"""
        return {
            sim_id: list(metrics)[-1] if metrics else None
            for sim_id, metrics in self.metrics.items()
        }
    
    def get_history(self, sim_id: str, count: int = 100) -> List[DashboardMetrics]:
        """Get historical metrics"""
        if sim_id in self.metrics:
            return list(self.metrics[sim_id])[-count:]
        return []


class DashboardServer:
    """HTTP server for dashboard"""
    
    def __init__(self, collector: MetricsCollector, port: int = 8080):
        self.collector = collector
        self.port = port
        self.server: Optional[socketserver.TCPServer] = None
    
    def create_html_dashboard(self) -> str:
        """Generate HTML dashboard"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ESP32 Simulator Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #00ff00;
            font-size: 36px;
            margin-bottom: 10px;
            text-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
        }
        
        .header .subtitle {
            color: #00ffff;
            font-size: 14px;
        }
        
        .simulator-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .simulator-card {
            background: rgba(42, 42, 42, 0.8);
            border: 2px solid #444;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        .simulator-card.offline {
            opacity: 0.5;
            border-color: #ff0000;
        }
        
        .sim-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #555;
        }
        
        .sim-name {
            font-size: 18px;
            font-weight: bold;
            color: #00ffff;
        }
        
        .status-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-badge.online {
            background: #00ff00;
            color: #000;
        }
        
        .status-badge.offline {
            background: #ff0000;
            color: #fff;
        }
        
        .metrics-row {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .metric {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 6px;
        }
        
        .metric-label {
            font-size: 11px;
            color: #999;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 20px;
            font-weight: bold;
            color: #00ff00;
        }
        
        .button-states {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        
        .button {
            flex: 1;
            padding: 8px;
            text-align: center;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
        }
        
        .button.pressed {
            background: #00ff00;
            color: #000;
        }
        
        .button.released {
            background: #333;
            color: #666;
        }
        
        .charts-section {
            background: rgba(42, 42, 42, 0.8);
            border: 2px solid #444;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .chart-container {
            height: 300px;
            margin-top: 20px;
        }
        
        .refresh-info {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #00ffff;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 ESP32 Simulator Analytics</h1>
        <div class="subtitle">Real-time monitoring dashboard</div>
    </div>
    
    <div id="simulators" class="simulator-grid">
        <div class="loading">Loading simulators...</div>
    </div>
    
    <div class="charts-section">
        <h2 style="color: #00ffff; margin-bottom: 20px;">Performance Overview</h2>
        <div class="chart-container">
            <canvas id="fpsChart"></canvas>
        </div>
    </div>
    
    <div class="refresh-info">
        Auto-refresh every 2 seconds | Last update: <span id="lastUpdate">-</span>
    </div>
    
    <script>
        let fpsChart = null;
        const fpsData = {};
        
        function updateDashboard() {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    updateSimulatorCards(data);
                    updateCharts(data);
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                })
                .catch(error => {
                    console.error('Failed to fetch metrics:', error);
                });
        }
        
        function updateSimulatorCards(simulators) {
            const container = document.getElementById('simulators');
            container.innerHTML = '';
            
            for (const [simId, metrics] of Object.entries(simulators)) {
                const card = document.createElement('div');
                card.className = 'simulator-card ' + (metrics ? 'online' : 'offline');
                
                if (metrics) {
                    card.innerHTML = `
                        <div class="sim-header">
                            <div class="sim-name">${simId}</div>
                            <div class="status-badge online">ONLINE</div>
                        </div>
                        <div class="metrics-row">
                            <div class="metric">
                                <div class="metric-label">FPS</div>
                                <div class="metric-value">${metrics.fps.toFixed(1)}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Frames</div>
                                <div class="metric-value">${metrics.frame_count}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Scene</div>
                                <div class="metric-value">${metrics.scene}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Render Time</div>
                                <div class="metric-value">${metrics.render_time_ms.toFixed(1)} ms</div>
                            </div>
                        </div>
                        <div class="button-states">
                            ${Object.entries(metrics.button_states || {}).map(([btn, pressed]) => 
                                `<div class="button ${pressed ? 'pressed' : 'released'}">${btn}</div>`
                            ).join('')}
                        </div>
                    `;
                } else {
                    card.innerHTML = `
                        <div class="sim-header">
                            <div class="sim-name">${simId}</div>
                            <div class="status-badge offline">OFFLINE</div>
                        </div>
                        <div style="text-align: center; padding: 20px; color: #666;">
                            Simulator not responding
                        </div>
                    `;
                }
                
                container.appendChild(card);
            }
        }
        
        function updateCharts(simulators) {
            // Update FPS data
            const now = Date.now();
            for (const [simId, metrics] of Object.entries(simulators)) {
                if (metrics) {
                    if (!fpsData[simId]) {
                        fpsData[simId] = [];
                    }
                    fpsData[simId].push({
                        time: now,
                        fps: metrics.fps
                    });
                    
                    // Keep only last 60 data points
                    if (fpsData[simId].length > 60) {
                        fpsData[simId].shift();
                    }
                }
            }
            
            // Update chart
            if (!fpsChart) {
                const ctx = document.getElementById('fpsChart').getContext('2d');
                fpsChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        datasets: []
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                type: 'linear',
                                ticks: { color: '#999' },
                                grid: { color: '#333' }
                            },
                            y: {
                                ticks: { color: '#999' },
                                grid: { color: '#333' }
                            }
                        },
                        plugins: {
                            legend: {
                                labels: { color: '#e0e0e0' }
                            }
                        }
                    }
                });
            }
            
            // Update chart datasets
            const colors = ['#00ff00', '#00ffff', '#ff00ff', '#ffff00'];
            fpsChart.data.datasets = Object.entries(fpsData).map(([simId, data], idx) => ({
                label: simId,
                data: data.map(d => ({ x: (d.time - now) / 1000, y: d.fps })),
                borderColor: colors[idx % colors.length],
                backgroundColor: 'transparent',
                tension: 0.4
            }));
            
            fpsChart.update();
        }
        
        // Auto-refresh
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>"""
        return html
    
    def start(self):
        """Start HTTP server"""
        parent = self
        
        class DashboardHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    # Serve dashboard HTML
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(parent.create_html_dashboard().encode())
                
                elif self.path == '/api/metrics':
                    # Serve metrics JSON
                    metrics = parent.collector.get_latest_metrics()
                    
                    # Convert to JSON-serializable format
                    data = {
                        sim_id: asdict(m) if m else None
                        for sim_id, m in metrics.items()
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())
                
                else:
                    self.send_error(404)
            
            def log_message(self, format, *args):
                # Suppress logging
                pass
        
        try:
            self.server = socketserver.TCPServer(("", self.port), DashboardHandler)
            print(f"📊 Dashboard server started at http://localhost:{self.port}")
            print(f"   Open in browser to view analytics")
            
            # Run server
            self.server.serve_forever()
        
        except KeyboardInterrupt:
            print("\n✓ Dashboard server stopped")
        finally:
            if self.server:
                self.server.shutdown()


if __name__ == '__main__':
    import sys
    
    print("╔═══════════════════════════════════════╗")
    print("║   ESP32 Analytics Dashboard           ║")
    print("╚═══════════════════════════════════════╝")
    print()
    
    # Create collector
    collector = MetricsCollector()
    
    # Add simulators (can be configured via CLI args)
    if len(sys.argv) > 1:
        # Parse: sim_id:host:port
        for arg in sys.argv[1:]:
            parts = arg.split(':')
            if len(parts) == 3:
                sim_id, host, port = parts
                collector.add_simulator(sim_id, host, int(port))
                print(f"✓ Added simulator: {sim_id} at {host}:{port}")
    else:
        # Default: single simulator
        collector.add_simulator("sim-1", "localhost", 5556)
        print("✓ Added default simulator: sim-1 at localhost:5556")
    
    print()
    
    # Start collection
    collector.start(interval=1.0)
    
    # Start dashboard server
    dashboard = DashboardServer(collector, port=8080)
    dashboard.start()
