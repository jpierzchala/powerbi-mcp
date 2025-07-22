import os
import subprocess
import sys
import time

import pytest


@pytest.mark.local
def test_server_stays_running():
    env = os.environ.copy()
    env.setdefault("MCP_PERSIST", "1")
    env.setdefault("PORT", "8123")
    proc = subprocess.Popen(
        [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "..", "src", "server.py"),
            "--port",
            "8123",  # Explicitly pass port argument
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        # Wait a bit for server to initialize, then check it's still running
        for i in range(5):  # 5 seconds should be enough for initialization
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                assert False, f"Server process died unexpectedly after {i}s: {stderr.decode()}"
            time.sleep(1.0)

        # Final check - server should still be running after 5 seconds
        assert proc.poll() is None, "Server process should still be running"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
