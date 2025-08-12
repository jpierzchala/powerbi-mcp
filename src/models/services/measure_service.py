"""Measure operations for PowerBI data models."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# Always get variables from server module for test compatibility
def _get_adomd_objects():
    """Get ADOMD objects from server module for test compatibility."""
    try:
        import server

        return server.Pyadomd
    except ImportError:
        # Fallback to direct import if server module not available
        from config.adomd_setup import initialize_adomd

        _, pyadomd, _, _ = initialize_adomd()
        return pyadomd


class MeasureService:
    """Handles measure operations for PowerBI data models."""

    def __init__(self, connector):
        """Initialize with a PowerBI connector."""
        self.connector = connector

    def get_measures_for_table(self, table_name: str) -> Dict[str, Any]:
        """Get measures for a measure table"""
        if not self.connector.connected:
            raise Exception("Not connected to Power BI")

        self.connector._check_pyadomd()
        try:
            Pyadomd = _get_adomd_objects()

            with Pyadomd(self.connector.connection_string) as conn:
                # Get table ID
                id_cursor = conn.cursor()
                id_query = f"SELECT [ID] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = '{table_name}'"
                id_cursor.execute(id_query)
                table_id_result = id_cursor.fetchone()
                id_cursor.close()

                if not table_id_result:
                    return {"table_name": table_name, "type": "unknown", "measures": []}

                table_id = list(table_id_result)[0]

                # Get measures
                measure_cursor = conn.cursor()
                measure_query = f"SELECT [Name], [Expression] FROM $SYSTEM.TMSCHEMA_MEASURES WHERE [TableID] = {table_id} ORDER BY [Name]"
                measure_cursor.execute(measure_query)
                measures = measure_cursor.fetchall()
                measure_cursor.close()

                return {
                    "table_name": table_name,
                    "type": "measure_table",
                    "measures": [{"name": m[0], "dax": m[1]} for m in measures],
                }

        except Exception as e:
            logger.error(f"Failed to get measures for table '{table_name}': {str(e)}")
            return {"table_name": table_name, "type": "error", "error": str(e)}
