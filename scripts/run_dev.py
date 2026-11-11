from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parents[1]


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def find_free_port(start_port: int, max_tries: int = 30) -> int:
    for port in range(start_port, start_port + max_tries):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + max_tries - 1}")


def wait_for_http(url: str, timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Service at {url} did not become ready within {timeout_seconds} seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run backend and frontend together for local AEGIS development.")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    args = parser.parse_args()

    backend_port = args.backend_port
    if not is_port_available(backend_port):
        backend_port = find_free_port(args.backend_port)
        print(f"Port {args.backend_port} is busy; using backend port {backend_port} instead.")

    frontend_port = args.frontend_port
    if not is_port_available(frontend_port):
        frontend_port = find_free_port(args.frontend_port)
        print(f"Port {args.frontend_port} is busy; using frontend port {frontend_port} instead.")

    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(ROOT / "backend")

    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(backend_port)],
        cwd=str(ROOT / "backend"),
        env=backend_env,
    )

    try:
        wait_for_http(f"http://127.0.0.1:{backend_port}/health")
    except Exception:
        backend.terminate()
        raise

    frontend_env = os.environ.copy()
    frontend_env["VITE_API_BASE_URL"] = f"http://localhost:{backend_port}"

    frontend = subprocess.Popen(
        ["npm.cmd" if os.name == "nt" else "npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", str(frontend_port)],
        cwd=str(ROOT / "frontend"),
        env=frontend_env,
    )

    print(f"Backend: http://localhost:{backend_port}")
    print(f"Frontend: http://localhost:{frontend_port}")
    print("Press Ctrl+C to stop both processes.")

    try:
        backend.wait()
    except KeyboardInterrupt:
        print("Stopping development services...")
    finally:
        frontend.terminate()
        backend.terminate()
        exit_codes = [p.wait(timeout=10) for p in (frontend, backend)]
        print(f"Exit codes: {exit_codes}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
