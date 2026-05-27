from prometheus_client import Counter, Gauge, Histogram

# HTTP metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency",
    ["method", "path"],
)

IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Requests currently being processed",
)
