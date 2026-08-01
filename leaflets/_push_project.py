"""Trigger process-and-push after workbook upload."""
from __future__ import annotations

import json
import sys
import time

import requests

API = "http://localhost:8000"
PROJECT_ID = 2


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    response = requests.post(
        f"{API}/api/v1/data/process-and-push/{PROJECT_ID}",
        json={"do_reset": 1},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    print(json.dumps(body, indent=2))
    task_id = body.get("task_id") or body.get("job_id")
    if not task_id:
        raise SystemExit("no task_id")

    deadline = time.time() + 1800
    last = {}
    while time.time() < deadline:
        poll = requests.get(f"{API}/api/v1/data/tasks/{task_id}", timeout=60)
        if poll.status_code >= 500:
            print(f"poll HTTP {poll.status_code}; retrying")
            time.sleep(10)
            continue
        poll.raise_for_status()
        last = poll.json()
        print(f"ready={last.get('ready')} status={last.get('status')}")
        if last.get("ready"):
            print(json.dumps(last, indent=2)[:2000])
            break
        time.sleep(8)
    else:
        raise TimeoutError(last)

    info = requests.get(f"{API}/api/v1/nlp/index/info/{PROJECT_ID}", timeout=60)
    info.raise_for_status()
    print("index info:", json.dumps(info.json(), indent=2)[:1500])


if __name__ == "__main__":
    main()
