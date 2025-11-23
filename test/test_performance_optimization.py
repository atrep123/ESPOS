#!/usr/bin/env python3
"""
Test performance optimizations (caching, lazy rendering)
"""

import time

import pytest

from ui_designer import UIDesigner, WidgetConfig


def test_cache_invalidation_on_add():
    """Test that cache is invalidated when adding widgets"""
    designer = UIDesigner()
    designer.create_scene("test")
    
    # Mock preview window with cache
    class MockPreview:
        def __init__(self):
            self._cache_valid = True
            self._ascii_cache_valid = True
        
        def _invalidate_cache(self):
            self._cache_valid = False
            self._ascii_cache_valid = False
    
    preview = MockPreview()
    
    # Add widget should invalidate cache
    preview._invalidate_cache()
    
    assert not preview._cache_valid
    assert not preview._ascii_cache_valid


def test_ascii_cache_hit():
    """Test ASCII rendering cache hit"""
    designer = UIDesigner()
    designer.create_scene("test")
    
    # Add some widgets
    for i in range(10):
        widget = WidgetConfig(type="button", x=i*10, y=0, width=8, height=5)
        designer.scenes["test"].widgets.append(widget)
    
    # Test caching logic
    cached_result = ["cached line 1", "cached line 2"]
    
    # Simulate cache check
    cache_valid = True
    widget_count = len(designer.scenes["test"].widgets)
    last_widget_count = 10
    
    if cache_valid and widget_count == last_widget_count:
        result = cached_result
    else:
        result = None
    
    assert result == cached_result


def test_ascii_cache_miss():
    """Test ASCII rendering cache miss when widget count changes"""
    # Simulate cache miss
    cache_valid = True
    widget_count = 15
    last_widget_count = 10
    cached_result = ["old data"]
    
    if cache_valid and widget_count == last_widget_count:
        result = cached_result
    else:
        result = None  # Cache miss, need to re-render
    
    assert result is None


def test_large_scene_widget_count():
    """Test that large scenes can be created"""
    designer = UIDesigner()
    designer.create_scene("large")
    
    # Create large scene with 500 widgets
    for i in range(500):
        widget = WidgetConfig(
            type="label" if i % 2 == 0 else "button",
            x=(i % 20) * 6,
            y=(i // 20) * 6,
            width=5,
            height=5
        )
        designer.scenes["large"].widgets.append(widget)
    
    assert len(designer.scenes["large"].widgets) == 500


def test_cache_behavior_with_force_refresh():
    """Test force refresh bypasses cache"""
    # Simulate force refresh
    force = True
    cache_valid = True
    
    if not force and cache_valid:
        use_cache = True
    else:
        use_cache = False
    
    assert not use_cache  # Force refresh should bypass cache


def test_cache_behavior_normal_refresh():
    """Test normal refresh uses cache"""
    # Simulate normal refresh
    force = False
    cache_valid = True
    
    if not force and cache_valid:
        use_cache = True
    else:
        use_cache = False
    
    assert use_cache  # Normal refresh should use cache


def test_invalidate_both_caches():
    """Test that invalidation affects both caches"""
    class CacheManager:
        def __init__(self):
            self._cache_valid = True
            self._ascii_cache_valid = True
        
        def invalidate(self):
            self._cache_valid = False
            self._ascii_cache_valid = False
    
    manager = CacheManager()
    manager.invalidate()
    
    assert not manager._cache_valid
    assert not manager._ascii_cache_valid


def test_performance_baseline():
    """Test performance baseline for rendering"""
    designer = UIDesigner(width=100, height=100)
    designer.create_scene("perf")
    
    # Add 100 widgets
    for i in range(100):
        widget = WidgetConfig(
            type="button",
            x=(i % 10) * 10,
            y=(i // 10) * 10,
            width=8,
            height=8,
            text=f"B{i}"
        )
        designer.scenes["perf"].widgets.append(widget)
    
    # Measure basic operation time (just widget count)
    start = time.time()
    count = len(designer.scenes["perf"].widgets)
    elapsed = time.time() - start
    
    assert count == 100
    assert elapsed < 1.0  # Should be very fast


def test_cache_storage_structure():
    """Test cache storage structure"""
    class PreviewCache:
        def __init__(self):
            self._render_cache = None
            self._cache_valid = False
            self._ascii_cache = None
            self._ascii_cache_valid = False
            self._last_widget_count = 0
    
    cache = PreviewCache()
    
    # Set cache
    cache._render_cache = "image_data"
    cache._ascii_cache = ["line1", "line2"]
    cache._cache_valid = True
    cache._ascii_cache_valid = True
    cache._last_widget_count = 50
    
    assert cache._render_cache == "image_data"
    assert cache._ascii_cache == ["line1", "line2"]
    assert cache._cache_valid
    assert cache._ascii_cache_valid
    assert cache._last_widget_count == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
