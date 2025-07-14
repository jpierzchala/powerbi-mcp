import os
import pytest
import asyncio
from mcp import types as mcp_types

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from server import PowerBIMCPServer

@pytest.mark.asyncio
async def test_connect_without_openai(monkeypatch):
    server = PowerBIMCPServer()

    # Patch connector.connect to avoid real connection
    def fake_connect(xmla, tenant, client, secret, catalog):
        return True
    monkeypatch.setattr(server.connector, 'connect', fake_connect)

    # Track if context preparation was called
    called = False
    async def fake_prepare():
        nonlocal called
        called = True
    monkeypatch.setattr(server, '_async_prepare_context', fake_prepare)

    # Ensure OPENAI_API_KEY is not set
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)

    result = await server._handle_connect({
        'xmla_endpoint': 'powerbi://test',
        'tenant_id': 't',
        'client_id': 'c',
        'client_secret': 's',
        'initial_catalog': 'd'
    })

    assert 'Successfully connected' in result
    assert server.is_connected is True
    assert server.analyzer is None
    assert called is False


@pytest.mark.asyncio
async def test_list_tools_without_openai(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    server = PowerBIMCPServer()
    handler = server.server.request_handlers[mcp_types.ListToolsRequest]
    result = await handler(mcp_types.ListToolsRequest(method='tools/list'))
    tool_names = [t.name for t in result.root.tools]
    assert 'query_data' not in tool_names
    assert 'suggest_questions' not in tool_names


@pytest.mark.asyncio
async def test_call_query_data_without_openai(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    server = PowerBIMCPServer()
    handler = server.server.request_handlers[mcp_types.CallToolRequest]
    req = mcp_types.CallToolRequest(
        method='tools/call',
        params=mcp_types.CallToolRequestParams(
            name='query_data', arguments={'question': 'hi'}
        )
    )
    result = await handler(req)
    text = result.root.content[0].text
    assert 'OpenAI API key not configured' in text
