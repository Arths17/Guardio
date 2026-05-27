class _NoOpMetric:
    def labels(self, *args, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        return None

    def dec(self, *args, **kwargs):
        return None

    def observe(self, *args, **kwargs):
        return None


REQUEST_COUNT = _NoOpMetric()
REQUEST_LATENCY = _NoOpMetric()
IN_PROGRESS = _NoOpMetric()
