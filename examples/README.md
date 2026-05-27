Examples
========

1) Quick start

Set environment variables (optional):

```bash
export GUARDIO_BASE=http://localhost:8000
export GUARDIO_API_KEY=devkey
```

Run the example client:

```bash
python examples/client.py
```

2) Use `curl` for quick checks

Liveness:

```bash
curl -sS http://localhost:8000/live | jq
```

List replays (requires API key):

```bash
curl -H "X-API-Key: devkey" http://localhost:8000/replays | jq
```


3) Run locally with Docker Compose

```bash
docker-compose up --build

# Prometheus will be available at http://localhost:9090
```
