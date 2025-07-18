import os
import subprocess
import sys
import time

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


@pytest.mark.asyncio
async def test_sse_list_tools():
    print("Starting SSE test...")
    start_time = time.time()

    env = os.environ.copy()
    env.setdefault("MCP_PERSIST", "0")
    env.setdefault("PORT", "8133")
    # Speed up server startup for testing
    env.setdefault("PYTHONNET_RUNTIME", "coreclr")
    env.setdefault("SKIP_ADOMD_LOAD", "1")  # Skip ADOMD.NET loading if supported

    print(f"Starting server process... ({time.time() - start_time:.2f}s)")
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
        print(f"Waiting for server to start... ({time.time() - start_time:.2f}s)")
        for i in range(40):  # Increase attempts to cover 20s startup time
            try:
                httpx.get("http://127.0.0.1:8133/sse", timeout=0.5)  # Shorter timeout
                print(f"Server responded on attempt {i + 1} ({time.time() - start_time:.2f}s)")
                break
            except Exception as e:
                if i < 5:  # Only print first few attempts to reduce noise
                    print(f"Attempt {i + 1} failed: {e} ({time.time() - start_time:.2f}s)")
                time.sleep(0.5)  # 500ms between attempts
        else:
            print("Server failed to start within timeout")

        print(f"Connecting to SSE... ({time.time() - start_time:.2f}s)")
        async with sse_client("http://127.0.0.1:8133/sse") as streams:
            print(f"Creating client session... ({time.time() - start_time:.2f}s)")
            async with ClientSession(*streams) as session:
                print(f"Initializing session... ({time.time() - start_time:.2f}s)")
                await session.initialize()
                print(f"Listing tools... ({time.time() - start_time:.2f}s)")
                result = await session.list_tools()
                tool_names = [t.name for t in result.tools]
                print(f"Test completed successfully! ({time.time() - start_time:.2f}s)")
                assert "connect_powerbi" in tool_names
    finally:
        print(f"Terminating server... ({time.time() - start_time:.2f}s)")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Server didn't terminate gracefully, killing...")
            proc.kill()
        print(f"Test finished. ({time.time() - start_time:.2f}s)")
