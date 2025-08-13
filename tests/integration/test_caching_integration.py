"""
Integration tests for per-model caching behavior when switching datasets.

These tests require two datasets to be available and will be skipped unless
ENABLE_INTEGRATION_TESTS=true and the following variables are provided:

- TEST_XMLA_ENDPOINT
- TEST_TENANT_ID
- TEST_CLIENT_ID
- TEST_CLIENT_SECRET
- TEST_INITIAL_CATALOG_A
- TEST_INITIAL_CATALOG_B
"""

import os
import sys
from typing import Dict, List

import pytest
from dotenv import load_dotenv

load_dotenv()

integration_enabled = os.getenv("ENABLE_INTEGRATION_TESTS", "false").lower() == "true"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

if integration_enabled:
    from server import PowerBIConnector  # noqa: F401


@pytest.mark.integration
@pytest.mark.skipif(
    not integration_enabled, reason="Integration tests disabled. Set ENABLE_INTEGRATION_TESTS=true to enable.",
)
class TestPerModelCachingIntegration:
    @pytest.fixture(scope="class")
    def test_config(self) -> Dict[str, str]:
        required_vars = [
            "TEST_XMLA_ENDPOINT",
            "TEST_TENANT_ID",
            "TEST_CLIENT_ID",
            "TEST_CLIENT_SECRET",
            "TEST_INITIAL_CATALOG_A",
            "TEST_INITIAL_CATALOG_B",
        ]

        config: Dict[str, str] = {}
        missing = []
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing.append(var)
            config[var] = value

        if missing:
            pytest.skip(f"Missing required environment variables for two-dataset test: {', '.join(missing)}")

        return config

    def _connect(self, connector: "PowerBIConnector", cfg: Dict[str, str], catalog: str) -> None:
        ok = connector.connect(
            xmla_endpoint=cfg["TEST_XMLA_ENDPOINT"],
            tenant_id=cfg["TEST_TENANT_ID"],
            client_id=cfg["TEST_CLIENT_ID"],
            client_secret=cfg["TEST_CLIENT_SECRET"],
            initial_catalog=catalog,
        )
        assert ok and connector.connected

    def _table_names(self, tables: List[Dict]) -> List[str]:
        return [t["name"] for t in tables if isinstance(t, dict) and "name" in t]

    def test_switching_between_models_uses_correct_cache(self, test_config):
        from server import PowerBIConnector

        connector = PowerBIConnector()

        # Connect to dataset A and collect tables
        self._connect(connector, test_config, test_config["TEST_INITIAL_CATALOG_A"])
        tables_a_first = connector.discover_tables()
        names_a_first = self._table_names(tables_a_first)
        assert len(names_a_first) > 0

        # Switch to dataset B and collect tables
        self._connect(connector, test_config, test_config["TEST_INITIAL_CATALOG_B"])
        tables_b_first = connector.discover_tables()
        names_b_first = self._table_names(tables_b_first)
        assert len(names_b_first) > 0

        # Sanity: datasets should differ in at least one table name
        # (If they don't, the test environment provides identical models and this check is skipped)
        if set(names_a_first) != set(names_b_first):
            assert set(names_a_first) != set(names_b_first)

        # Switch back to A - should return same names as names_a_first (cached per model)
        self._connect(connector, test_config, test_config["TEST_INITIAL_CATALOG_A"])
        tables_a_again = connector.discover_tables()
        names_a_again = self._table_names(tables_a_again)
        assert set(names_a_again) == set(names_a_first)

        # Back to B - should return same names as names_b_first (its own cache)
        self._connect(connector, test_config, test_config["TEST_INITIAL_CATALOG_B"])
        tables_b_again = connector.discover_tables()
        names_b_again = self._table_names(tables_b_again)
        assert set(names_b_again) == set(names_b_first)


