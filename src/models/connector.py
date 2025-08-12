"""PowerBI Connector - Main interface for PowerBI operations."""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from .services.measure_service import MeasureService
from .services.query_service import QueryService
from .services.relationship_service import RelationshipService
from .services.schema_service import SchemaService

logger = logging.getLogger(__name__)

# Import variables that will be set by server module
Pyadomd = None
AdomdSchemaGuid = None

try:
    import server

    if hasattr(server, "Pyadomd"):
        Pyadomd = server.Pyadomd
    if hasattr(server, "AdomdSchemaGuid"):
        AdomdSchemaGuid = server.AdomdSchemaGuid
except ImportError:
    # server module not available yet (during initial import), use local variables
    pass


class PowerBIConnector:
    """Main PowerBI connector class that orchestrates operations through services."""

    def __init__(self):
        """Initialize the PowerBI connector"""
        self.connection_string = None
        self.connected = False
        self.tables = []
        self.metadata = {}
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Initialize services
        self.schema_service = SchemaService(self)
        self.relationship_service = RelationshipService(self)
        self.measure_service = MeasureService(self)
        self.query_service = QueryService(self)

    def _check_pyadomd(self):
        """Check if Pyadomd is available"""
        global Pyadomd
        # Update from server module if available
        try:
            import server

            if hasattr(server, "Pyadomd"):
                Pyadomd = server.Pyadomd
        except ImportError:
            pass

        if Pyadomd is None:
            raise Exception("Pyadomd library not available. Ensure .NET runtime and ADOMD.NET are installed")

    def connect(
        self, xmla_endpoint: str, tenant_id: str, client_id: str, client_secret: str, initial_catalog: str
    ) -> bool:
        """Establish connection to Power BI dataset"""
        self._check_pyadomd()
        self.connection_string = (
            f"Provider=MSOLAP;"
            f"Data Source={xmla_endpoint};"
            f"Initial Catalog={initial_catalog};"
            f"User ID=app:{client_id}@{tenant_id};"
            f"Password={client_secret};"
        )

        try:
            # Test connection
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string):
                self.connected = True
                logger.info(f"Connected to Power BI dataset: {initial_catalog}")
                # Don't discover tables during connection to speed up
                return True
        except Exception as e:
            self.connected = False
            logger.error(f"Connection failed: {str(e)}")
            raise Exception(f"Connection failed: {str(e)}")

    # Delegate methods to services
    def discover_tables(self) -> List[Dict[str, Any]]:
        """Discover all tables in the Power BI data model"""
        return self.schema_service.discover_tables()

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a specific table"""
        return self.schema_service.get_table_schema(table_name)

    def _get_table_relationships(self, table_name: str) -> List[Dict[str, Any]]:
        """Get relationships for a specific table"""
        return self.relationship_service.get_table_relationships(table_name)

    def _get_all_table_descriptions(self, table_names: List[str]) -> Dict[str, str]:
        """Get descriptions for multiple tables in a single query for performance"""
        return self.schema_service._get_all_table_descriptions(table_names)

    def _get_all_relationships(self, table_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get all relationships for multiple tables in batch for performance"""
        return self.relationship_service.get_all_relationships(table_names)

    def _get_column_descriptions(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column descriptions for a table"""
        return self.schema_service._get_column_descriptions(table_name)

    def _format_cardinality(self, from_cardinality: int, to_cardinality: int) -> str:
        """Format cardinality for display"""
        return self.relationship_service._format_cardinality(from_cardinality, to_cardinality)

    def _format_cross_filter(self, cross_filter_behavior: int) -> str:
        """Format cross filter behavior for display"""
        return self.relationship_service._format_cross_filter(cross_filter_behavior)

    def get_measures_for_table(self, table_name: str) -> Dict[str, Any]:
        """Get measures for a measure table"""
        return self.measure_service.get_measures_for_table(table_name)

    def execute_dax_query(self, dax_query: str) -> List[Dict[str, Any]]:
        """Execute a DAX query and return results"""
        return self.query_service.execute_dax_query(dax_query)

    def get_sample_data(self, table_name: str, num_rows: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        return self.query_service.get_sample_data(table_name, num_rows)
