from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]


def call_json(url: str, payload: dict[str, object] | None = None, method: str = "GET") -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Request failed for {url}: {exc.code} {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the AEGIS app end-to-end.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--incident", default="INC-001", help="Incident ID to validate")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    health = call_json(f"{base_url}/api/v1/health")
    print(f"Health status: {health.get('status', 'unknown')}")

    analysis = call_json(f"{base_url}/api/v1/investigations/analyze", {"incident_id": args.incident}, method="POST")
    print(f"Analysis: {analysis.get('incident_id')} | {analysis.get('service')} | confidence={analysis.get('confidence')}")

    approval = call_json(f"{base_url}/api/v1/investigations/approve", {"incident_id": args.incident, "decision": "approve"}, method="POST")
    print(f"Approval: {approval.get('approval_status')} | {approval.get('message')}")

    history = call_json(f"{base_url}/api/v1/investigations/history/{args.incident}")
    print(f"History entries: {len(history)}")

    frontend_dir = ROOT / "frontend"
    npm_cmd = ["npm.cmd", "run", "build"] if os.name == "nt" else ["npm", "run", "build"]
    build = subprocess.run(npm_cmd, cwd=frontend_dir, capture_output=True, text=True)
    print(f"Frontend build exit: {build.returncode}")
    if build.stdout:
        print(build.stdout.strip().splitlines()[-3])
    if build.stderr:
        print(build.stderr.strip().splitlines()[-3])

    if build.returncode != 0:
        return build.returncode

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI failure path
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
