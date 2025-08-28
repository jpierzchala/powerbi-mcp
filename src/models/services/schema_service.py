"""Schema operations for PowerBI data models."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Always get variables from server module for test compatibility
def _get_adomd_objects():
    """Get ADOMD objects from server module for test compatibility."""
    try:
        import server

        return server.Pyadomd, server.AdomdSchemaGuid
    except ImportError:
        # Fallback to direct import if server module not available
        from config.adomd_setup import initialize_adomd

        _, pyadomd, _, adomd_schema_guid = initialize_adomd()
        return pyadomd, adomd_schema_guid


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
            Pyadomd, AdomdSchemaGuid = _get_adomd_objects()

            with Pyadomd(self.connector.connection_string) as pyadomd_conn:
                adomd_connection = pyadomd_conn.conn

                # Get table schemas from MDSCHEMA_TABLES (original logic)
                tables_dataset = adomd_connection.GetSchemaDataSet(AdomdSchemaGuid.Tables, None)

                # First, collect all user-facing table names
                user_table_names = []
                tables_list_obj = getattr(tables_dataset, "Tables", None)
                if tables_list_obj and len(tables_list_obj) > 0:
                    schema_table = tables_list_obj[0]
                    for row in schema_table.Rows:
                        table_name = row["TABLE_NAME"]
                        if (
                            not table_name.startswith("$")
                            and not table_name.startswith("DateTableTemplate_")
                            and not row["TABLE_SCHEMA"] == "$SYSTEM"
                        ):
                            user_table_names.append(table_name)

                table_names = user_table_names

                logger.info(f"Found {len(table_names)} tables")

                # Get table descriptions in batch for performance
                # Use connector method if available (for test compatibility)
                if hasattr(self.connector, "_get_all_table_descriptions"):
                    table_descriptions = self.connector._get_all_table_descriptions(table_names)
                else:
                    table_descriptions = self._get_all_table_descriptions(table_names)

                # Get all relationships in batch for performance
                # Use connector method if available (for test compatibility)
                if hasattr(self.connector, "_get_all_relationships"):
                    table_relationships = self.connector._get_all_relationships(table_names)
                else:
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
            Pyadomd, _ = _get_adomd_objects()

            with Pyadomd(self.connector.connection_string) as conn:
                cursor = conn.cursor()

                # First get the table description
                # Use connector method if available (for test compatibility)
                if hasattr(self.connector, "_get_table_description_direct"):
                    table_description = self.connector._get_table_description_direct(table_name)
                else:
                    table_description = self._get_table_description_direct(table_name)

                # Try to get column information
                try:
                    # Get basic column information
                    # Quote table names to handle spaces/special chars in DAX identifiers
                    safe_table = table_name.replace("'", "''")
                    column_query = f"EVALUATE TOPN(1, '{safe_table}')"
                    cursor.execute(column_query)

                    # Get column names from cursor description (original behavior)
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []

                    cursor.fetchall()  # consume results
                    cursor.close()

                    # Get enhanced column information with descriptions
                    enhanced_columns = []
                    # Use connector method if available (for test compatibility)
                    if hasattr(self.connector, "_get_column_descriptions"):
                        column_descriptions = self.connector._get_column_descriptions(table_name)
                    else:
                        column_descriptions = self._get_column_descriptions(table_name)

                    for col_name in columns:
                        # Find description for this column
                        col_description = None
                        col_data_type = None

                        # Try exact match first
                        for col_info in column_descriptions:
                            if col_info["name"] == col_name:
                                col_description = col_info["description"]
                                col_data_type = col_info["data_type"]
                                break

                        # If no exact match, try partial match (remove table prefix if present)
                        if not col_description:
                            # Extract column name from format like "Employee Skills[Id]" -> "Id"
                            if "[" in col_name and "]" in col_name:
                                clean_col_name = col_name.split("[")[1].replace("]", "")
                            else:
                                clean_col_name = col_name

                            for col_info in column_descriptions:
                                if col_info["name"] == clean_col_name:
                                    col_description = col_info["description"]
                                    col_data_type = col_info["data_type"]
                                    logger.debug(f"Matched column '{col_name}' with '{clean_col_name}'")
                                    break

                        # Create enhanced column info
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
                    logger.warning(
                        f"Failed to get column information for table '{table_name}', treating as measure table: {e}"
                    )
                    cursor.close()
                    # Use connector method if available (for test compatibility)
                    if hasattr(self.connector, "get_measures_for_table"):
                        measure_info = self.connector.get_measures_for_table(table_name)
                    else:
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
            Pyadomd, _ = _get_adomd_objects()

            with Pyadomd(self.connector.connection_string) as conn:
                cursor = conn.cursor()

                # Query the table schema to get description
                safe_table = table_name.replace("'", "''")
                description_query = (
                    f"SELECT [Description] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = '{safe_table}'"
                )
                cursor.execute(description_query)
                results = cursor.fetchall()
                cursor.close()

                if results:
                    first = results[0]
                    if first and first[0]:
                        return str(first[0])

                return None
        except Exception as e:
            logger.warning(f"Could not get table description for '{table_name}': {str(e)}")
            return None

    def _get_all_table_descriptions(self, table_names: List[str]) -> Dict[str, Optional[str]]:
        """Get descriptions for multiple tables in a single query for performance"""
        if not self.connector.connected:
            return {}

        try:
            Pyadomd, _ = _get_adomd_objects()

            with Pyadomd(self.connector.connection_string) as conn:
                cursor = conn.cursor()
                # Get all table descriptions in one query (original behavior)
                # Note: DMV queries don't support IN clauses, so we need to be creative
                desc_query = "SELECT [Name], [Description] FROM $SYSTEM.TMSCHEMA_TABLES"
                logger.debug(f"Batch descriptions query: {desc_query}")
                cursor.execute(desc_query)
                results = cursor.fetchall()
                cursor.close()

                # Build a mapping of table name to description
                descriptions = {}
                for result in results:
                    table_name = result[0] if result[0] else None
                    description = result[1] if len(result) > 1 and result[1] else None
                    if table_name:
                        descriptions[table_name] = description

                # Return only descriptions for requested tables
                return {name: descriptions.get(name) for name in table_names}

        except Exception as e:
            logger.warning(f"Failed to get batch table descriptions: {str(e)}")
            # Fallback to individual queries if batch fails
            descriptions = {}
            for table_name in table_names:
                descriptions[table_name] = self._get_table_description_direct(table_name)
            return descriptions

    def _get_column_descriptions(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column descriptions for a table"""
        try:
            Pyadomd, _ = _get_adomd_objects()

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
                    result.append({"name": column_name, "description": column_description, "data_type": col_data_type})

                return result

        except Exception as e:
            logger.warning(f"Failed to get column descriptions for '{table_name}': {str(e)}")
            return []
