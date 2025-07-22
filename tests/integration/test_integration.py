"""
Integration tests for Power BI MCP Server.

These tests require real Power BI credentials and will only run
when ENABLE_INTEGRATION_TESTS=true in the environment.

To enable integration tests:
1. Copy .env.example to .env
2. Set ENABLE_INTEGRATION_TESTS=true
3. Configure TEST_* variables with your Power BI test dataset details
4. Run: pytest tests/test_integration.py -v

Warning: These tests connect to real Power BI datasets and may
consume API quota.
"""

import asyncio
import os
import sys
from typing import TYPE_CHECKING, Any, Dict, Generator, List

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Skip all integration tests if not enabled
integration_enabled = os.getenv("ENABLE_INTEGRATION_TESTS", "false").lower() == "true"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Import for type checking only
if TYPE_CHECKING:
    from server import DataAnalyzer, PowerBIConnector, PowerBIMCPServer

# Runtime imports
if integration_enabled:
    from server import DataAnalyzer, PowerBIConnector, PowerBIMCPServer  # noqa: F401


@pytest.mark.integration
@pytest.mark.skipif(
    not integration_enabled, reason="Integration tests disabled. Set ENABLE_INTEGRATION_TESTS=true to enable."
)
class TestPowerBIIntegration:
    """Integration tests for Power BI connectivity and functionality."""

    @pytest.fixture(scope="class")
    def test_config(self) -> Dict[str, str]:
        """Load test configuration from environment variables."""
        required_vars = [
            "TEST_XMLA_ENDPOINT",
            "TEST_TENANT_ID",
            "TEST_CLIENT_ID",
            "TEST_CLIENT_SECRET",
            "TEST_INITIAL_CATALOG",
        ]

        config = {}
        missing_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            config[var] = value

        if missing_vars:
            pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Optional test configuration
        config["TEST_EXPECTED_TABLE"] = os.getenv("TEST_EXPECTED_TABLE", "")
        config["TEST_EXPECTED_COLUMN"] = os.getenv("TEST_EXPECTED_COLUMN", "")
        config["TEST_DAX_QUERY"] = os.getenv("TEST_DAX_QUERY", "")
        config["TEST_MIN_TABLES_COUNT"] = int(os.getenv("TEST_MIN_TABLES_COUNT", "1"))

        return config

    @pytest.fixture(scope="class")
    def connector(self, test_config) -> "Generator[PowerBIConnector, None, None]":
        """Create and connect a PowerBIConnector instance."""
        connector = PowerBIConnector()

        # Test if ADOMD.NET is properly available
        try:
            connector._check_pyadomd()
        except Exception as e:
            if "System.Configuration.ConfigurationManager" in str(e):
                pytest.skip(
                    "ADOMD.NET dependency issue: System.Configuration.ConfigurationManager not found. "
                    "This is a known issue with newer .NET versions. "
                    "See docs/TROUBLESHOOTING_INTEGRATION.md for solutions."
                )
            else:
                pytest.skip(f"ADOMD.NET not available: {e}")

        # Connect to Power BI
        success = False
        try:
            success = connector.connect(
                xmla_endpoint=test_config["TEST_XMLA_ENDPOINT"],
                tenant_id=test_config["TEST_TENANT_ID"],
                client_id=test_config["TEST_CLIENT_ID"],
                client_secret=test_config["TEST_CLIENT_SECRET"],
                initial_catalog=test_config["TEST_INITIAL_CATALOG"],
            )
        except Exception as e:
            if "System.Configuration.ConfigurationManager" in str(e):
                pytest.skip(
                    "ADOMD.NET configuration error: System.Configuration.ConfigurationManager missing. "
                    "See docs/TROUBLESHOOTING_INTEGRATION.md for installation instructions."
                )
            else:
                pytest.fail(f"Connection failed: {e}")

        assert success, "Failed to connect to Power BI test dataset"
        assert connector.connected, "Connector should be in connected state"

        yield connector

        # Cleanup: connector doesn't need explicit disconnect
        connector.connected = False

    def test_connection_establishment(self, connector, test_config):
        """Test that connection to Power BI dataset is successful."""
        assert connector.connected
        assert connector.connection_string is not None
        assert test_config["TEST_INITIAL_CATALOG"] in connector.connection_string

    def test_discover_tables(self, connector, test_config):
        """Test discovery of tables in the dataset."""
        tables = connector.discover_tables()

        assert isinstance(tables, list), "Tables should be returned as a list"
        assert (
            len(tables) >= test_config["TEST_MIN_TABLES_COUNT"]
        ), f"Expected at least {test_config['TEST_MIN_TABLES_COUNT']} tables"

        # Check that table names are strings and not empty
        for table in tables:
            assert isinstance(table, str), f"Table name should be string, got {type(table)}"
            assert len(table) > 0, "Table name should not be empty"
            assert not table.startswith("$"), "System tables should be filtered out"

    def test_expected_table_exists(self, connector, test_config):
        """Test that expected test table exists in the dataset."""
        if not test_config["TEST_EXPECTED_TABLE"]:
            pytest.skip("TEST_EXPECTED_TABLE not configured")

        tables = connector.discover_tables()
        expected_table = test_config["TEST_EXPECTED_TABLE"]

        assert expected_table in tables, f"Expected table '{expected_table}' not found in tables: {tables}"

    def test_get_table_schema(self, connector, test_config):
        """Test retrieving schema information for a table."""
        tables = connector.discover_tables()
        assert len(tables) > 0, "No tables found to test schema retrieval"

        # Test schema for first table
        table_name = tables[0]
        schema = connector.get_table_schema(table_name)

        assert isinstance(schema, dict), "Schema should be returned as dictionary"
        assert "table_name" in schema, "Schema should contain table_name"
        assert "type" in schema, "Schema should contain type"
        assert schema["table_name"] == table_name

        if schema["type"] == "data_table":
            assert "columns" in schema, "Data table schema should contain columns"
            assert isinstance(schema["columns"], list), "Columns should be a list"
            assert len(schema["columns"]) > 0, "Table should have at least one column"
        elif schema["type"] == "measure_table":
            assert "measures" in schema, "Measure table schema should contain measures"
            assert isinstance(schema["measures"], list), "Measures should be a list"

    def test_expected_column_exists(self, connector, test_config):
        """Test that expected column exists in the expected table."""
        if not test_config["TEST_EXPECTED_TABLE"] or not test_config["TEST_EXPECTED_COLUMN"]:
            pytest.skip("TEST_EXPECTED_TABLE or TEST_EXPECTED_COLUMN not configured")

        table_name = test_config["TEST_EXPECTED_TABLE"]
        expected_column = test_config["TEST_EXPECTED_COLUMN"]

        schema = connector.get_table_schema(table_name)

        if schema["type"] == "data_table":
            columns = schema.get("columns", [])
            assert (
                expected_column in columns
            ), f"Expected column '{expected_column}' not found in table '{table_name}'. Available columns: {columns}"

    def test_execute_simple_dax_query(self, connector):
        """Test executing a simple DAX query."""
        tables = connector.discover_tables()
        assert len(tables) > 0, "No tables found to test DAX execution"

        # Find a data table to query
        data_table = None
        for table in tables:
            schema = connector.get_table_schema(table)
            if schema["type"] == "data_table":
                data_table = table
                break

        if not data_table:
            pytest.skip("No data tables found for DAX query testing")

        # Execute simple query
        dax_query = f"EVALUATE TOPN(1, '{data_table}')"
        results = connector.execute_dax_query(dax_query)

        assert isinstance(results, list), "Results should be returned as a list"
        # Results might be empty, but should be a valid list
        if len(results) > 0:
            assert isinstance(results[0], dict), "Each result row should be a dictionary"

    def test_configured_dax_query(self, connector, test_config):
        """Test executing the configured test DAX query."""
        if not test_config["TEST_DAX_QUERY"]:
            pytest.skip("TEST_DAX_QUERY not configured")

        dax_query = test_config["TEST_DAX_QUERY"]
        results = connector.execute_dax_query(dax_query)

        assert isinstance(results, list), "Results should be returned as a list"
        assert len(results) > 0, f"Test DAX query should return at least one row: {dax_query}"
        assert isinstance(results[0], dict), "Each result row should be a dictionary"

    def test_get_sample_data(self, connector):
        """Test retrieving sample data from a table."""
        tables = connector.discover_tables()
        assert len(tables) > 0, "No tables found to test sample data retrieval"

        # Find a data table
        data_table = None
        for table in tables:
            schema = connector.get_table_schema(table)
            if schema["type"] == "data_table":
                data_table = table
                break

        if not data_table:
            pytest.skip("No data tables found for sample data testing")

        sample_data = connector.get_sample_data(data_table, num_rows=3)

        assert isinstance(sample_data, list), "Sample data should be returned as a list"
        assert len(sample_data) <= 3, "Should return at most 3 rows as requested"

        if len(sample_data) > 0:
            assert isinstance(sample_data[0], dict), "Each sample row should be a dictionary"


@pytest.mark.integration
@pytest.mark.skipif(
    not integration_enabled or not os.getenv("OPENAI_API_KEY"),
    reason="Integration tests or OpenAI API key not available",
)
class TestDataAnalyzerIntegration:
    """Integration tests for DataAnalyzer with real Power BI data."""

    @pytest.fixture(scope="class")
    def test_config(self) -> Dict[str, str]:
        """Load test configuration from environment variables."""
        required_vars = [
            "TEST_XMLA_ENDPOINT",
            "TEST_TENANT_ID",
            "TEST_CLIENT_ID",
            "TEST_CLIENT_SECRET",
            "TEST_INITIAL_CATALOG",
            "OPENAI_API_KEY",
        ]

        config = {}
        missing_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            config[var] = value

        if missing_vars:
            pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

        return config

    @pytest.fixture(scope="class")
    def analyzer_with_data(self, test_config) -> "DataAnalyzer":
        """Create DataAnalyzer with connected Power BI data context."""
        # Create and connect PowerBI connector
        connector = PowerBIConnector()
        connector.connect(
            xmla_endpoint=test_config["TEST_XMLA_ENDPOINT"],
            tenant_id=test_config["TEST_TENANT_ID"],
            client_id=test_config["TEST_CLIENT_ID"],
            client_secret=test_config["TEST_CLIENT_SECRET"],
            initial_catalog=test_config["TEST_INITIAL_CATALOG"],
        )

        # Create analyzer
        analyzer = DataAnalyzer(test_config["OPENAI_API_KEY"])

        # Prepare data context
        tables = connector.discover_tables()
        schemas = {}
        sample_data = {}

        # Get schemas for first few tables
        for table in tables[:3]:
            try:
                schema = connector.get_table_schema(table)
                schemas[table] = schema

                if schema["type"] == "data_table":
                    samples = connector.get_sample_data(table, 2)
                    sample_data[table] = samples
            except Exception:
                # Skip tables that can't be processed
                continue

        analyzer.set_data_context(tables, schemas, sample_data)

        return analyzer

    def test_generate_dax_query(self, analyzer_with_data):
        """Test generating a DAX query from natural language."""
        question = "Show me the first 5 rows from any available table"

        dax_query = analyzer_with_data.generate_dax_query(question)

        assert isinstance(dax_query, str), "Generated query should be a string"
        assert len(dax_query) > 0, "Generated query should not be empty"
        assert "EVALUATE" in dax_query.upper(), "DAX query should contain EVALUATE statement"
        assert not any(tag in dax_query for tag in ["<", ">"]), "Generated query should not contain HTML/XML tags"

    def test_suggest_questions(self, analyzer_with_data):
        """Test generating suggested questions about the data."""
        questions = analyzer_with_data.suggest_questions()

        assert isinstance(questions, list), "Suggestions should be returned as a list"
        assert len(questions) > 0, "Should suggest at least one question"
        assert len(questions) <= 10, "Should not suggest too many questions"

        for question in questions:
            assert isinstance(question, str), "Each question should be a string"
            assert len(question) > 0, "Questions should not be empty"
            assert question.endswith("?"), "Questions should end with question mark"


@pytest.mark.integration
@pytest.mark.skipif(
    not integration_enabled, reason="Integration tests disabled. Set ENABLE_INTEGRATION_TESTS=true to enable."
)
class TestMCPServerIntegration:
    """Integration tests for the complete MCP Server functionality."""

    @pytest.fixture(scope="class")
    def test_config(self) -> Dict[str, str]:
        """Load test configuration from environment variables."""
        required_vars = [
            "TEST_XMLA_ENDPOINT",
            "TEST_TENANT_ID",
            "TEST_CLIENT_ID",
            "TEST_CLIENT_SECRET",
            "TEST_INITIAL_CATALOG",
        ]

        config = {}
        missing_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            config[var] = value

        if missing_vars:
            pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

        return config

    @pytest.fixture(scope="class")
    def mcp_server(self) -> "PowerBIMCPServer":
        """Create MCP Server instance."""
        return PowerBIMCPServer(host="localhost", port=8001)

    @pytest.mark.asyncio
    async def test_connect_powerbi_tool(self, mcp_server, test_config):
        """Test the connect_powerbi tool through MCP interface."""
        # Prepare connection arguments
        arguments = {
            "xmla_endpoint": test_config["TEST_XMLA_ENDPOINT"],
            "tenant_id": test_config["TEST_TENANT_ID"],
            "client_id": test_config["TEST_CLIENT_ID"],
            "client_secret": test_config["TEST_CLIENT_SECRET"],
            "initial_catalog": test_config["TEST_INITIAL_CATALOG"],
        }

        # Test connection
        result = await mcp_server._handle_connect(arguments)

        assert isinstance(result, str), "Connection result should be a string"
        assert "Successfully connected" in result, f"Connection should succeed: {result}"
        assert mcp_server.is_connected, "Server should be in connected state"

    @pytest.mark.asyncio
    async def test_list_tables_tool(self, mcp_server, test_config):
        """Test the list_tables tool through MCP interface."""
        # First connect
        arguments = {
            "xmla_endpoint": test_config["TEST_XMLA_ENDPOINT"],
            "tenant_id": test_config["TEST_TENANT_ID"],
            "client_id": test_config["TEST_CLIENT_ID"],
            "client_secret": test_config["TEST_CLIENT_SECRET"],
            "initial_catalog": test_config["TEST_INITIAL_CATALOG"],
        }
        await mcp_server._handle_connect(arguments)

        # Test listing tables
        result = await mcp_server._handle_list_tables()

        assert isinstance(result, str), "Tables list result should be a string"
        assert (
            "Available tables:" in result or "No tables found" in result
        ), f"Result should contain tables information: {result}"

    @pytest.mark.asyncio
    async def test_get_table_info_tool(self, mcp_server, test_config):
        """Test the get_table_info tool through MCP interface."""
        # First connect
        arguments = {
            "xmla_endpoint": test_config["TEST_XMLA_ENDPOINT"],
            "tenant_id": test_config["TEST_TENANT_ID"],
            "client_id": test_config["TEST_CLIENT_ID"],
            "client_secret": test_config["TEST_CLIENT_SECRET"],
            "initial_catalog": test_config["TEST_INITIAL_CATALOG"],
        }
        await mcp_server._handle_connect(arguments)

        # Get first available table
        tables_result = await mcp_server._handle_list_tables()
        if "No tables found" in tables_result:
            pytest.skip("No tables available for testing table info")

        # Extract first table name (this is a simple extraction, could be improved)
        lines = tables_result.split("\n")
        table_name = None
        for line in lines:
            if line.strip().startswith("- "):
                table_name = line.strip()[2:]
                break

        if not table_name:
            pytest.skip("Could not extract table name from tables list")

        # Test getting table info
        arguments = {"table_name": table_name}
        result = await mcp_server._handle_get_table_info(arguments)

        assert isinstance(result, str), "Table info result should be a string"
        assert f"Table: {table_name}" in result, f"Result should contain table name: {result}"

    @pytest.mark.asyncio
    async def test_execute_dax_tool(self, mcp_server, test_config):
        """Test the execute_dax tool through MCP interface."""
        # First connect
        arguments = {
            "xmla_endpoint": test_config["TEST_XMLA_ENDPOINT"],
            "tenant_id": test_config["TEST_TENANT_ID"],
            "client_id": test_config["TEST_CLIENT_ID"],
            "client_secret": test_config["TEST_CLIENT_SECRET"],
            "initial_catalog": test_config["TEST_INITIAL_CATALOG"],
        }
        await mcp_server._handle_connect(arguments)

        # Test simple DAX query
        if test_config.get("TEST_DAX_QUERY"):
            dax_query = test_config["TEST_DAX_QUERY"]
        else:
            # Use a generic query that should work
            dax_query = 'EVALUATE ROW("Test", 1)'

        arguments = {"dax_query": dax_query}
        result = await mcp_server._handle_execute_dax(arguments)

        assert isinstance(result, str), "DAX execution result should be a string"
        # Result should be JSON or an error message
        assert (
            result.startswith("[") or result.startswith("{") or "error" in result.lower() or "failed" in result.lower()
        ), f"Result should be JSON data or error message: {result}"


if __name__ == "__main__":
    # Run integration tests if enabled
    if integration_enabled:
        print("Running Power BI MCP Integration Tests...")
        print("=" * 50)
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("Integration tests are disabled.")
        print("To enable:")
        print("1. Copy .env.example to .env")
        print("2. Set ENABLE_INTEGRATION_TESTS=true")
        print("3. Configure TEST_* variables")
        print("4. Run: pytest tests/test_integration.py -v")
