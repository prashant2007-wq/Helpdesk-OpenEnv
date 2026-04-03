#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _get(url: str, timeout_s: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body


def _post(url: str, data: dict, timeout_s: int = 20) -> tuple[int, str]:
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body


def main() -> None:
    base = os.environ.get("SPACE_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not base:
        raise SystemExit("Usage: SPACE_URL=https://huggingface.co/spaces/<u>/<s> python scripts/ping_space.py")

    base = base.rstrip("/")
    health_url = f"{base}/health"
    reset_url = f"{base}/reset"

    try:
        status, _ = _get(health_url)
        if status != 200:
            raise SystemExit(f"/health returned {status} (expected 200)")
        status, body = _post(reset_url, {"task_id": "triage_easy"})
        if status != 200:
            raise SystemExit(f"/reset returned {status} (expected 200): {body[:400]}")
        print(json.dumps({"ok": True, "health": 200, "reset": 200}, indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise SystemExit(f"HTTPError {e.code} for {e.url}: {body[:400]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"URLError: {e}")


if __name__ == "__main__":
    main()

