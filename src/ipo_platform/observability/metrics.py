"""
In-Memory Thread-Safe Metrics Collection Layer for Indian IPO Platform.
Provides Counter, Gauge, and Timer/Histogram primitives with tag support and statistical summaries.
"""

from collections import defaultdict
from contextlib import contextmanager
import functools
import threading
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


def _tags_to_key(tags: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
    """Converts a tag dictionary to an immutable sorted tuple key."""
    if not tags:
        return ()
    return tuple(sorted((str(k), str(v)) for k, v in tags.items()))


class Counter:
    """Thread-safe monotonic or additive counter."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        if value < 0:
            raise ValueError("Counter increments must be non-negative")
        key = _tags_to_key(tags)
        with self._lock:
            self._values[key] += value

    def get(self, tags: Optional[Dict[str, str]] = None) -> float:
        key = _tags_to_key(tags)
        with self._lock:
            return self._values.get(key, 0.0)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "type": "counter",
                "description": self.description,
                "values": [
                    {"tags": dict(key), "value": val} for key, val in self._values.items()
                ],
            }


class Gauge:
    """Thread-safe gauge representing an instantaneous value."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        key = _tags_to_key(tags)
        with self._lock:
            self._values[key] = float(value)

    def get(self, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        key = _tags_to_key(tags)
        with self._lock:
            return self._values.get(key)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "type": "gauge",
                "description": self.description,
                "values": [
                    {"tags": dict(key), "value": val} for key, val in self._values.items()
                ],
            }


class Timer:
    """
    Thread-safe timer for latency and duration measurement.
    Calculates count, total duration, mean, p95, and p99 percentiles.
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._samples: Dict[Tuple[Tuple[str, str], ...], List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def observe(self, duration_seconds: float, tags: Optional[Dict[str, str]] = None) -> None:
        key = _tags_to_key(tags)
        with self._lock:
            self._samples[key].append(float(duration_seconds))

    @contextmanager
    def time(self, tags: Optional[Dict[str, str]] = None) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.observe(elapsed, tags=tags)

    def wrap(self, tags: Optional[Dict[str, str]] = None) -> Callable[..., Any]:
        """Decorator to measure execution latency of functions."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.time(tags=tags):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def stats(self, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        key = _tags_to_key(tags)
        with self._lock:
            values = sorted(self._samples.get(key, []))

        count = len(values)
        if count == 0:
            return {
                "count": 0,
                "total_seconds": 0.0,
                "mean_seconds": 0.0,
                "min_seconds": 0.0,
                "max_seconds": 0.0,
                "p50_seconds": 0.0,
                "p95_seconds": 0.0,
                "p99_seconds": 0.0,
            }

        total = sum(values)
        mean = total / count
        p50 = values[int(count * 0.50)]
        p95 = values[min(int(count * 0.95), count - 1)]
        p99 = values[min(int(count * 0.99), count - 1)]

        return {
            "count": count,
            "total_seconds": round(total, 6),
            "mean_seconds": round(mean, 6),
            "min_seconds": round(values[0], 6),
            "max_seconds": round(values[-1], 6),
            "p50_seconds": round(p50, 6),
            "p95_seconds": round(p95, 6),
            "p99_seconds": round(p99, 6),
        }

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            keys = list(self._samples.keys())

        result = []
        for key in keys:
            tag_dict = dict(key)
            result.append({
                "tags": tag_dict,
                "stats": self.stats(tag_dict),
            })
        return {
            "name": self.name,
            "type": "timer",
            "description": self.description,
            "values": result,
        }


class MetricsRegistry:
    """Registry coordinating all platform metric instruments."""

    def __init__(self) -> None:
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._timers: Dict[str, Timer] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, description: str = "") -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description)
            return self._counters[name]

    def gauge(self, name: str, description: str = "") -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description)
            return self._gauges[name]

    def timer(self, name: str, description: str = "") -> Timer:
        with self._lock:
            if name not in self._timers:
                self._timers[name] = Timer(name, description)
            return self._timers[name]

    def snapshot(self) -> Dict[str, Any]:
        """Returns snapshot of all registered metrics."""
        with self._lock:
            counters = [c.snapshot() for c in self._counters.values()]
            gauges = [g.snapshot() for g in self._gauges.values()]
            timers = [t.snapshot() for t in self._timers.values()]

        return {
            "timestamp": time.time(),
            "counters": counters,
            "gauges": gauges,
            "timers": timers,
        }

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._timers.clear()


# Default global singleton registry
default_registry = MetricsRegistry()
