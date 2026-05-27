from __future__ import annotations

from typing import Any


class _NoOpMetric:
    def labels(self, *args: Any, **kwargs: Any) -> "_NoOpMetric":
        return self

    def inc(self, *args: Any, **kwargs: Any) -> None:
        return None

    def dec(self, *args: Any, **kwargs: Any) -> None:
        return None

    def observe(self, *args: Any, **kwargs: Any) -> None:
        return None


REQUEST_COUNT: _NoOpMetric = _NoOpMetric()
REQUEST_LATENCY: _NoOpMetric = _NoOpMetric()
IN_PROGRESS: _NoOpMetric = _NoOpMetric()
