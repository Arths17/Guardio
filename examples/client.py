"""Small example client for Guardio backend.

Usage:
  python examples/client.py

This script demonstrates health checks, listing replays, and calling AI endpoints (with AI disabled by default).
"""

import os
import requests

BASE = os.environ.get("GUARDIO_BASE", "http://localhost:8000")
API_KEY = os.environ.get("GUARDIO_API_KEY", "devkey")


def headers():
    return {"X-API-Key": API_KEY}


def live():
    r = requests.get(f"{BASE}/live")
    print("/live ->", r.status_code, r.json())


def metrics():
    r = requests.get(f"{BASE}/metrics")
    print("/metrics ->", r.status_code)


def list_replays():
    r = requests.get(f"{BASE}/replays")
    print("/replays ->", r.status_code, r.json())


def main():
    live()
    metrics()
    list_replays()


if __name__ == "__main__":
    main()
