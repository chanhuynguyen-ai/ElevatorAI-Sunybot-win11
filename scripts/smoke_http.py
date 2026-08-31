"""Smoke-test an already running ElevatorAI stack using only the Python stdlib."""
import json
import os
import sys
import urllib.request

BASE = os.getenv("ELEVATORAI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def request(path, method="GET", payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main():
    checks = [
        ("/health", "GET", None),
        ("/chat", "POST", {"message": "xin chao"}),
        ("/api/elevator/status", "GET", None),
        ("/api/integration/cv/status", "GET", None),
    ]
    for path, method, payload in checks:
        status, body = request(path, method, payload)
        if status != 200:
            raise RuntimeError("{0} returned HTTP {1}".format(path, status))
        print("PASS", method, path, body.get("status") if isinstance(body, dict) else "ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
