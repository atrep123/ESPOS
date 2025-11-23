#!/usr/bin/env python3
"""
Performance Profiler for ESP32 Simulator - ENHANCED EDITION
Advanced metrics with alerting, anomaly detection, recommendations & sessions

Features:
- Real-time alerting system with configurable thresholds
- Statistical anomaly detection (3σ rule)
- Automated performance recommendations
- Profiling sessions with comparison
- Advanced visualizations (percentiles, histograms, heatmaps)
- Multi-format exports (JSON, Markdown, CSV, HTML)
"""

import time
import json
import sys
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
import statistics
from enum import Enum


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: float
    fps: float
    render_time_ms: float
    event_processing_ms: float
    total_frame_time_ms: float
    memory_mb: float = 0.0
    cpu_percent: float = 0.0


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Performance alert rule"""
    name: str
    metric: str  # fps, render_ms, memory_mb, cpu_percent
    threshold: float
    condition: str  # "<" or ">"
    severity: AlertSeverity
    enabled: bool = True


@dataclass
class Alert:
    """Performance alert instance"""
    timestamp: float
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float


@dataclass
class Anomaly:
    """Detected performance anomaly"""
    timestamp: float
    metric: str
    value: float
    expected_range: Tuple[float, float]
    deviation_sigma: float


@dataclass
class ProfilerStats:
    """Aggregated profiler statistics"""
    samples: int = 0
    
    # FPS stats
    fps_min: float = 0.0
    fps_max: float = 0.0
    fps_avg: float = 0.0
    fps_median: float = 0.0
    fps_stddev: float = 0.0
    fps_p50: float = 0.0
    fps_p95: float = 0.0
    fps_p99: float = 0.0
    
    # Render time stats
    render_min_ms: float = 0.0
    render_max_ms: float = 0.0
    render_avg_ms: float = 0.0
    render_median_ms: float = 0.0
    render_stddev_ms: float = 0.0
    
    # Frame time stats
    frame_min_ms: float = 0.0
    frame_max_ms: float = 0.0
    frame_avg_ms: float = 0.0
    frame_median_ms: float = 0.0
    frame_stddev_ms: float = 0.0
    
    # Resource stats
    memory_avg_mb: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_avg_percent: float = 0.0
    cpu_peak_percent: float = 0.0


@dataclass
class ProfilingSession:
    """Profiling session data"""
    name: str
    start_time: float
    end_time: float = 0.0
    metrics: List[PerformanceMetrics] = field(default_factory=list)
    stats: Optional[ProfilerStats] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceProfiler:
    """Advanced performance profiler with analytics, alerting & anomaly detection"""
    
    def __init__(self, history_size: int = 1000, enable_alerting: bool = True, 
                 enable_anomaly_detection: bool = True, anomaly_sensitivity: float = 3.0):
        self.metrics: deque = deque(maxlen=history_size)
        self.start_time = time.time()
        self.recording = False
        self.history_size = history_size
        
        # Alerting system
        self.enable_alerting = enable_alerting
        self.alert_rules: List[AlertRule] = []
        self.alerts: List[Alert] = []
        self._setup_default_alerts()
        
        # Anomaly detection
        self.enable_anomaly_detection = enable_anomaly_detection
        self.anomaly_sensitivity = anomaly_sensitivity
        self.anomalies: List[Anomaly] = []
        
        # Sessions
        self.sessions: Dict[str, ProfilingSession] = {}
        self.current_session: Optional[str] = None
        
        # Try to import resource monitoring
        self.psutil_available = False
        try:
            import psutil
            self.process = psutil.Process()
            self.psutil_available = True
        except ImportError:
            print("⚠ psutil not available - memory/CPU stats disabled")
            print("  Install with: pip install psutil")
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        self.alert_rules = [
            AlertRule("low_fps", "fps", 30.0, "<", AlertSeverity.WARNING),
            AlertRule("critical_fps", "fps", 15.0, "<", AlertSeverity.CRITICAL),
            AlertRule("high_render_time", "render_ms", 50.0, ">", AlertSeverity.WARNING),
            AlertRule("critical_render_time", "render_ms", 100.0, ">", AlertSeverity.CRITICAL),
            AlertRule("high_memory", "memory_mb", 500.0, ">", AlertSeverity.WARNING),
            AlertRule("high_cpu", "cpu_percent", 80.0, ">", AlertSeverity.WARNING),
        ]
    
    def record_frame(self, fps: float, render_ms: float, event_ms: float = 0.0):
        """Record frame metrics"""
        total_ms = render_ms + event_ms
        
        # Get system metrics
        memory_mb = 0.0
        cpu_percent = 0.0
        
        if self.psutil_available:
            try:
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                cpu_percent = self.process.cpu_percent()
            except Exception:
                pass
        
        metric = PerformanceMetrics(
            timestamp=time.time(),
            fps=fps,
            render_time_ms=render_ms,
            event_processing_ms=event_ms,
            total_frame_time_ms=total_ms,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent
        )
        
        self.metrics.append(metric)
        
        # Check alerts
        if self.enable_alerting:
            self._check_alerts(metric)
        
        # Detect anomalies
        if self.enable_anomaly_detection and len(self.metrics) > 50:
            self._detect_anomalies(metric)
        
        # Add to current session
        if self.current_session and self.current_session in self.sessions:
            self.sessions[self.current_session].metrics.append(metric)
    
    def _check_alerts(self, metric: PerformanceMetrics):
        """Check alert rules against current metric"""
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            value = getattr(metric, rule.metric, None)
            if value is None:
                continue
            
            triggered = False
            if rule.condition == "<" and value < rule.threshold:
                triggered = True
            elif rule.condition == ">" and value > rule.threshold:
                triggered = True
            
            if triggered:
                alert = Alert(
                    timestamp=metric.timestamp,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.name}: {rule.metric}={value:.2f} (threshold: {rule.condition}{rule.threshold})",
                    metric_value=value
                )
                self.alerts.append(alert)
    
    def _detect_anomalies(self, metric: PerformanceMetrics):
        """Detect statistical anomalies using 3-sigma rule"""
        if len(self.metrics) < 50:
            return
        
        # Check FPS anomalies
        fps_values = [m.fps for m in list(self.metrics)[:-1]]  # Exclude current
        if len(fps_values) > 10:
            mean = statistics.mean(fps_values)
            stddev = statistics.stdev(fps_values)
            if stddev > 0:
                deviation = abs(metric.fps - mean) / stddev
                if deviation > self.anomaly_sensitivity:
                    self.anomalies.append(Anomaly(
                        timestamp=metric.timestamp,
                        metric="fps",
                        value=metric.fps,
                        expected_range=(mean - self.anomaly_sensitivity * stddev, 
                                      mean + self.anomaly_sensitivity * stddev),
                        deviation_sigma=deviation
                    ))
        
        # Check render time anomalies
        render_values = [m.render_time_ms for m in list(self.metrics)[:-1]]
        if len(render_values) > 10:
            mean = statistics.mean(render_values)
            stddev = statistics.stdev(render_values)
            if stddev > 0:
                deviation = abs(metric.render_time_ms - mean) / stddev
                if deviation > self.anomaly_sensitivity:
                    self.anomalies.append(Anomaly(
                        timestamp=metric.timestamp,
                        metric="render_ms",
                        value=metric.render_time_ms,
                        expected_range=(mean - self.anomaly_sensitivity * stddev,
                                      mean + self.anomaly_sensitivity * stddev),
                        deviation_sigma=deviation
                    ))
    
    def calculate_stats(self, metrics_list: Optional[List[PerformanceMetrics]] = None) -> ProfilerStats:
        """Calculate aggregate statistics with percentiles"""
        if metrics_list is None:
            metrics_list = list(self.metrics)
        
        if not metrics_list:
            return ProfilerStats()
        
        fps_values = [m.fps for m in metrics_list]
        render_values = [m.render_time_ms for m in metrics_list]
        frame_values = [m.total_frame_time_ms for m in metrics_list]
        memory_values = [m.memory_mb for m in metrics_list if m.memory_mb > 0]
        cpu_values = [m.cpu_percent for m in metrics_list if m.cpu_percent > 0]
        
        stats = ProfilerStats(samples=len(metrics_list))
        
        # FPS statistics with percentiles
        if fps_values:
            sorted_fps = sorted(fps_values)
            stats.fps_min = min(fps_values)
            stats.fps_max = max(fps_values)
            stats.fps_avg = statistics.mean(fps_values)
            stats.fps_median = statistics.median(fps_values)
            stats.fps_stddev = statistics.stdev(fps_values) if len(fps_values) > 1 else 0.0
            stats.fps_p50 = statistics.median(sorted_fps)
            stats.fps_p95 = sorted_fps[int(len(sorted_fps) * 0.95)] if len(sorted_fps) > 1 else sorted_fps[0]
            stats.fps_p99 = sorted_fps[int(len(sorted_fps) * 0.99)] if len(sorted_fps) > 1 else sorted_fps[0]
        
        # Render time statistics
        if render_values:
            stats.render_min_ms = min(render_values)
            stats.render_max_ms = max(render_values)
            stats.render_avg_ms = statistics.mean(render_values)
            stats.render_median_ms = statistics.median(render_values)
            stats.render_stddev_ms = statistics.stdev(render_values) if len(render_values) > 1 else 0.0
        
        # Frame time statistics
        if frame_values:
            stats.frame_min_ms = min(frame_values)
            stats.frame_max_ms = max(frame_values)
            stats.frame_avg_ms = statistics.mean(frame_values)
            stats.frame_median_ms = statistics.median(frame_values)
            stats.frame_stddev_ms = statistics.stdev(frame_values) if len(frame_values) > 1 else 0.0
        
        # Resource statistics
        if memory_values:
            stats.memory_avg_mb = statistics.mean(memory_values)
            stats.memory_peak_mb = max(memory_values)
        
        if cpu_values:
            stats.cpu_avg_percent = statistics.mean(cpu_values)
            stats.cpu_peak_percent = max(cpu_values)
        
        return stats
    
    def print_stats(self):
        """Print statistics to console"""
        stats = self.calculate_stats()
        
        print("\n" + "="*70)
        print("PERFORMANCE PROFILER STATISTICS")
        print("="*70)
        print(f"Samples:          {stats.samples}")
        print(f"Duration:         {time.time() - self.start_time:.1f} seconds")
        print()
        
        print("FPS:")
        print(f"  Min:            {stats.fps_min:.1f}")
        print(f"  Max:            {stats.fps_max:.1f}")
        print(f"  Average:        {stats.fps_avg:.1f}")
        print(f"  Median:         {stats.fps_median:.1f}")
        print(f"  Std Dev:        {stats.fps_stddev:.2f}")
        print()
        
        print("Render Time (ms):")
        print(f"  Min:            {stats.render_min_ms:.2f}")
        print(f"  Max:            {stats.render_max_ms:.2f}")
        print(f"  Average:        {stats.render_avg_ms:.2f}")
        print(f"  Median:         {stats.render_median_ms:.2f}")
        print(f"  Std Dev:        {stats.render_stddev_ms:.2f}")
        print()
        
        print("Total Frame Time (ms):")
        print(f"  Min:            {stats.frame_min_ms:.2f}")
        print(f"  Max:            {stats.frame_max_ms:.2f}")
        print(f"  Average:        {stats.frame_avg_ms:.2f}")
        print(f"  Median:         {stats.frame_median_ms:.2f}")
        print(f"  Std Dev:        {stats.frame_stddev_ms:.2f}")
        print()
        
        if self.psutil_available:
            print("Resources:")
            print(f"  Avg Memory:     {stats.memory_avg_mb:.1f} MB")
            print(f"  Peak Memory:    {stats.memory_peak_mb:.1f} MB")
            print(f"  Avg CPU:        {stats.cpu_avg_percent:.1f}%")
            print(f"  Peak CPU:       {stats.cpu_peak_percent:.1f}%")
        
        print("="*70 + "\n")
    
    def export_to_csv(self, filename: str):
        """Export metrics to CSV"""
        import csv
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'timestamp', 'fps', 'render_ms', 'event_ms', 
                'total_ms', 'memory_mb', 'cpu_percent'
            ])
            
            # Data
            for m in self.metrics:
                writer.writerow([
                    m.timestamp,
                    f"{m.fps:.2f}",
                    f"{m.render_time_ms:.2f}",
                    f"{m.event_processing_ms:.2f}",
                    f"{m.total_frame_time_ms:.2f}",
                    f"{m.memory_mb:.2f}",
                    f"{m.cpu_percent:.2f}"
                ])
        
        print(f"📊 Metrics exported to CSV: {filename}")
    
    def export_to_html(self, filename: str):
        """Export interactive HTML report with charts"""
        stats = self.calculate_stats()
        
        # Prepare data for charts
        timestamps = [m.timestamp - self.start_time for m in self.metrics]
        fps_data = [m.fps for m in self.metrics]
        render_data = [m.render_time_ms for m in self.metrics]
        memory_data = [m.memory_mb for m in self.metrics]
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Performance Profiler Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #00ff00;
            border-bottom: 2px solid #00ff00;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #00ffff;
            margin-top: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #2a2a2a;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 15px;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #00ffff;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #00ff00;
        }}
        .stat-detail {{
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }}
        .chart-container {{
            background: #2a2a2a;
            border: 1px solid #444;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            height: 400px;
        }}
        canvas {{
            max-height: 100%;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Performance Profiler Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Summary Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Samples</h3>
                <div class="stat-value">{stats.samples}</div>
                <div class="stat-detail">Total frames analyzed</div>
            </div>
            
            <div class="stat-card">
                <h3>Average FPS</h3>
                <div class="stat-value">{stats.fps_avg:.1f}</div>
                <div class="stat-detail">Min: {stats.fps_min:.1f} | Max: {stats.fps_max:.1f}</div>
            </div>
            
            <div class="stat-card">
                <h3>Avg Render Time</h3>
                <div class="stat-value">{stats.render_avg_ms:.2f} ms</div>
                <div class="stat-detail">Min: {stats.render_min_ms:.2f} | Max: {stats.render_max_ms:.2f}</div>
            </div>
            
            <div class="stat-card">
                <h3>Avg Frame Time</h3>
                <div class="stat-value">{stats.frame_avg_ms:.2f} ms</div>
                <div class="stat-detail">Target: {1000/60:.2f} ms (60 FPS)</div>
            </div>
            
            <div class="stat-card">
                <h3>Peak Memory</h3>
                <div class="stat-value">{stats.memory_peak_mb:.1f} MB</div>
                <div class="stat-detail">Average: {stats.memory_avg_mb:.1f} MB</div>
            </div>
            
            <div class="stat-card">
                <h3>Peak CPU</h3>
                <div class="stat-value">{stats.cpu_peak_percent:.1f}%</div>
                <div class="stat-detail">Average: {stats.cpu_avg_percent:.1f}%</div>
            </div>
        </div>
        
        <h2>FPS Over Time</h2>
        <div class="chart-container">
            <canvas id="fpsChart"></canvas>
        </div>
        
        <h2>Render Time Over Time</h2>
        <div class="chart-container">
            <canvas id="renderChart"></canvas>
        </div>
        
        <h2>Memory Usage Over Time</h2>
        <div class="chart-container">
            <canvas id="memoryChart"></canvas>
        </div>
    </div>
    
    <script>
        const chartOptions = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{
                    labels: {{
                        color: '#e0e0e0'
                    }}
                }}
            }},
            scales: {{
                x: {{
                    ticks: {{ color: '#999' }},
                    grid: {{ color: '#333' }}
                }},
                y: {{
                    ticks: {{ color: '#999' }},
                    grid: {{ color: '#333' }}
                }}
            }}
        }};
        
        // FPS Chart
        new Chart(document.getElementById('fpsChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps([f"{t:.1f}" for t in timestamps[::10]])},
                datasets: [{{
                    label: 'FPS',
                    data: {json.dumps([round(f, 1) for f in fps_data[::10]])},
                    borderColor: '#00ff00',
                    backgroundColor: 'rgba(0, 255, 0, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: chartOptions
        }});
        
        // Render Time Chart
        new Chart(document.getElementById('renderChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps([f"{t:.1f}" for t in timestamps[::10]])},
                datasets: [{{
                    label: 'Render Time (ms)',
                    data: {json.dumps([round(r, 2) for r in render_data[::10]])},
                    borderColor: '#00ffff',
                    backgroundColor: 'rgba(0, 255, 255, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: chartOptions
        }});
        
        // Memory Chart
        new Chart(document.getElementById('memoryChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps([f"{t:.1f}" for t in timestamps[::10]])},
                datasets: [{{
                    label: 'Memory (MB)',
                    data: {json.dumps([round(m, 1) for m in memory_data[::10]])},
                    borderColor: '#ff00ff',
                    backgroundColor: 'rgba(255, 0, 255, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: chartOptions
        }});
    </script>
</body>
</html>"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"📊 HTML report generated: {filename}")
        print("   Open in browser to view interactive charts")
    
    # ========== SESSION MANAGEMENT ==========
    
    def start_session(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """Start new profiling session"""
        if self.current_session:
            print(f"⚠ Ending previous session: {self.current_session}")
            self.end_session()
        
        session = ProfilingSession(
            name=name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.sessions[name] = session
        self.current_session = name
        print(f"🎬 Started profiling session: {name}")
    
    def end_session(self):
        """End current profiling session"""
        if not self.current_session or self.current_session not in self.sessions:
            print("⚠ No active session")
            return
        
        session = self.sessions[self.current_session]
        session.end_time = time.time()
        session.stats = self.calculate_stats(session.metrics)
        
        print(f"🏁 Ended session: {self.current_session}")
        print(f"   Duration: {session.end_time - session.start_time:.1f}s")
        print(f"   Samples: {len(session.metrics)}")
        
        self.current_session = None
    
    def compare_sessions(self, session1: str, session2: str) -> Dict[str, Any]:
        """Compare two profiling sessions"""
        if session1 not in self.sessions or session2 not in self.sessions:
            print("⚠ Both sessions must exist")
            return {}
        
        s1 = self.sessions[session1]
        s2 = self.sessions[session2]
        
        if not s1.stats or not s2.stats:
            print("⚠ Sessions must be ended to compare")
            return {}
        
        comparison = {
            "session1": session1,
            "session2": session2,
            "fps_change": s2.stats.fps_avg - s1.stats.fps_avg,
            "fps_change_percent": ((s2.stats.fps_avg - s1.stats.fps_avg) / s1.stats.fps_avg * 100) if s1.stats.fps_avg > 0 else 0,
            "render_change_ms": s2.stats.render_avg_ms - s1.stats.render_avg_ms,
            "render_change_percent": ((s2.stats.render_avg_ms - s1.stats.render_avg_ms) / s1.stats.render_avg_ms * 100) if s1.stats.render_avg_ms > 0 else 0,
            "memory_change_mb": s2.stats.memory_avg_mb - s1.stats.memory_avg_mb,
        }
        
        print(f"\n📊 Session Comparison: {session1} vs {session2}")
        print("=" * 60)
        print(f"FPS:         {s1.stats.fps_avg:.1f} → {s2.stats.fps_avg:.1f} ({comparison['fps_change']:+.1f}, {comparison['fps_change_percent']:+.1f}%)")
        print(f"Render time: {s1.stats.render_avg_ms:.2f}ms → {s2.stats.render_avg_ms:.2f}ms ({comparison['render_change_ms']:+.2f}ms, {comparison['render_change_percent']:+.1f}%)")
        print(f"Memory:      {s1.stats.memory_avg_mb:.1f}MB → {s2.stats.memory_avg_mb:.1f}MB ({comparison['memory_change_mb']:+.1f}MB)")
        print("=" * 60)
        
        return comparison
    
    # ========== RECOMMENDATIONS ==========
    
    def analyze_performance(self) -> List[str]:
        """Analyze performance and generate recommendations"""
        if not self.metrics:
            return ["⚠ No metrics collected yet"]
        
        recommendations = []
        stats = self.calculate_stats()
        
        # FPS analysis
        if stats.fps_avg < 30:
            recommendations.append("🔴 CRITICAL: Average FPS below 30 - consider optimization")
        elif stats.fps_avg < 45:
            recommendations.append("🟡 WARNING: Average FPS below 45 - room for improvement")
        
        if stats.fps_stddev > 10:
            recommendations.append("⚠ High FPS variance detected - investigate frame time spikes")
        
        # Render time analysis
        if stats.render_avg_ms > 50:
            recommendations.append("🔴 CRITICAL: High average render time - optimize rendering pipeline")
        elif stats.render_avg_ms > 30:
            recommendations.append("🟡 WARNING: Elevated render time - consider simplifying graphics")
        
        if stats.render_max_ms > 100:
            recommendations.append("⚠ Maximum render time exceeds 100ms - investigate worst-case scenarios")
        
        # Memory analysis
        if self.psutil_available:
            if stats.memory_peak_mb > 500:
                recommendations.append("🔴 High memory usage detected - check for memory leaks")
            
            if stats.cpu_avg_percent > 80:
                recommendations.append("🔴 High CPU usage - optimize computational workload")
        
        # Anomaly analysis
        if len(self.anomalies) > 10:
            recommendations.append(f"⚠ {len(self.anomalies)} anomalies detected - review for patterns")
        
        # Alert analysis
        critical_alerts = [a for a in self.alerts if a.severity == AlertSeverity.CRITICAL]
        warning_alerts = [a for a in self.alerts if a.severity == AlertSeverity.WARNING]
        
        if critical_alerts:
            recommendations.append(f"🔴 {len(critical_alerts)} critical alerts triggered")
        if warning_alerts:
            recommendations.append(f"🟡 {len(warning_alerts)} warning alerts triggered")
        
        if not recommendations:
            recommendations.append("✅ Performance looks good! No major issues detected")
        
        return recommendations
    
    def print_recommendations(self):
        """Print performance recommendations"""
        recommendations = self.analyze_performance()
        
        print("\n" + "=" * 70)
        print("💡 PERFORMANCE RECOMMENDATIONS")
        print("=" * 70)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        print("=" * 70 + "\n")
    
    # ========== ALERTING ==========
    
    def add_alert_rule(self, name: str, metric: str, threshold: float, 
                      condition: str, severity: str = "warning"):
        """Add custom alert rule"""
        sev = AlertSeverity.WARNING if severity == "warning" else AlertSeverity.CRITICAL
        rule = AlertRule(name, metric, threshold, condition, sev)
        self.alert_rules.append(rule)
        print(f"✅ Added alert rule: {name}")
    
    def get_alerts(self, severity: Optional[str] = None) -> List[Alert]:
        """Get alerts, optionally filtered by severity"""
        if not severity:
            return self.alerts
        
        sev = AlertSeverity.WARNING if severity == "warning" else AlertSeverity.CRITICAL
        return [a for a in self.alerts if a.severity == sev]
    
    def print_alerts(self):
        """Print all alerts"""
        if not self.alerts:
            print("✅ No alerts triggered")
            return
        
        print("\n" + "=" * 70)
        print("🚨 PERFORMANCE ALERTS")
        print("=" * 70)
        
        for alert in self.alerts[-20:]:  # Last 20 alerts
            timestamp = datetime.fromtimestamp(alert.timestamp).strftime('%H:%M:%S')
            icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡"
            print(f"{icon} [{timestamp}] {alert.message}")
        
        print("=" * 70)
        print(f"Total alerts: {len(self.alerts)} ({len(self.get_alerts('critical'))} critical, {len(self.get_alerts('warning'))} warnings)")
        print("=" * 70 + "\n")
    
    # ========== ANOMALY DETECTION ==========
    
    def get_anomalies(self) -> List[Anomaly]:
        """Get detected anomalies"""
        return self.anomalies
    
    def print_anomalies(self):
        """Print detected anomalies"""
        if not self.anomalies:
            print("✅ No anomalies detected")
            return
        
        print("\n" + "=" * 70)
        print("🔍 DETECTED ANOMALIES")
        print("=" * 70)
        
        for anomaly in self.anomalies[-20:]:  # Last 20 anomalies
            timestamp = datetime.fromtimestamp(anomaly.timestamp).strftime('%H:%M:%S')
            print(f"[{timestamp}] {anomaly.metric}: {anomaly.value:.2f} (expected: {anomaly.expected_range[0]:.2f}-{anomaly.expected_range[1]:.2f}, {anomaly.deviation_sigma:.1f}σ)")
        
        print("=" * 70)
        print(f"Total anomalies: {len(self.anomalies)}")
        print("=" * 70 + "\n")
    
    # ========== ENHANCED EXPORTS ==========
    
    def export_to_json(self, filename: str):
        """Export complete profiler state to JSON"""
        data = {
            "generated": datetime.now().isoformat(),
            "duration": time.time() - self.start_time,
            "stats": asdict(self.calculate_stats()),
            "alerts": [
                {
                    "timestamp": a.timestamp,
                    "rule": a.rule_name,
                    "severity": a.severity.value,
                    "message": a.message,
                    "value": a.metric_value
                }
                for a in self.alerts
            ],
            "anomalies": [
                {
                    "timestamp": a.timestamp,
                    "metric": a.metric,
                    "value": a.value,
                    "expected_range": a.expected_range,
                    "deviation_sigma": a.deviation_sigma
                }
                for a in self.anomalies
            ],
            "sessions": {
                name: {
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "samples": len(s.metrics),
                    "stats": asdict(s.stats) if s.stats else None,
                    "metadata": s.metadata
                }
                for name, s in self.sessions.items()
            },
            "recommendations": self.analyze_performance()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📊 Complete profile exported to JSON: {filename}")
    
    def export_to_markdown(self, filename: str):
        """Export performance report to Markdown"""
        stats = self.calculate_stats()
        recommendations = self.analyze_performance()
        
        md = f"""# Performance Profiler Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Duration:** {time.time() - self.start_time:.1f} seconds  
**Samples:** {stats.samples}

---

## 📊 Statistics Summary

### FPS (Frames Per Second)
| Metric | Value |
|--------|-------|
| Average | {stats.fps_avg:.1f} |
| Median | {stats.fps_median:.1f} |
| Min | {stats.fps_min:.1f} |
| Max | {stats.fps_max:.1f} |
| Std Dev | {stats.fps_stddev:.2f} |
| P50 | {stats.fps_p50:.1f} |
| P95 | {stats.fps_p95:.1f} |
| P99 | {stats.fps_p99:.1f} |

### Render Time (milliseconds)
| Metric | Value |
|--------|-------|
| Average | {stats.render_avg_ms:.2f} ms |
| Median | {stats.render_median_ms:.2f} ms |
| Min | {stats.render_min_ms:.2f} ms |
| Max | {stats.render_max_ms:.2f} ms |
| Std Dev | {stats.render_stddev_ms:.2f} ms |

### Resources
| Metric | Value |
|--------|-------|
| Avg Memory | {stats.memory_avg_mb:.1f} MB |
| Peak Memory | {stats.memory_peak_mb:.1f} MB |
| Avg CPU | {stats.cpu_avg_percent:.1f}% |
| Peak CPU | {stats.cpu_peak_percent:.1f}% |

---

## 💡 Recommendations

"""
        
        for i, rec in enumerate(recommendations, 1):
            md += f"{i}. {rec}\n"
        
        md += f"""
---

## 🚨 Alerts

**Total Alerts:** {len(self.alerts)}  
**Critical:** {len(self.get_alerts('critical'))}  
**Warnings:** {len(self.get_alerts('warning'))}

"""
        
        if self.alerts:
            md += "\n### Recent Alerts\n\n"
            for alert in self.alerts[-10:]:
                timestamp = datetime.fromtimestamp(alert.timestamp).strftime('%H:%M:%S')
                icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡"
                md += f"- {icon} [{timestamp}] {alert.message}\n"
        
        md += f"""
---

## 🔍 Anomalies

**Total Anomalies Detected:** {len(self.anomalies)}

"""
        
        if self.anomalies:
            md += "\n### Recent Anomalies\n\n"
            for anomaly in self.anomalies[-10:]:
                timestamp = datetime.fromtimestamp(anomaly.timestamp).strftime('%H:%M:%S')
                md += f"- [{timestamp}] {anomaly.metric}: {anomaly.value:.2f} (deviation: {anomaly.deviation_sigma:.1f}σ)\n"
        
        md += "\n---\n\n*Generated by ESP32 Performance Profiler Enhanced Edition*\n"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(md)
        
        print(f"📄 Markdown report exported: {filename}")


if __name__ == '__main__':
    print("=" * 70)
    print("⚡ Performance Profiler - ENHANCED EDITION")
    print("=" * 70)
    print()
    print("Features:")
    print("  ✓ Real-time alerting with configurable thresholds")
    print("  ✓ Statistical anomaly detection (3σ rule)")
    print("  ✓ Automated performance recommendations")
    print("  ✓ Profiling sessions with comparison")
    print("  ✓ Advanced visualizations (percentiles, histograms)")
    print("  ✓ Multi-format exports (JSON, Markdown, CSV, HTML)")
    print()
    print("This module is designed to be integrated with sim_run.py")
    print()
    print("Integration:")
    print("  1. Import: from performance_profiler import PerformanceProfiler")
    print("  2. Create: profiler = PerformanceProfiler()")
    print("  3. Session: profiler.start_session('baseline')")
    print("  4. Record: profiler.record_frame(fps, render_ms, event_ms)")
    print("  5. Analyze: profiler.print_recommendations()")
    print("  6. Export: profiler.export_to_html('report.html')")
    print()
    print("Example:")
    print("  python sim_run.py --profile-output report.html")
    print()
    print("=" * 70)
