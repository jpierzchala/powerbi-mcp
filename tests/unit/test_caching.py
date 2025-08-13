"""
Unit tests for per-model caching and invalidation in PowerBIConnector.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from server import PowerBIConnector  # noqa: E402


@pytest.mark.unit
class TestPerModelCaching:
    def _make_connected_connector(self) -> PowerBIConnector:
        connector = PowerBIConnector()
        connector.connected = True
        connector.connection_string = "test-connection"
        return connector

    def test_tables_cache_is_per_model_key(self):
        connector = self._make_connected_connector()

        # Freeze model update marker
        connector._get_model_last_update_marker = lambda: datetime(2024, 1, 1)  # type: ignore

        # Model A
        connector.model_key = "endpoint|ModelA"
        connector.schema_service.discover_tables = lambda: [  # type: ignore
            {"name": "A_Table1", "description": "desc", "relationships": []}
        ]
        tables_a_first = connector.discover_tables()
        assert tables_a_first and tables_a_first[0]["name"] == "A_Table1"

        # Model B
        connector.model_key = "endpoint|ModelB"
        connector.schema_service.discover_tables = lambda: [  # type: ignore
            {"name": "B_Table1", "description": "desc", "relationships": []}
        ]
        tables_b_first = connector.discover_tables()
        assert tables_b_first and tables_b_first[0]["name"] == "B_Table1"

        # Switch back to Model A - should return cached A without calling service
        connector.model_key = "endpoint|ModelA"
        # If service is called, it would return the B-specific stub; the cache must win
        connector.schema_service.discover_tables = lambda: [  # type: ignore
            {"name": "A_Table_SHOULD_NOT_BE_USED", "description": "desc", "relationships": []}
        ]
        tables_a_again = connector.discover_tables()
        assert tables_a_again and tables_a_again[0]["name"] == "A_Table1"

    def test_tables_cache_invalidates_on_marker_change(self):
        connector = self._make_connected_connector()

        t1 = datetime(2024, 1, 1)
        t2 = t1 + timedelta(days=1)

        connector.model_key = "endpoint|ModelA"
        connector._get_model_last_update_marker = lambda: t1  # type: ignore
        connector.schema_service.discover_tables = lambda: [  # type: ignore
            {"name": "A_Table1", "description": "desc", "relationships": []}
        ]
        tables_first = connector.discover_tables()
        assert tables_first and tables_first[0]["name"] == "A_Table1"

        # Simulate model update and new data
        connector._get_model_last_update_marker = lambda: t2  # type: ignore
        connector.schema_service.discover_tables = lambda: [  # type: ignore
            {"name": "A_Table2", "description": "desc", "relationships": []}
        ]
        tables_after_update = connector.discover_tables()
        assert tables_after_update and tables_after_update[0]["name"] == "A_Table2"

    def test_table_schema_cache_per_model_and_invalidation(self):
        connector = self._make_connected_connector()

        t1 = datetime(2024, 2, 1)
        t2 = t1 + timedelta(hours=1)

        # Model X
        connector.model_key = "endpoint|ModelX"
        connector._get_model_last_update_marker = lambda: t1  # type: ignore
        connector.schema_service.get_table_schema = lambda name: {  # type: ignore
            "table_name": name,
            "type": "data_table",
            "description": "descX",
            "columns": [{"name": f"{name}[Id]", "description": "id", "data_type": 6}],
        }
        schema_x_first = connector.get_table_schema("TableX")
        assert schema_x_first["description"] == "descX"

        # Switch to Model Y
        connector.model_key = "endpoint|ModelY"
        connector.schema_service.get_table_schema = lambda name: {  # type: ignore
            "table_name": name,
            "type": "data_table",
            "description": "descY",
            "columns": [{"name": f"{name}[Id]", "description": "id", "data_type": 6}],
        }
        schema_y_first = connector.get_table_schema("TableX")
        assert schema_y_first["description"] == "descY"

        # Back to Model X, should return cached descX
        connector.model_key = "endpoint|ModelX"
        connector.schema_service.get_table_schema = lambda name: {  # type: ignore
            "table_name": name,
            "type": "data_table",
            "description": "descX-NEW-SHOULD-NOT-APPEAR",
            "columns": [{"name": f"{name}[Id]", "description": "id", "data_type": 6}],
        }
        schema_x_again = connector.get_table_schema("TableX")
        assert schema_x_again["description"] == "descX"

        # Invalidate Model X by advancing marker
        connector._get_model_last_update_marker = lambda: t2  # type: ignore
        schema_x_after_update = connector.get_table_schema("TableX")
        assert schema_x_after_update["description"] == "descX-NEW-SHOULD-NOT-APPEAR"


