"""
Tests for PowerBIConnector class
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import PowerBIConnector, clean_dax_query


@pytest.mark.unit
class TestPowerBIConnector:
    """Test cases for PowerBIConnector"""

    @pytest.fixture
    def connector(self):
        """Create a PowerBIConnector instance"""
        return PowerBIConnector()

    @pytest.fixture
    def mock_pyadomd(self):
        """Mock pyadomd for testing"""
        with patch("server.Pyadomd") as mock:
            yield mock

    def test_initialization(self, connector):
        """Test connector initializes with correct defaults"""
        assert connector.connection_string is None
        assert connector.connected is False
        assert connector.tables == []
        assert connector.metadata == {}

    def test_successful_connection(self, connector, mock_pyadomd):
        """Test successful connection to Power BI"""
        # Arrange
        mock_conn = MagicMock()
        mock_pyadomd.return_value.__enter__.return_value = mock_conn

        # Act
        result = connector.connect(
            xmla_endpoint="powerbi://test",
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            initial_catalog="test-dataset",
        )

        # Assert
        assert result is True
        assert connector.connected is True
        assert "Provider=MSOLAP" in connector.connection_string
        assert "test-dataset" in connector.connection_string

    def test_connection_failure(self, connector, mock_pyadomd):
        """Test handling of connection failure"""
        # Arrange
        mock_pyadomd.side_effect = Exception("Connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            connector.connect(
                xmla_endpoint="invalid",
                tenant_id="test",
                client_id="test",
                client_secret="test",
                initial_catalog="test",
            )

        assert "Connection failed" in str(exc_info.value)
        assert connector.connected is False

    def test_discover_tables(self, connector, mock_pyadomd):
        """Test table discovery"""
        # Arrange
        connector.connected = True
        connector.connection_string = "test"

        # Mock schema dataset
        mock_table = Mock()
        mock_table.Rows = [
            {"TABLE_NAME": "Sales", "TABLE_SCHEMA": "Model"},
            {"TABLE_NAME": "Product", "TABLE_SCHEMA": "Model"},
            {"TABLE_NAME": "$SYSTEM_TABLE", "TABLE_SCHEMA": "$SYSTEM"},  # Should be filtered
            {"TABLE_NAME": "DateTableTemplate_123", "TABLE_SCHEMA": "Model"},  # Should be filtered
        ]

        mock_dataset = Mock()
        mock_dataset.Tables.Count = 1
        mock_dataset.Tables = [mock_table]

        mock_conn = Mock()
        mock_conn.conn.GetSchemaDataSet.return_value = mock_dataset
        mock_pyadomd.return_value.__enter__.return_value = mock_conn

        # Act
        tables = connector.discover_tables()

        # Assert
        assert len(tables) == 2
        assert "Sales" in tables
        assert "Product" in tables
        assert "$SYSTEM_TABLE" not in tables
        assert "DateTableTemplate_123" not in tables

    def test_execute_dax_query(self, connector, mock_pyadomd):
        """Test DAX query execution"""
        # Arrange
        connector.connected = True
        connector.connection_string = "test"

        mock_cursor = Mock()
        mock_cursor.description = [("Column1",), ("Column2",)]
        mock_cursor.fetchall.return_value = [("Value1", "Value2"), ("Value3", "Value4")]

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pyadomd.return_value.__enter__.return_value = mock_conn

        # Act
        results = connector.execute_dax_query("EVALUATE Sales")

        # Assert
        assert len(results) == 2
        assert results[0]["Column1"] == "Value1"
        assert results[0]["Column2"] == "Value2"
        assert results[1]["Column1"] == "Value3"
        assert results[1]["Column2"] == "Value4"
        mock_cursor.execute.assert_called_once_with("EVALUATE Sales")


@pytest.mark.unit
class TestDAXCleaning:
    """Test cases for DAX query cleaning"""

    def test_clean_html_tags(self):
        """Test removal of HTML tags"""
        dirty_query = "EVALUATE FILTER(Sales, Sales[<oii>Rank</oii>] > 5)"
        clean_query = clean_dax_query(dirty_query)
        assert clean_query == "EVALUATE FILTER(Sales, Sales[Rank] > 5)"

    def test_clean_xml_tags(self):
        """Test removal of XML tags"""
        dirty_query = "EVALUATE <tag>SUMMARIZE</tag>(Product, Product[Category])"
        clean_query = clean_dax_query(dirty_query)
        assert clean_query == "EVALUATE SUMMARIZE(Product, Product[Category])"

    def test_clean_multiple_tags(self):
        """Test removal of multiple tags"""
        dirty_query = "EVALUATE <a>TOPN</a>(10, Sales, Sales[Amount], <desc>DESC</desc>)"
        clean_query = clean_dax_query(dirty_query)
        assert clean_query == "EVALUATE TOPN(10, Sales, Sales[Amount], DESC)"

    def test_no_tags_unchanged(self):
        """Test that queries without tags are unchanged"""
        clean_query_input = "EVALUATE SUMMARIZE(Sales, Product[Category])"
        clean_query = clean_dax_query(clean_query_input)
        assert clean_query == clean_query_input

    def test_preserve_dax_operators(self):
        """Test that DAX operators < and > are preserved"""
        query = "EVALUATE FILTER(Sales, Sales[Amount] > 100 && Sales[Quantity] < 50)"
        clean_query = clean_dax_query(query)
        # Should only remove tags, not comparison operators
        assert ">" in clean_query
        assert "<" in clean_query


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling scenarios"""

    def test_not_connected_error(self):
        """Test operations fail when not connected"""
        connector = PowerBIConnector()

        with pytest.raises(Exception) as exc_info:
            connector.execute_dax_query("EVALUATE Sales")

        assert "Not connected to Power BI" in str(exc_info.value)

    @patch("server.Pyadomd")
    def test_dax_execution_error(self, mock_pyadomd):
        """Test handling of DAX execution errors"""
        # Arrange
        connector = PowerBIConnector()
        connector.connected = True
        connector.connection_string = "test"

        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Invalid DAX syntax")

        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pyadomd.return_value.__enter__.return_value = mock_conn

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            connector.execute_dax_query("INVALID DAX")

        assert "DAX query failed" in str(exc_info.value)


@pytest.mark.unit
class TestPyadomdUnavailable:
    """Test behavior when pyadomd is not available"""

    @patch("server.Pyadomd", None)
    def test_pyadomd_unavailable_error(self):
        """Test that proper error is raised when pyadomd is not available"""
        connector = PowerBIConnector()

        with pytest.raises(Exception) as exc_info:
            connector.connect("test_endpoint", "test_tenant", "test_client", "test_secret", "test_catalog")

        assert "Pyadomd library not available" in str(exc_info.value)

    @patch("server.Pyadomd", None)
    def test_operations_fail_without_pyadomd(self):
        """Test that operations fail gracefully without pyadomd"""
        connector = PowerBIConnector()

        # Test connect
        with pytest.raises(Exception) as exc_info:
            connector.connect("test", "tenant", "client", "secret", "catalog")
        assert "Pyadomd library not available" in str(exc_info.value)

        # Test discover_tables - should fail with connection error first
        with pytest.raises(Exception) as exc_info:
            connector.discover_tables()
        assert "Not connected to Power BI" in str(exc_info.value)

        # Test execute_dax_query - should fail with connection error first
        with pytest.raises(Exception) as exc_info:
            connector.execute_dax_query("EVALUATE Sales")
        assert "Not connected to Power BI" in str(exc_info.value)

        # Test with mocked connection to check pyadomd error
        connector.connected = True
        connector.connection_string = "mocked"

        with pytest.raises(Exception) as exc_info:
            connector.discover_tables()
        assert "Pyadomd library not available" in str(exc_info.value)

        with pytest.raises(Exception) as exc_info:
            connector.execute_dax_query("EVALUATE Sales")
        assert "Pyadomd library not available" in str(exc_info.value)


@pytest.mark.unit
class TestPowerBIConnectorMetadata:
    """Test cases for enhanced metadata functionality"""

    @pytest.fixture
    def connector(self):
        """Create a connected PowerBIConnector instance"""
        connector = PowerBIConnector()
        connector.connected = True
        connector.connection_string = "mocked_connection"
        return connector

    @pytest.fixture
    def mock_pyadomd(self):
        """Mock pyadomd for testing"""
        with patch("server.Pyadomd") as mock:
            yield mock

    def test_discover_tables_with_metadata(self, connector, mock_pyadomd):
        """Test discovering tables with metadata"""
        # Arrange
        mock_adomd_conn = MagicMock()
        mock_pyadomd_conn = MagicMock()
        mock_pyadomd_conn.conn = mock_adomd_conn
        mock_pyadomd.return_value.__enter__.return_value = mock_pyadomd_conn

        # Mock schema dataset
        mock_dataset = MagicMock()
        mock_table = MagicMock()
        mock_dataset.Tables = [mock_table]
        mock_adomd_conn.GetSchemaDataSet.return_value = mock_dataset

        # Mock table rows with proper mocking
        mock_row1 = MagicMock()
        mock_row1.__getitem__.return_value = "Sales"
        mock_row1.get.return_value = "Sales transactions table"

        mock_row2 = MagicMock()
        mock_row2.__getitem__.return_value = "Products"
        mock_row2.get.return_value = "Product information"

        mock_row3 = MagicMock()
        mock_row3.__getitem__.return_value = "Customers"
        mock_row3.get.return_value = ""  # None description converted to empty string

        mock_table.Rows = [mock_row1, mock_row2, mock_row3]

        # Act
        result = connector.discover_tables_with_metadata()

        # Assert
        assert len(result) == 3
        assert result[0]["name"] == "Sales"
        assert result[0]["description"] == "Sales transactions table"
        assert result[1]["name"] == "Products"
        assert result[1]["description"] == "Product information"
        assert result[2]["name"] == "Customers"
        assert result[2]["description"] == ""

    def test_get_relationships(self, connector, mock_pyadomd):
        """Test getting relationships between tables"""
        # Arrange
        mock_adomd_conn = MagicMock()
        mock_pyadomd_conn = MagicMock()
        mock_pyadomd_conn.conn = mock_adomd_conn
        mock_pyadomd.return_value.__enter__.return_value = mock_pyadomd_conn

        # Mock schema dataset for relationships
        mock_dataset = MagicMock()
        mock_table = MagicMock()
        mock_dataset.Tables = [mock_table]
        mock_adomd_conn.GetSchemaDataSet.return_value = mock_dataset

        # Mock relationship rows with simple approach
        mock_row1 = MagicMock()
        mock_row1.get.side_effect = lambda key, default="": {
            "Name": "Rel1",
            "FromTable": "Sales",
            "FromColumn": "ProductID",
            "ToTable": "Products",
            "ToColumn": "ID",
        }.get(key, default)

        mock_row2 = MagicMock()
        mock_row2.get.side_effect = lambda key, default="": {
            "Name": "Rel2",
            "FromTable": "Sales",
            "FromColumn": "CustomerID",
            "ToTable": "Customers",
            "ToColumn": "ID",
        }.get(key, default)

        mock_table.Rows = [mock_row1, mock_row2]

        # Act
        result = connector.get_relationships()

        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "Rel1"
        assert result[0]["from_table"] == "Sales"
        assert result[0]["from_column"] == "ProductID"
        assert result[0]["to_table"] == "Products"
        assert result[0]["to_column"] == "ID"

    def test_get_table_schema_with_metadata(self, connector, mock_pyadomd):
        """Test getting table schema with enhanced metadata"""
        # This test now uses the working get_table_schema method + metadata enhancements
        # We need to mock the basic get_table_schema method
        with patch.object(connector, "get_table_schema") as mock_get_schema:
            mock_get_schema.return_value = {
                "table_name": "Sales",
                "type": "data_table",
                "columns": ["ProductID", "Amount", "Date"],
            }

            # Mock get_table_relationships to return empty
            with patch.object(connector, "get_table_relationships") as mock_get_rels:
                mock_get_rels.return_value = []

                # Act
                result = connector.get_table_schema_with_metadata("Sales")

                # Assert
                assert result["table_name"] == "Sales"
                assert result["type"] == "data_table"
                assert result["description"] == ""  # No description available in basic approach
                assert len(result["columns"]) == 3
                assert result["columns"][0]["name"] == "ProductID"
                assert result["columns"][0]["description"] == ""  # No column descriptions available
                assert "relationships" in result

    def test_get_table_relationships(self, connector, mock_pyadomd):
        """Test getting relationships for a specific table"""
        # This now filters all relationships for a specific table
        with patch.object(connector, "get_relationships") as mock_get_all_rels:
            mock_get_all_rels.return_value = [
                {
                    "name": "Rel1",
                    "from_table": "Sales",
                    "from_column": "ProductID",
                    "to_table": "Products",
                    "to_column": "ID",
                },
                {
                    "name": "Rel2",
                    "from_table": "Customers",
                    "from_column": "ID",
                    "to_table": "Orders",
                    "to_column": "CustomerID",
                },
                {
                    "name": "Rel3",
                    "from_table": "Sales",
                    "from_column": "CustomerID",
                    "to_table": "Customers",
                    "to_column": "ID",
                },
            ]

            # Act
            result = connector.get_table_relationships("Sales")

            # Assert - should return only relationships involving "Sales" table
            assert len(result) == 2  # Rel1 and Rel3
            assert result[0]["name"] == "Rel1"
            assert result[1]["name"] == "Rel3"

    def test_error_handling_metadata_methods(self, connector, mock_pyadomd):
        """Test error handling in metadata methods"""
        # Arrange - simulate database error
        mock_pyadomd.return_value.__enter__.side_effect = Exception("Database error")

        # Test discover_tables_with_metadata error handling
        with pytest.raises(Exception) as exc_info:
            connector.discover_tables_with_metadata()
        assert "Failed to discover tables with metadata" in str(exc_info.value)

        # Test get_relationships error handling
        with pytest.raises(Exception) as exc_info:
            connector.get_relationships()
        assert "Failed to get relationships" in str(exc_info.value)

        # Test get_table_schema_with_metadata error handling
        with pytest.raises(Exception) as exc_info:
            connector.get_table_schema_with_metadata("Sales")
        assert "Failed to get enhanced schema for table 'Sales'" in str(exc_info.value)

    def test_not_connected_error_metadata_methods(self, mock_pyadomd):
        """Test that metadata methods fail when not connected"""
        # Arrange
        connector = PowerBIConnector()  # Not connected

        # Test all new methods fail when not connected
        with pytest.raises(Exception) as exc_info:
            connector.discover_tables_with_metadata()
        assert "Not connected to Power BI" in str(exc_info.value)

        with pytest.raises(Exception) as exc_info:
            connector.get_relationships()
        assert "Not connected to Power BI" in str(exc_info.value)

        with pytest.raises(Exception) as exc_info:
            connector.get_table_schema_with_metadata("Sales")
        assert "Not connected to Power BI" in str(exc_info.value)

        with pytest.raises(Exception) as exc_info:
            connector.get_table_relationships("Sales")
        assert "Not connected to Power BI" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
