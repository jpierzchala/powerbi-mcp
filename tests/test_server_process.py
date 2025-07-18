import os
import subprocess
import sys
import time

import httpx


def test_server_stays_running():
    env = os.environ.copy()
    env.setdefault("MCP_PERSIST", "1")
    env.setdefault("PORT", "8123")
    proc = subprocess.Popen(
        [
            sys.executable,
            os.path.join("src", "server.py"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        # Wait for server to start
        for _ in range(10):
            try:
                httpx.get("http://127.0.0.1:8123/", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        assert proc.poll() is None
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
