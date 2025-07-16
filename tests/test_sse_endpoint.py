import os
import sys
import time
import subprocess
import httpx
import pytest

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


@pytest.mark.asyncio
async def test_sse_list_tools():
    env = os.environ.copy()
    env.setdefault("MCP_PERSIST", "0")
    env.setdefault("PORT", "8133")
    proc = subprocess.Popen([
        sys.executable,
        os.path.join("src", "server.py"),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        for _ in range(20):
            try:
                httpx.get("http://127.0.0.1:8133/sse", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        async with sse_client("http://127.0.0.1:8133/sse") as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.list_tools()
                tool_names = [t.name for t in result.tools]
                assert "connect_powerbi" in tool_names
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
