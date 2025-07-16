import os
import json
import traceback
import re
import pytest
import pytest_asyncio

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import PowerBIMCPServer


@pytest_asyncio.fixture(scope="module")
async def connected_server():
    server = PowerBIMCPServer()
    try:
        result = await server._handle_connect(
            {
                "xmla_endpoint": os.environ["DEFAULT_ENDPOINT"],
                "tenant_id": os.environ["DEFAULT_TENANT_ID"],
                "client_id": os.environ["DEFAULT_CLIENT_ID"],
                "client_secret": os.environ["DEFAULT_CLIENT_SECRET"],
                "initial_catalog": os.environ["DEFAULT_CATALOG"],
            }
        )
    except Exception:
        print("\n--- CONNECT FAILURE DEBUG ---")
        tb = traceback.format_exc()
        print(tb)
        hosts = set(re.findall(r"([A-Za-z0-9.-]+\.analysis\.windows\.net)", tb))
        if hosts:
            print("Candidate blocked Analysis hosts:", ", ".join(sorted(hosts)))
        raise
    if "Successfully connected" not in result:
        pytest.fail(f"Connection failed: {result}")
    return server


@pytest.mark.asyncio
async def test_list_tables_live(connected_server):
    result = await connected_server._handle_list_tables()
    assert "Available tables:" in result
    tables = [line[2:] for line in result.splitlines() if line.startswith("- ")]
    assert tables, "No tables returned"


@pytest.mark.asyncio
async def test_get_table_info_live(connected_server):
    list_result = await connected_server._handle_list_tables()
    tables = [line[2:] for line in list_result.splitlines() if line.startswith("- ")]
    assert tables, "No tables returned to inspect"
    table = tables[0]
    info = await connected_server._handle_get_table_info({"table_name": table})
    assert f"Table: {table}" in info


@pytest.mark.asyncio
async def test_execute_dax_live(connected_server):
    list_result = await connected_server._handle_list_tables()
    tables = [line[2:] for line in list_result.splitlines() if line.startswith("- ")]
    assert tables, "No tables returned to query"
    table = tables[0]
    query = f"EVALUATE TOPN(1, '{table}')"
    raw = await connected_server._handle_execute_dax({"dax_query": query})
    data = json.loads(raw)
    assert isinstance(data, list)
    assert data, "Query returned no rows"
