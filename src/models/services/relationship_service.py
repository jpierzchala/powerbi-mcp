"""Relationship operations for PowerBI data models."""

import logging
from typing import Any, Dict, List

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


class RelationshipService:
    """Handles relationship operations for PowerBI data models."""

    def __init__(self, connector):
        """Initialize with a PowerBI connector."""
        self.connector = connector

    def get_table_relationships(self, table_name: str) -> List[Dict[str, Any]]:
        """Get relationships for a specific table"""
        if not self.connector.connected:
            raise Exception("Not connected to Power BI")

        self.connector._check_pyadomd()
        try:
            Pyadomd = _get_adomd_objects()

            with Pyadomd(self.connector.connection_string) as conn:
                cursor = conn.cursor()

                # Query to get relationships where this table is involved
                relationship_query = f"""
                SELECT
                    ft.[Name] as FromTable,
                    fc.[Name] as FromColumn,
                    tt.[Name] as ToTable,
                    tc.[Name] as ToColumn,
                    r.[FromCardinality],
                    r.[ToCardinality],
                    r.[CrossFilteringBehavior]
                FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS r
                JOIN $SYSTEM.TMSCHEMA_COLUMNS fc ON r.[FromColumnID] = fc.[ID]
                JOIN $SYSTEM.TMSCHEMA_TABLES ft ON fc.[TableID] = ft.[ID]
                JOIN $SYSTEM.TMSCHEMA_COLUMNS tc ON r.[ToColumnID] = tc.[ID]
                JOIN $SYSTEM.TMSCHEMA_TABLES tt ON tc.[TableID] = tt.[ID]
                WHERE ft.[Name] = '{table_name}' OR tt.[Name] = '{table_name}'
                """

                cursor.execute(relationship_query)
                results = cursor.fetchall()
                cursor.close()

                relationships = []
                for result in results:
                    from_table = result[0]
                    from_column = result[1]
                    to_table = result[2]
                    to_column = result[3]
                    from_cardinality = result[4]
                    to_cardinality = result[5]
                    cross_filter = result[6]

                    # Determine direction from perspective of current table
                    if from_table == table_name:
                        direction = "outgoing"
                        related_table = to_table
                        local_column = from_column
                        related_column = to_column
                    else:
                        direction = "incoming"
                        related_table = from_table
                        local_column = to_column
                        related_column = from_column

                    relationships.append(
                        {
                            "direction": direction,
                            "related_table": related_table,
                            "local_column": local_column,
                            "related_column": related_column,
                            "cardinality": self._format_cardinality(from_cardinality, to_cardinality),
                            "cross_filter": self._format_cross_filter(cross_filter),
                        }
                    )

                return relationships

        except Exception as e:
            logger.error(f"Failed to get relationships for table '{table_name}': {str(e)}")
            return []

    def get_all_relationships(self, table_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get relationships for all tables in optimized batch queries"""
        try:
            Pyadomd = _get_adomd_objects()

            with Pyadomd(self.connector.connection_string) as conn:
                # First, get all table name-to-ID mappings
                cursor = conn.cursor()
                table_map_query = "SELECT [Name], [ID] FROM $SYSTEM.TMSCHEMA_TABLES"
                cursor.execute(table_map_query)
                table_map_results = cursor.fetchall()
                cursor.close()

                table_name_to_id = {}
                table_id_to_name = {}
                for result in table_map_results:
                    name, table_id = result[0], result[1]
                    if name:
                        table_name_to_id[name] = table_id
                        table_id_to_name[table_id] = name

                # Get all column name-to-ID mappings
                cursor = conn.cursor()
                column_map_query = "SELECT [ID], [ExplicitName], [TableID] FROM $SYSTEM.TMSCHEMA_COLUMNS"
                cursor.execute(column_map_query)
                column_map_results = cursor.fetchall()
                cursor.close()

                column_id_to_info = {}
                for result in column_map_results:
                    col_id, col_name, table_id = result[0], result[1], result[2]
                    if col_id and col_name:
                        column_id_to_info[col_id] = {"name": col_name, "table_id": table_id}

                # Get all relationships in one query
                cursor = conn.cursor()
                relationships_query = """
                SELECT
                    [FromTableID], [ToTableID], [FromColumnID], [ToColumnID],
                    [IsActive], [Type], [CrossFilteringBehavior],
                    [FromCardinality], [ToCardinality]
                FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS
                """
                cursor.execute(relationships_query)
                all_relationships = cursor.fetchall()
                cursor.close()

                # Build relationships mapping for requested tables
                table_relationships = {name: [] for name in table_names}

                for rel in all_relationships:
                    from_table_id, to_table_id = rel[0], rel[1]
                    from_col_id, to_col_id = rel[2], rel[3]
                    is_active, cross_filter = rel[4], rel[6]  # Skip rel[5] (Type) as it's not used
                    from_cardinality, to_cardinality = rel[7], rel[8]

                    from_table_name = table_id_to_name.get(from_table_id)
                    to_table_name = table_id_to_name.get(to_table_id)

                    if not from_table_name or not to_table_name:
                        continue

                    from_col_info = column_id_to_info.get(from_col_id)
                    to_col_info = column_id_to_info.get(to_col_id)

                    if not from_col_info or not to_col_info:
                        continue

                    from_col_name = from_col_info["name"]
                    to_col_name = to_col_info["name"]

                    # Add relationship from the "Many" side (from_table)
                    if from_table_name in table_relationships:
                        table_relationships[from_table_name].append(
                            {
                                "relatedTable": to_table_name,
                                "fromColumn": from_col_name,
                                "toColumn": to_col_name,
                                "cardinality": self.connector._format_cardinality(from_cardinality, to_cardinality),
                                "isActive": bool(is_active),
                                "crossFilterDirection": self.connector._format_cross_filter(cross_filter),
                                "relationshipType": "Many-to-One",
                            }
                        )

                    # Add relationship from the "One" side (to_table)
                    if to_table_name in table_relationships:
                        table_relationships[to_table_name].append(
                            {
                                "relatedTable": from_table_name,
                                "fromColumn": to_col_name,  # Current table column
                                "toColumn": from_col_name,  # Related table column
                                "cardinality": self.connector._format_cardinality(to_cardinality, from_cardinality),
                                "isActive": bool(is_active),
                                "crossFilterDirection": self.connector._format_cross_filter(cross_filter),
                                "relationshipType": "One-to-Many",
                            }
                        )

                return table_relationships

        except Exception as e:
            logger.warning(f"Failed to get batch relationships: {str(e)}")
            # Fallback to individual queries if batch fails
            table_relationships = {name: [] for name in table_names}
            for table_name in table_names:
                try:
                    table_relationships[table_name] = self.get_table_relationships(table_name)
                except Exception:
                    table_relationships[table_name] = []
            return table_relationships

    def _format_cardinality(self, from_cardinality: int, to_cardinality: int) -> str:
        """Format cardinality for display"""
        cardinality_map = {1: "One", 2: "Many"}
        from_card = cardinality_map.get(from_cardinality, "Unknown")
        to_card = cardinality_map.get(to_cardinality, "Unknown")
        return f"{from_card}-to-{to_card}"

    def _format_cross_filter(self, cross_filter_behavior: int) -> str:
        """Format cross filter behavior for display"""
        filter_map = {1: "Single", 2: "Both", 3: "Automatic", 4: "None"}
        return filter_map.get(cross_filter_behavior, "Unknown")
