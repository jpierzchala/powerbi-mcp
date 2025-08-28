"""PowerBI Connector - Main interface for PowerBI operations."""

import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

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

        # Identity and caching
        self._connection_identity: Dict[str, Optional[str]] = {
            "xmla_endpoint": None,
            "initial_catalog": None,
        }
        self.model_key: Optional[str] = None
        self._cache_lock = threading.Lock()
        # Cache structure per model_key
        # {
        #   model_key: {
        #       "version": datetime | None,  # Last known model update marker used for cache entries
        #       "tables": List[Dict[str, Any]] | None,
        #       "table_schemas": { table_name: {"data": Dict[str, Any], "version": datetime | None} }
        #   }
        # }
        self._model_cache: Dict[str, Dict[str, Any]] = {}

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

        # Store identity for cache keying without secrets
        self._connection_identity = {
            "xmla_endpoint": xmla_endpoint,
            "initial_catalog": initial_catalog,
        }
        self.model_key = f"{xmla_endpoint}|{initial_catalog}"

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

    # Delegate methods to services with per-model caching
    def discover_tables(self) -> List[Dict[str, Any]]:
        """Discover all tables in the Power BI data model (cached per model)."""
        if not self.connected:
            raise Exception("Not connected to Power BI")

        current_marker = self._get_model_last_update_marker()
        cache_key = self._get_effective_model_key()

        with self._cache_lock:
            model_entry = self._model_cache.get(cache_key)
            if model_entry:
                cached_tables = model_entry.get("tables")
                cached_version: Optional[datetime] = model_entry.get("version")
                if cached_tables is not None and self._is_cache_valid(cached_version, current_marker):
                    logger.info("Using cached tables for model %s", cache_key)
                    return cached_tables

        # Cache miss or invalid: fetch fresh
        tables = self.schema_service.discover_tables()

        with self._cache_lock:
            model_entry = self._model_cache.setdefault(cache_key, {"version": None, "tables": None, "table_schemas": {}})
            model_entry["tables"] = tables
            # Store the marker we observed now; if None, we keep None to allow future invalidations when marker becomes available
            model_entry["version"] = current_marker

        return tables

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a specific table (cached per model+table)."""
        if not self.connected:
            raise Exception("Not connected to Power BI")

        current_marker = self._get_model_last_update_marker()
        cache_key = self._get_effective_model_key()

        with self._cache_lock:
            model_entry = self._model_cache.get(cache_key)
            if model_entry:
                table_schemas: Dict[str, Any] = model_entry.get("table_schemas", {})
                table_entry = table_schemas.get(table_name)
                if table_entry:
                    cached_version: Optional[datetime] = table_entry.get("version")
                    if self._is_cache_valid(cached_version, current_marker):
                        logger.info("Using cached table schema for %s in model %s", table_name, cache_key)
                        return table_entry["data"]

        # Cache miss or invalid: fetch fresh
        schema = self.schema_service.get_table_schema(table_name)

        with self._cache_lock:
            model_entry = self._model_cache.setdefault(cache_key, {"version": None, "tables": None, "table_schemas": {}})
            table_schemas = model_entry.setdefault("table_schemas", {})
            table_schemas[table_name] = {"data": schema, "version": current_marker}
            # Also consider updating model-level version if it's currently None
            if model_entry.get("version") is None:
                model_entry["version"] = current_marker

        return schema

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

    # -------------------
    # Internal helpers
    # -------------------

    def _get_effective_model_key(self) -> str:
        """Return a stable model key for caching; fall back to connection_string if needed."""
        if self.model_key:
            return self.model_key
        # Fallback for tests that set connection_string directly
        return str(self.connection_string or "<unknown>")

    def _is_cache_valid(self, cached_marker: Optional[datetime], current_marker: Optional[datetime]) -> bool:
        """Determine if cache is valid based on last known and current model update markers."""
        if cached_marker is None:
            # If we never recorded a marker, be conservative and invalidate only when we have a newer marker present
            return current_marker is None
        if current_marker is None:
            # We cannot determine freshness; assume cached is valid
            return True
        # Valid if nothing changed since the cache was stored
        return cached_marker >= current_marker

    def _get_model_last_update_marker(self) -> Optional[datetime]:
        """Fetch the latest model update timestamp (max of schema/data updates) from DMV.

        Returns None if it cannot be determined (e.g., lack of permissions or DMV unavailable).
        """
        try:
            self._check_pyadomd()
            Pyadomd = None
            try:
                import server  # type: ignore

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            if Pyadomd is None:
                # Fallback: import via initializer
                from config.adomd_setup import initialize_adomd

                _, pyadomd, _, _ = initialize_adomd()
                Pyadomd = pyadomd

            if Pyadomd is None or not self.connection_string:
                return None

            with Pyadomd(self.connection_string) as conn:
                cursor = None
                try:
                    cursor = conn.cursor()
                    # Query DMV for last updates; Power BI model name is always 'Model'
                    dmv_query = (
                        "SELECT [LAST_SCHEMA_UPDATE], [LAST_DATA_UPDATE] "
                        "FROM $SYSTEM.MDSCHEMA_CUBES WHERE [CUBE_NAME] = 'Model'"
                    )
                    cursor.execute(dmv_query)
                    rows = cursor.fetchall() or []
                    if not rows:
                        return None
                    last_seen: Optional[datetime] = None
                    for row in rows:
                        # Row may be a tuple-like with datetime objects
                        last_schema = row[0] if len(row) > 0 else None
                        last_data = row[1] if len(row) > 1 else None
                        # Determine max for this row
                        for d in (last_schema, last_data):
                            if isinstance(d, datetime):
                                if last_seen is None or d > last_seen:
                                    last_seen = d
                    return last_seen
                finally:
                    if cursor is not None:
                        try:
                            cursor.close()
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"Could not retrieve model update marker: {e}")
            return None
