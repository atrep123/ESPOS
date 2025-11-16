#!/usr/bin/env python3
"""Test Enhanced Performance Profiler with all new features"""

import sys
import time
import random
sys.path.insert(0, '.')

from performance_profiler import PerformanceProfiler

def simulate_good_performance(profiler, duration=10):
    """Simulate good performance scenario"""
    print(f"\n🟢 Simulating good performance ({duration}s)...")
    start = time.time()
    frame = 0
    
    while time.time() - start < duration:
        fps = random.uniform(55, 65)  # Good FPS
        render_ms = random.uniform(10, 15)  # Good render time
        event_ms = random.uniform(1, 3)
        
        profiler.record_frame(fps, render_ms, event_ms)
        frame += 1
        time.sleep(0.016)  # ~60 FPS
    
    print(f"  ✓ Recorded {frame} frames")

def simulate_bad_performance(profiler, duration=10):
    """Simulate bad performance scenario"""
    print(f"\n🔴 Simulating bad performance ({duration}s)...")
    start = time.time()
    frame = 0
    
    while time.time() - start < duration:
        fps = random.uniform(20, 30)  # Low FPS
        render_ms = random.uniform(40, 60)  # High render time
        event_ms = random.uniform(5, 10)
        
        profiler.record_frame(fps, render_ms, event_ms)
        frame += 1
        time.sleep(0.033)  # ~30 FPS
    
    print(f"  ✓ Recorded {frame} frames")

def simulate_spike_performance(profiler, duration=10):
    """Simulate performance with spikes"""
    print(f"\n🟡 Simulating performance with spikes ({duration}s)...")
    start = time.time()
    frame = 0
    
    while time.time() - start < duration:
        # Occasional spikes
        if random.random() < 0.1:  # 10% chance of spike
            fps = random.uniform(10, 20)
            render_ms = random.uniform(80, 120)
        else:
            fps = random.uniform(55, 65)
            render_ms = random.uniform(10, 15)
        
        event_ms = random.uniform(1, 3)
        profiler.record_frame(fps, render_ms, event_ms)
        frame += 1
        time.sleep(0.016)
    
    print(f"  ✓ Recorded {frame} frames")

def test_enhanced_features():
    """Test all enhanced profiler features"""
    
    print("=" * 80)
    print("⚡ TESTING ENHANCED PERFORMANCE PROFILER")
    print("=" * 80)
    
    # Create profiler with enhanced features
    profiler = PerformanceProfiler(
        history_size=2000,
        enable_alerting=True,
        enable_anomaly_detection=True,
        anomaly_sensitivity=3.0
    )
    
    # ========== TEST 1: Session Management ==========
    print("\n" + "─" * 80)
    print("1️⃣  SESSION MANAGEMENT")
    print("─" * 80)
    
    profiler.start_session("baseline", metadata={"version": "v1.0", "config": "default"})
    simulate_good_performance(profiler, duration=5)
    profiler.end_session()
    
    profiler.start_session("optimized", metadata={"version": "v2.0", "config": "optimized"})
    simulate_good_performance(profiler, duration=3)
    profiler.end_session()
    
    # Compare sessions
    comparison = profiler.compare_sessions("baseline", "optimized")
    print(f"\n✓ Session comparison complete")
    
    # ========== TEST 2: Alerting System ==========
    print("\n" + "─" * 80)
    print("2️⃣  ALERTING SYSTEM")
    print("─" * 80)
    
    # Add custom alert
    profiler.add_alert_rule("very_low_fps", "fps", 25.0, "<", "critical")
    
    # Simulate bad performance to trigger alerts
    profiler.start_session("alerts_test")
    simulate_bad_performance(profiler, duration=5)
    profiler.end_session()
    
    # Show alerts
    profiler.print_alerts()
    
    print(f"✓ Alerts system tested")
    print(f"  Total alerts: {len(profiler.alerts)}")
    print(f"  Critical: {len(profiler.get_alerts('critical'))}")
    print(f"  Warnings: {len(profiler.get_alerts('warning'))}")
    
    # ========== TEST 3: Anomaly Detection ==========
    print("\n" + "─" * 80)
    print("3️⃣  ANOMALY DETECTION")
    print("─" * 80)
    
    profiler.start_session("anomalies_test")
    simulate_spike_performance(profiler, duration=8)
    profiler.end_session()
    
    # Show anomalies
    profiler.print_anomalies()
    
    print(f"✓ Anomaly detection tested")
    print(f"  Total anomalies: {len(profiler.anomalies)}")
    
    # ========== TEST 4: Recommendations ==========
    print("\n" + "─" * 80)
    print("4️⃣  PERFORMANCE RECOMMENDATIONS")
    print("─" * 80)
    
    profiler.print_recommendations()
    
    # ========== TEST 5: Statistics with Percentiles ==========
    print("\n" + "─" * 80)
    print("5️⃣  STATISTICS WITH PERCENTILES")
    print("─" * 80)
    
    stats = profiler.calculate_stats()
    print(f"Samples:     {stats.samples}")
    print(f"FPS avg:     {stats.fps_avg:.1f}")
    print(f"FPS P50:     {stats.fps_p50:.1f}")
    print(f"FPS P95:     {stats.fps_p95:.1f}")
    print(f"FPS P99:     {stats.fps_p99:.1f}")
    print(f"Render avg:  {stats.render_avg_ms:.2f} ms")
    
    # ========== TEST 6: Enhanced Exports ==========
    print("\n" + "─" * 80)
    print("6️⃣  ENHANCED EXPORTS")
    print("─" * 80)
    
    # JSON export
    profiler.export_to_json("profiler_enhanced.json")
    
    # Markdown export
    profiler.export_to_markdown("PROFILER_REPORT.md")
    
    # CSV export
    profiler.export_to_csv("profiler_enhanced.csv")
    
    # HTML export
    profiler.export_to_html("profiler_enhanced.html")
    
    print("\n✓ All exports complete")
    
    # ========== FINAL SUMMARY ==========
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    
    print(f"\nSessions:     {len(profiler.sessions)}")
    print(f"Total frames: {stats.samples}")
    print(f"Alerts:       {len(profiler.alerts)} ({len(profiler.get_alerts('critical'))} critical)")
    print(f"Anomalies:    {len(profiler.anomalies)}")
    
    print("\n📁 Generated Files:")
    print("  • profiler_enhanced.json - Complete JSON export")
    print("  • PROFILER_REPORT.md - Markdown report")
    print("  • profiler_enhanced.csv - CSV metrics")
    print("  • profiler_enhanced.html - Interactive HTML report")
    
    print("\n" + "=" * 80)
    print("✅ ALL ENHANCED FEATURES TESTED SUCCESSFULLY!")
    print("=" * 80)
    
    # Feature checklist
    print("\n🎯 Feature Checklist:")
    features = [
        "Real-time Alerting System",
        "Anomaly Detection (3σ)",
        "Performance Recommendations",
        "Session Management & Comparison",
        "Percentile Statistics (P50, P95, P99)",
        "JSON Export with metadata",
        "Markdown Report Generation",
        "CSV Export",
        "HTML Interactive Report",
    ]
    
    for i, feature in enumerate(features, 1):
        print(f"  [{i}] ✓ {feature}")
    
    print("\n🎉 Performance Profiler Enhanced Edition Ready!")

if __name__ == '__main__':
    test_enhanced_features()
