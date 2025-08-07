"""Relationship operations for PowerBI data models."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Import variables that will be set by server module
Pyadomd = None

try:
    import server
    if hasattr(server, "Pyadomd"):
        Pyadomd = server.Pyadomd
except ImportError:
    # server module not available yet (during initial import), use local variables
    pass


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
            global Pyadomd
            # Update from server module if available
            try:
                import server
                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

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
                    
                    relationships.append({
                        "direction": direction,
                        "related_table": related_table,
                        "local_column": local_column,
                        "related_column": related_column,
                        "cardinality": self._format_cardinality(from_cardinality, to_cardinality),
                        "cross_filter": self._format_cross_filter(cross_filter)
                    })
                
                return relationships
                
        except Exception as e:
            logger.error(f"Failed to get relationships for table '{table_name}': {str(e)}")
            return []

    def get_all_relationships(self, table_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get all relationships for multiple tables in batch for performance"""
        if not self.connector.connected:
            return {}

        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server
                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connector.connection_string) as conn:
                # Get all relationships in one query
                table_names_str = "', '".join(table_names)
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
                WHERE ft.[Name] IN ('{table_names_str}') OR tt.[Name] IN ('{table_names_str}')
                """
                
                cursor = conn.cursor()
                cursor.execute(relationship_query)
                results = cursor.fetchall()
                cursor.close()
                
                # Initialize relationships dict
                relationships = {}
                for table_name in table_names:
                    relationships[table_name] = []
                
                # Process results
                for result in results:
                    from_table = result[0]
                    from_column = result[1]
                    to_table = result[2]
                    to_column = result[3]
                    from_cardinality = result[4]
                    to_cardinality = result[5]
                    cross_filter = result[6]
                    
                    # Add relationship to from_table (outgoing)
                    if from_table in relationships:
                        relationships[from_table].append({
                            "direction": "outgoing",
                            "related_table": to_table,
                            "local_column": from_column,
                            "related_column": to_column,
                            "cardinality": self._format_cardinality(from_cardinality, to_cardinality),
                            "cross_filter": self._format_cross_filter(cross_filter)
                        })
                    
                    # Add relationship to to_table (incoming)
                    if to_table in relationships:
                        relationships[to_table].append({
                            "direction": "incoming",
                            "related_table": from_table,
                            "local_column": to_column,
                            "related_column": from_column,
                            "cardinality": self._format_cardinality(from_cardinality, to_cardinality),
                            "cross_filter": self._format_cross_filter(cross_filter)
                        })
                
                return relationships

        except Exception as e:
            logger.warning(f"Failed to get relationships in batch: {str(e)}")
            return {}

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