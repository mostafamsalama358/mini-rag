"""Upload leaflets/ to project 2 and process-and-push with vector reset."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

API = "http://localhost:8000"
PROJECT_ID = 2
LEAFLETS = Path(__file__).resolve().parent
OUT = Path(__file__).resolve().parents[1] / "eval_run" / "e2e_live_results"


def wait_task(task_id: str, timeout: float = 900.0) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        r = requests.get(f"{API}/api/v1/data/tasks/{task_id}", timeout=60)
        r.raise_for_status()
        last = r.json()
        state = last.get("status") or last.get("state")
        ready = last.get("ready")
        print(f"  task={task_id[:8]}… ready={ready} status={state}")
        if ready:
            return last
        time.sleep(5)
    raise TimeoutError(f"task timeout: {last}")


def upload_file(path: Path) -> str:
    with path.open("rb") as handle:
        r = requests.post(
            f"{API}/api/v1/data/upload/{PROJECT_ID}",
            files={"file": (path.name, handle, "text/plain")},
            timeout=120,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"upload {path.name}: {r.status_code} {r.text}")
    body = r.json()
    if body.get("signal") != "file_upload_success":
        raise RuntimeError(f"upload signal: {body}")
    return body.get("asset_name") or path.name


def main() -> None:
    files = sorted(LEAFLETS.glob("*.txt"))
    print(f"Uploading {len(files)} leaflets to project {PROJECT_ID}…")
    uploaded = []
    for path in files:
        name = upload_file(path)
        uploaded.append(name)
        print(f"  OK {path.name} -> {name}")

    print("process-and-push do_reset=1…")
    r = requests.post(
        f"{API}/api/v1/data/process-and-push/{PROJECT_ID}",
        json={"do_reset": 1},
        timeout=60,
    )
    r.raise_for_status()
    body = r.json()
    print(json.dumps(body, indent=2)[:800])
    task_id = body.get("task_id") or body.get("job_id")
    if not task_id:
        # some responses nest under signal payloads
        raise RuntimeError(f"no task_id in {body}")

    result = wait_task(str(task_id), timeout=1200)
    print("task result:", json.dumps(result, indent=2)[:1200])

    info = requests.get(f"{API}/api/v1/nlp/index/info/{PROJECT_ID}", timeout=60)
    info.raise_for_status()
    info_body = info.json()
    print("index info:", json.dumps(info_body, indent=2)[:1500])

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "uploaded_count": len(uploaded),
        "uploaded": uploaded,
        "process_task": result,
        "index_info": info_body,
    }
    out_path = OUT / "reindex_leaflets_web_enriched.json"
    out_path.write_text(json.dumps(stamp, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
