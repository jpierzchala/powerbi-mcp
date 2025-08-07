"""Schema operations for PowerBI data models."""

import logging
from typing import Any, Dict, List, Optional

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


class SchemaService:
    """Handles schema-related operations for PowerBI data models."""
    
    def __init__(self, connector):
        """Initialize with a PowerBI connector."""
        self.connector = connector
        
    def discover_tables(self) -> List[Dict[str, Any]]:
        """Discover all tables in the Power BI data model"""
        if not self.connector.connected:
            raise Exception("Not connected to Power BI")

        self.connector._check_pyadomd()
        tables_list = []

        try:
            global Pyadomd, AdomdSchemaGuid
            # Update from server module if available
            try:
                import server
                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
                if hasattr(server, "AdomdSchemaGuid"):
                    AdomdSchemaGuid = server.AdomdSchemaGuid
            except ImportError:
                pass

            with Pyadomd(self.connector.connection_string) as pyadomd_conn:
                adomd_connection = pyadomd_conn.conn

                # Get table schemas from MDSCHEMA_CUBES
                tables_schema = adomd_connection.GetSchemaDataSet(
                    AdomdSchemaGuid.Cubes, []
                )

                table_names = []
                for table_row in tables_schema.Tables[0].Rows:
                    cube_name = table_row["CUBE_NAME"]
                    cube_type = table_row["CUBE_TYPE"]
                    if cube_type == 1:  # User-defined cube (table)
                        table_names.append(cube_name)

                logger.info(f"Found {len(table_names)} tables")

                # Get table descriptions in batch for performance
                table_descriptions = self._get_all_table_descriptions(table_names)

                # Get all relationships in batch for performance
                from .relationship_service import RelationshipService
                relationship_service = RelationshipService(self.connector)
                table_relationships = relationship_service.get_all_relationships(table_names)

                # Process each table
                for table_name in table_names:
                    table_description = table_descriptions.get(table_name)
                    relationships = table_relationships.get(table_name, [])

                    table_info = {
                        "name": table_name,
                        "description": table_description or "No description available",
                        "relationships": relationships,
                    }
                    tables_list.append(table_info)

                return tables_list

        except Exception as e:
            logger.error(f"Failed to discover tables: {str(e)}")
            raise Exception(f"Failed to discover tables: {str(e)}")

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a specific table"""
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

                # First get the table description
                table_description = self._get_table_description_direct(table_name)

                # Try to get column information
                try:
                    # Get basic column information
                    column_query = f"EVALUATE TOPN(1, {table_name})"
                    cursor.execute(column_query)
                    
                    # Get column names and types from cursor description
                    columns_basic = []
                    if cursor.description:
                        for col_desc in cursor.description:
                            col_name = col_desc[0]
                            col_type = col_desc[1].__name__ if hasattr(col_desc[1], '__name__') else str(col_desc[1])
                            columns_basic.append({
                                "name": col_name,
                                "data_type": col_type
                            })

                    cursor.fetchall()  # consume results
                    cursor.close()

                    # Get enhanced column information with descriptions
                    enhanced_columns = []
                    column_descriptions = self._get_column_descriptions(table_name)
                    
                    for col_basic in columns_basic:
                        col_name = col_basic["name"]
                        col_data_type = col_basic["data_type"]
                        
                        # Find matching description
                        col_description = None
                        for col_desc_info in column_descriptions:
                            if col_desc_info.get("name") == col_name:
                                col_description = col_desc_info.get("description")
                                break

                        enhanced_columns.append(
                            {
                                "name": col_name,
                                "description": col_description or "No description available",
                                "data_type": col_data_type,
                            }
                        )

                    return {
                        "table_name": table_name,
                        "type": "data_table",
                        "description": table_description or "No description available",
                        "columns": enhanced_columns,
                    }
                except Exception as e:
                    # This might be a measure table, or there was an error getting column info
                    logger.warning(f"Failed to get column information for table '{table_name}', treating as measure table: {e}")
                    cursor.close()
                    from .measure_service import MeasureService
                    measure_service = MeasureService(self.connector)
                    measure_info = measure_service.get_measures_for_table(table_name)
                    measure_info["description"] = table_description or "No description available"
                    return measure_info

        except Exception as e:
            logger.error(f"Failed to get schema for table '{table_name}': {str(e)}")
            raise Exception(f"Failed to get schema for table '{table_name}': {str(e)}")

    def _get_table_description_direct(self, table_name: str) -> Optional[str]:
        """Get table description using direct Pyadomd connection"""
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
                
                # Query the table schema to get description
                description_query = f"SELECT [Description] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = '{table_name}'"
                cursor.execute(description_query)
                result = cursor.fetchone()
                cursor.close()
                
                if result and result[0]:
                    return result[0]
                    
                return None
        except Exception as e:
            logger.warning(f"Could not get table description for '{table_name}': {str(e)}")
            return None

    def _get_all_table_descriptions(self, table_names: List[str]) -> Dict[str, Optional[str]]:
        """Get descriptions for multiple tables in a single query for performance"""
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
                # First, get all table name-to-ID mappings
                table_names_str = "', '".join(table_names)
                query = f"SELECT [Name], [Description] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] IN ('{table_names_str}')"
                
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                cursor.close()
                
                # Create mapping
                descriptions = {}
                for table_name in table_names:
                    descriptions[table_name] = None
                    
                for result in results:
                    table_name = result[0]
                    description = result[1] if len(result) > 1 else None
                    descriptions[table_name] = description
                    
                return descriptions

        except Exception as e:
            logger.warning(f"Failed to get table descriptions in batch: {str(e)}")
            return {}

    def _get_column_descriptions(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column descriptions for a table"""
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
                # First get the table ID
                id_cursor = conn.cursor()
                id_query = f"SELECT [ID] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = '{table_name}'"
                id_cursor.execute(id_query)
                table_id_result = id_cursor.fetchone()

                if not table_id_result:
                    id_cursor.close()
                    return []

                # Extract table ID from generator and tuple
                table_id_tuple = list(table_id_result)[0]  # Get first tuple from generator
                table_id = table_id_tuple[0]  # Get the integer from the tuple
                id_cursor.close()

                # Get column descriptions from TMSCHEMA_COLUMNS
                desc_cursor = conn.cursor()
                desc_query = f"""
                SELECT
                    [ExplicitName] as ColumnName,
                    [Description] as ColumnDescription,
                    [ExplicitDataType] as DataType
                FROM $SYSTEM.TMSCHEMA_COLUMNS
                WHERE [TableID] = {table_id}
                ORDER BY [ExplicitName]
                """
                desc_cursor.execute(desc_query)
                descriptions = desc_cursor.fetchall()
                desc_cursor.close()

                result = []
                for desc in descriptions:
                    column_name = desc[0] if desc[0] else "Unknown"
                    column_description = desc[1] if len(desc) > 1 and desc[1] else None
                    col_data_type = desc[2] if len(desc) > 2 else None
                    result.append({
                        "name": column_name,
                        "description": column_description,
                        "data_type": col_data_type
                    })

                return result

        except Exception as e:
            logger.warning(f"Failed to get column descriptions for '{table_name}': {str(e)}")
            return []