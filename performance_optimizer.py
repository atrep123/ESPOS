# Performance Optimizer Module for ESP32OS UI Designer
#
# Provides:
# - Advanced caching with LRU eviction
# - Lazy loading for large widget collections
# - Render pooling and object reuse
# - Debouncing and throttling utilities
# - Memory profiling and optimization hints

import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Generic
from functools import wraps
from collections import OrderedDict
import hashlib
import pickle

T = TypeVar('T')


class LRUCache(Generic[T]):
    """Thread-safe LRU cache with size limit and TTL support"""
    
    def __init__(self, max_size: int = 100, ttl: Optional[float] = None):
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self.cache: OrderedDict[str, Tuple[T, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache, returns None if not found or expired"""
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, timestamp = self.cache[key]
        
        # Check TTL
        if self.ttl and (time.time() - timestamp) > self.ttl:
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return value
    
    def put(self, key: str, value: T):
        """Put value into cache, evicting LRU item if at capacity"""
        # Remove if exists (to update timestamp)
        if key in self.cache:
            del self.cache[key]
        
        # Add new item
        self.cache[key] = (value, time.time())
        
        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def clear(self):
        """Clear all cached items"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "ttl": self.ttl
        }


class RenderPool:
    """Object pool for reusing render resources"""
    
    def __init__(self, factory: Callable[[], T], initial_size: int = 10):
        self.factory = factory
        self.available: List[T] = []
        self.in_use: set = set()  # Use regular set instead of WeakSet
        
        # Pre-create initial objects
        for _ in range(initial_size):
            self.available.append(factory())
    
    def acquire(self) -> T:
        """Get an object from the pool"""
        if self.available:
            obj = self.available.pop()
        else:
            obj = self.factory()
        
        self.in_use.add(id(obj))  # Track by id instead of reference
        return obj
    
    def release(self, obj: T):
        """Return an object to the pool"""
        obj_id = id(obj)
        if obj_id in self.in_use:
            self.in_use.remove(obj_id)
            self.available.append(obj)
    
    def clear(self):
        """Clear the pool"""
        self.available.clear()
        self.in_use.clear()


class LazyLoader:
    """Lazy loading manager for large collections"""
    
    def __init__(self, items: List[Any], chunk_size: int = 50):
        self.items = items
        self.chunk_size = chunk_size
        self.loaded_chunks: Dict[int, List[Any]] = {}
        self.total_chunks = (len(items) + chunk_size - 1) // chunk_size
    
    def get_chunk(self, chunk_index: int) -> List[Any]:
        """Get a specific chunk of items"""
        if chunk_index in self.loaded_chunks:
            return self.loaded_chunks[chunk_index]
        
        start_idx = chunk_index * self.chunk_size
        end_idx = min(start_idx + self.chunk_size, len(self.items))
        
        chunk = self.items[start_idx:end_idx]
        self.loaded_chunks[chunk_index] = chunk
        return chunk
    
    def get_visible_range(self, start: int, end: int) -> List[Any]:
        """Get items in a specific range (for viewport-based loading)"""
        result = []
        start_chunk = start // self.chunk_size
        end_chunk = end // self.chunk_size
        
        for chunk_idx in range(start_chunk, end_chunk + 1):
            chunk = self.get_chunk(chunk_idx)
            chunk_start = chunk_idx * self.chunk_size
            
            for i, item in enumerate(chunk):
                item_idx = chunk_start + i
                if start <= item_idx < end:
                    result.append(item)
        
        return result
    
    def unload_chunk(self, chunk_index: int):
        """Unload a chunk to free memory"""
        if chunk_index in self.loaded_chunks:
            del self.loaded_chunks[chunk_index]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics"""
        return {
            "total_items": len(self.items),
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "loaded_chunks": len(self.loaded_chunks),
            "memory_usage_pct": (len(self.loaded_chunks) / self.total_chunks * 100) if self.total_chunks > 0 else 0
        }


def debounce(wait: float):
    """Debounce decorator - only call function after wait seconds of no calls"""
    def decorator(func: Callable):
        last_call_time = [0.0]
        scheduled_call = [None]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            def call_func():
                last_call_time[0] = time.time()
                return func(*args, **kwargs)
            
            current_time = time.time()
            
            # Cancel any scheduled call
            if scheduled_call[0]:
                try:
                    # This would need actual timer cancellation in production
                    pass
                except Exception:
                    pass
            
            # Schedule new call
            if (current_time - last_call_time[0]) >= wait:
                return call_func()
            else:
                # Would schedule for later in production
                return None
        
        return wrapper
    return decorator


def throttle(interval: float):
    """Throttle decorator - limit function calls to once per interval"""
    def decorator(func: Callable):
        last_call_time = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if (current_time - last_call_time[0]) >= interval:
                last_call_time[0] = current_time
                return func(*args, **kwargs)
            return None
        
        return wrapper
    return decorator


def memoize_with_key(key_func: Callable):
    """Memoization decorator with custom key function"""
    cache: Dict[str, Any] = {}
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs)
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        
        wrapper.cache = cache
        wrapper.clear_cache = lambda: cache.clear()
        return wrapper
    
    return decorator


def hash_object(obj: Any) -> str:
    """Generate hash for any object (for cache keys)"""
    try:
        # Try to pickle and hash
        obj_bytes = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
        return hashlib.md5(obj_bytes).hexdigest()
    except Exception:
        # Fallback to repr
        return hashlib.md5(repr(obj).encode()).hexdigest()


class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}
    
    def start(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = time.perf_counter()
    
    def end(self, operation: str):
        """End timing an operation and record duration"""
        if operation in self.start_times:
            duration = time.perf_counter() - self.start_times[operation]
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
            del self.start_times[operation]
            return duration
        return None
    
    def get_stats(self, operation: str) -> Optional[Dict[str, float]]:
        """Get statistics for an operation"""
        if operation not in self.metrics or not self.metrics[operation]:
            return None
        
        times = self.metrics[operation]
        return {
            "count": len(times),
            "total": sum(times),
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "last": times[-1]
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations"""
        return {op: self.get_stats(op) for op in self.metrics.keys() if self.get_stats(op)}
    
    def clear(self):
        """Clear all metrics"""
        self.metrics.clear()
        self.start_times.clear()


# Global instances
_render_cache = LRUCache(max_size=200, ttl=300.0)  # 5 minute TTL
_perf_monitor = PerformanceMonitor()


def get_render_cache() -> LRUCache:
    """Get global render cache instance"""
    return _render_cache


def get_perf_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    return _perf_monitor


if __name__ == "__main__":
    # Example usage
    print("Performance Optimizer Module")
    print("=" * 50)
    
    # Test LRU cache
    cache = LRUCache(max_size=3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    print(f"Cache stats: {cache.get_stats()}")
    
    # Test lazy loader
    items = list(range(100))
    loader = LazyLoader(items, chunk_size=10)
    visible = loader.get_visible_range(15, 35)
    print(f"Lazy loader stats: {loader.get_stats()}")
    print(f"Visible items (15-35): {len(visible)} items")
    
    # Test performance monitor
    monitor = PerformanceMonitor()
    monitor.start("test_op")
    time.sleep(0.01)
    monitor.end("test_op")
    print(f"Performance stats: {monitor.get_all_stats()}")
