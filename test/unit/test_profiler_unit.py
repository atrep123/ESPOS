#!/usr/bin/env python3
from performance_profiler import PerformanceProfiler, AlertSeverity


def test_profiler_records_frames_and_alerts():
    profiler = PerformanceProfiler(enable_alerting=True, enable_anomaly_detection=False)
    # clear default alerts and add a deterministic one
    profiler.alert_rules = [
        # trigger when fps < 30
        profiler.alert_rules[0].__class__("low_fps", "fps", 30.0, "<", AlertSeverity.WARNING)
    ]

    # record a few "good" frames
    for _ in range(5):
        profiler.record_frame(fps=60.0, render_ms=10.0, event_ms=1.0)

    assert len(profiler.metrics) == 5
    assert not profiler.alerts

    # record a "bad" frame to trigger the alert
    profiler.record_frame(fps=15.0, render_ms=10.0, event_ms=1.0)
    assert profiler.alerts
    alert = profiler.alerts[-1]
    assert alert.rule_name == "low_fps"
    assert alert.severity == AlertSeverity.WARNING

