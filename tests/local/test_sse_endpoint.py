import os
import subprocess
import sys
import time

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


@pytest.mark.local
@pytest.mark.asyncio
async def test_sse_list_tools():
    print("Starting SSE test...")
    start_time = time.time()

    env = os.environ.copy()
    env.setdefault("MCP_PERSIST", "1")  # Keep server running during test
    env.setdefault("PORT", "8133")
    # Speed up server startup for testing
    env.setdefault("PYTHONNET_RUNTIME", "coreclr")
    env.setdefault("SKIP_ADOMD_LOAD", "1")  # Skip ADOMD.NET loading if supported

    print(f"Starting server process... ({time.time() - start_time:.2f}s)")
    proc = subprocess.Popen(
        [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "..", "..", "src", "server.py"),
            "--port",
            "8133",  # Explicitly pass port argument
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    try:
        print(f"Waiting for server to start... ({time.time() - start_time:.2f}s)")
        # Wait for server startup by checking if process is running and give it time
        for i in range(15):  # 15 seconds should be enough
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                print(f"Server process died: stdout={stdout.decode()}, stderr={stderr.decode()}")
                assert False, "Server process died unexpectedly"

            time.sleep(1.0)
            # Try a simple health check - SSE endpoint should accept connections
            try:
                # Don't wait for response, just try to connect
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(("127.0.0.1", 8133))
                sock.close()
                if result == 0:
                    print(f"Server is listening on attempt {i + 1} ({time.time() - start_time:.2f}s)")
                    break
            except Exception as e:
                print(f"Socket test {i + 1} failed: {e} ({time.time() - start_time:.2f}s)")
        else:
            print("Server failed to start listening within timeout")
            # Print server output for debugging
            if proc.poll() is None:
                proc.terminate()
                try:
                    stdout, stderr = proc.communicate(timeout=5)
                    print(f"Server stdout: {stdout.decode()}")
                    print(f"Server stderr: {stderr.decode()}")
                except subprocess.TimeoutExpired:
                    proc.kill()
                    print("Server did not terminate, killed")
            else:
                stdout, stderr = proc.communicate()
                print(f"Server stdout: {stdout.decode()}")
                print(f"Server stderr: {stderr.decode()}")
            assert False, "Server failed to start within 15 seconds"

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
