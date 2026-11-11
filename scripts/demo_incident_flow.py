from __future__ import annotations

import argparse
import json
from typing import Any
from urllib import error, request


def call_json(url: str, payload: dict[str, Any] | None = None, method: str = "GET") -> Any:
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
    parser = argparse.ArgumentParser(description="Run a smoke-test incident analysis flow against the local API.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--incident", default="INC-001", help="Incident ID to investigate")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    analyze_url = f"{base_url}/api/v1/investigations/analyze"
    approve_url = f"{base_url}/api/v1/investigations/approve"
    history_url = f"{base_url}/api/v1/investigations/history/{args.incident}"

    analysis = call_json(analyze_url, {"incident_id": args.incident}, method="POST")
    print(f"Incident: {analysis.get('incident_id')} | Service: {analysis.get('service')} | Confidence: {analysis.get('confidence')}")
    print(f"Summary: {analysis.get('summary')}")

    approval = call_json(approve_url, {"incident_id": args.incident, "decision": "approve"}, method="POST")
    print(f"Approval: {approval.get('approval_status')} | Message: {approval.get('message')}")

    history = call_json(history_url)
    print(f"History entries: {len(history)}")
    if history:
        latest = history[-1]
        print(f"Latest decision: {latest.get('decision')} ({latest.get('status')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
