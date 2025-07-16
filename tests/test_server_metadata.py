import pytest

# Add src to path
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from server import PowerBIMCPServer


@pytest.mark.asyncio
async def test_list_tables_includes_metadata(monkeypatch):
    server = PowerBIMCPServer()
    server.is_connected = True

    monkeypatch.setattr(server.connector, 'discover_tables', lambda: ['Sales', 'Product'])
    monkeypatch.setattr(
        server.connector,
        'get_table_descriptions',
        lambda: {'Sales': 'Sales table', 'Product': 'Product table'}
    )
    monkeypatch.setattr(
        server.connector,
        'get_relationships',
        lambda: [{
            'from_table': 'Sales',
            'from_column': 'ProductID',
            'to_table': 'Product',
            'to_column': 'ID'
        }]
    )

    result = await server._handle_list_tables()

    assert 'Sales table' in result
    assert 'Sales.ProductID -> Product.ID' in result


@pytest.mark.asyncio
async def test_get_table_info_includes_metadata(monkeypatch):
    server = PowerBIMCPServer()
    server.is_connected = True

    monkeypatch.setattr(
        server.connector,
        'get_table_schema',
        lambda name: {'type': 'data_table', 'columns': ['ID', 'Name']}
    )
    monkeypatch.setattr(server.connector, 'get_sample_data', lambda n, num: [])
    monkeypatch.setattr(server.connector, 'get_table_descriptions', lambda: {'Sales': 'Sales desc'})
    monkeypatch.setattr(server.connector, 'get_column_descriptions', lambda t: {'ID': 'identifier', 'Name': ''})
    monkeypatch.setattr(
        server.connector,
        'get_relationships_for_table',
        lambda t: [{
            'from_table': 'Sales',
            'from_column': 'ProductID',
            'to_table': 'Product',
            'to_column': 'ID'
        }]
    )

    result = await server._handle_get_table_info({'table_name': 'Sales'})

    assert 'Description: Sales desc' in result
    assert '- ID: identifier' in result
    assert 'Sales.ProductID -> Product.ID' in result
