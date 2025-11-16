# Performance Profiler - Plán rozšíření

## 🎯 Současný stav (400 řádků)
- ✅ Basic metrics collection (FPS, render time, event time)
- ✅ Statistics calculation (min, max, avg, median, stddev)
- ✅ CSV export
- ✅ HTML report s Chart.js grafy
- ✅ Memory & CPU monitoring (s psutil)

## 🚀 Plánované rozšíření

### 1. **Real-time Alerting System**
- Threshold-based alerts (FPS < 30, render > 50ms)
- Alert severity levels (warning, critical)
- Alert history a logging
- Configurable alert rules

### 2. **Anomaly Detection**
- Statistical anomaly detection (3σ rule)
- Pattern recognition (FPS drops, spikes)
- Trend analysis (degradation over time)
- Predictive warnings

### 3. **Performance Recommendations**
- Automated performance analysis
- Bottleneck identification
- Optimization suggestions
- Best practices checks

### 4. **Advanced Visualizations**
- Heatmaps (performance over time)
- Percentile graphs (P50, P95, P99)
- Frame time distribution histogram
- Resource usage correlation

### 5. **Profiling Sessions**
- Named sessions s metadata
- Session comparison
- Baseline establishment
- Regression detection

### 6. **Export Enhancements**
- JSON export s metadata
- Markdown report generation
- Image export (matplotlib charts)
- Multi-format reports

### 7. **Live Dashboard Integration**
- WebSocket streaming
- Real-time alerts display
- Interactive controls
- Multi-profiler aggregation

## 📊 Target Features

```python
# Alert system
profiler.add_alert_rule("low_fps", fps_threshold=30, severity="warning")
profiler.add_alert_rule("high_render", render_threshold_ms=50, severity="critical")

# Anomaly detection
profiler.enable_anomaly_detection(sensitivity=3.0)
anomalies = profiler.get_anomalies()

# Recommendations
recommendations = profiler.analyze_performance()
# Returns: ["FPS drops detected at 10:23:45", "Consider reducing render complexity"]

# Session management
profiler.start_session("baseline_v1")
profiler.end_session()
profiler.compare_sessions("baseline_v1", "optimized_v2")

# Advanced exports
profiler.export_to_json("profile_session.json")
profiler.export_to_markdown("PERFORMANCE_REPORT.md")
profiler.generate_images("charts/")
```

## 🎨 Cílový rozsah
- **Současnost:** ~400 řádků
- **Cíl:** ~800-900 řádků (2x rozšíření)
- **Nové funkce:** ~7 pokročilých systémů
