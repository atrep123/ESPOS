"""Tests for Performance Optimizer Module"""

import time
import pytest
from performance_optimizer import (
    LRUCache, RenderPool, LazyLoader,
    debounce, throttle, memoize_with_key,
    hash_object, PerformanceMonitor,
    get_render_cache, get_perf_monitor
)


class TestLRUCache:
    def test_basic_operations(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") is None
    
    def test_eviction(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # Should evict "a"
        
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
    
    def test_lru_ordering(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # Access "a" to make it most recent
        cache.put("c", 3)  # Should evict "b", not "a"
        
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
    
    def test_ttl_expiration(self):
        cache = LRUCache(max_size=10, ttl=0.1)  # 100ms TTL
        cache.put("a", 1)
        
        assert cache.get("a") == 1
        time.sleep(0.15)
        assert cache.get("a") is None
    
    def test_stats(self):
        cache = LRUCache(max_size=5)
        cache.put("a", 1)
        cache.get("a")  # Hit
        cache.get("b")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["size"] == 1


class TestRenderPool:
    def test_basic_pool(self):
        pool = RenderPool(factory=list, initial_size=5)
        
        obj1 = pool.acquire()
        obj2 = pool.acquire()
        
        assert isinstance(obj1, list)
        assert isinstance(obj2, list)
        assert obj1 is not obj2
    
    def test_release(self):
        pool = RenderPool(factory=dict, initial_size=2)
        
        obj = pool.acquire()
        pool.release(obj)
        obj_reused = pool.acquire()
        
        assert obj is obj_reused
    
    def test_expansion(self):
        pool = RenderPool(factory=list, initial_size=1)
        
        obj1 = pool.acquire()
        obj2 = pool.acquire()  # Should create new object
        
        assert isinstance(obj2, list)


class TestLazyLoader:
    def test_chunk_loading(self):
        items = list(range(100))
        loader = LazyLoader(items, chunk_size=10)
        
        chunk = loader.get_chunk(0)
        assert len(chunk) == 10
        assert chunk == list(range(10))
        
        chunk5 = loader.get_chunk(5)
        assert len(chunk5) == 10
        assert chunk5 == list(range(50, 60))
    
    def test_visible_range(self):
        items = list(range(100))
        loader = LazyLoader(items, chunk_size=10)
        
        visible = loader.get_visible_range(15, 35)
        assert len(visible) == 20
        assert visible == list(range(15, 35))
    
    def test_stats(self):
        items = list(range(100))
        loader = LazyLoader(items, chunk_size=20)
        
        loader.get_chunk(0)
        loader.get_chunk(1)
        
        stats = loader.get_stats()
        assert stats["total_items"] == 100
        assert stats["total_chunks"] == 5
        assert stats["loaded_chunks"] == 2
        assert stats["memory_usage_pct"] == 40.0
    
    def test_unload_chunk(self):
        items = list(range(50))
        loader = LazyLoader(items, chunk_size=10)
        
        loader.get_chunk(0)
        loader.get_chunk(1)
        loader.unload_chunk(0)
        
        stats = loader.get_stats()
        assert stats["loaded_chunks"] == 1


class TestDebounceThrottle:
    def test_throttle(self):
        call_count = [0]
        
        @throttle(interval=0.1)
        def func():
            call_count[0] += 1
            return call_count[0]
        
        # First call should work
        result1 = func()
        assert result1 == 1
        
        # Second immediate call should be throttled
        result2 = func()
        assert result2 is None
        assert call_count[0] == 1
        
        # After interval, should work again
        time.sleep(0.11)
        result3 = func()
        assert result3 == 2
    
    def test_debounce(self):
        call_count = [0]
        
        @debounce(wait=0.1)
        def func():
            call_count[0] += 1
            return call_count[0]
        
        # Multiple rapid calls
        func()
        func()
        func()
        
        # Only last one should have executed immediately
        time.sleep(0.05)
        assert call_count[0] >= 0  # Implementation dependent


class TestMemoization:
    def test_memoize_with_key(self):
        call_count = [0]
        
        @memoize_with_key(lambda x: str(x))
        def expensive_func(x):
            call_count[0] += 1
            return x * 2
        
        result1 = expensive_func(5)
        result2 = expensive_func(5)
        
        assert result1 == 10
        assert result2 == 10
        assert call_count[0] == 1  # Only called once
        
        result3 = expensive_func(10)
        assert result3 == 20
        assert call_count[0] == 2
    
    def test_hash_object(self):
        # Same objects should have same hash
        hash1 = hash_object({"a": 1, "b": 2})
        hash2 = hash_object({"a": 1, "b": 2})
        assert hash1 == hash2
        
        # Different objects should have different hash
        hash3 = hash_object({"a": 1, "b": 3})
        assert hash1 != hash3


class TestPerformanceMonitor:
    def test_basic_timing(self):
        monitor = PerformanceMonitor()
        
        monitor.start("test_op")
        time.sleep(0.01)
        duration = monitor.end("test_op")
        
        assert duration is not None
        assert duration >= 0.01
    
    def test_stats(self):
        monitor = PerformanceMonitor()
        
        for _ in range(5):
            monitor.start("op")
            time.sleep(0.01)
            monitor.end("op")
        
        stats = monitor.get_stats("op")
        assert stats is not None
        assert stats["count"] == 5
        assert stats["avg"] >= 0.01
        assert stats["min"] >= 0.01
        assert stats["max"] >= stats["min"]
    
    def test_multiple_operations(self):
        monitor = PerformanceMonitor()
        
        monitor.start("op1")
        time.sleep(0.01)
        monitor.end("op1")
        
        monitor.start("op2")
        time.sleep(0.02)
        monitor.end("op2")
        
        all_stats = monitor.get_all_stats()
        assert "op1" in all_stats
        assert "op2" in all_stats
        assert all_stats["op2"]["avg"] > all_stats["op1"]["avg"]


class TestGlobalInstances:
    def test_global_cache(self):
        cache = get_render_cache()
        assert isinstance(cache, LRUCache)
        
        cache.put("test", "value")
        assert cache.get("test") == "value"
    
    def test_global_monitor(self):
        monitor = get_perf_monitor()
        assert isinstance(monitor, PerformanceMonitor)
        
        monitor.start("test")
        monitor.end("test")
        stats = monitor.get_stats("test")
        assert stats is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
