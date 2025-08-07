"""PowerBI Connector class for database operations."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from config.adomd_setup import initialize_adomd
from config.environment import logger
from utils.dax_utils import clean_dax_query

# Initialize ADOMD components
clr, Pyadomd, adomd_loaded, AdomdSchemaGuid = initialize_adomd()

# For backward compatibility with tests, check if we should use server module variables
try:
    import server

    # Use server variables if they exist (for test compatibility)
    if hasattr(server, "Pyadomd"):
        Pyadomd = server.Pyadomd
    if hasattr(server, "AdomdSchemaGuid"):
        AdomdSchemaGuid = server.AdomdSchemaGuid
except ImportError:
    # server module not available yet (during initial import), use local variables
    pass


class PowerBIConnector:
    def __init__(self):
        self.connection_string = None
        self.connected = False
        self.tables = []
        self.metadata = {}
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _check_pyadomd(self):
        # Import here to avoid circular import issues
        global Pyadomd
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
            with Pyadomd(self.connection_string):
                self.connected = True
                logger.info(f"Connected to Power BI dataset: {initial_catalog}")
                # Don't discover tables during connection to speed up
                return True
        except Exception as e:
            self.connected = False
            logger.error(f"Connection failed: {str(e)}")
            raise Exception(f"Connection failed: {str(e)}")

    def discover_tables(self) -> List[Dict[str, Any]]:
        """Discover all user-facing tables in the dataset with their descriptions and relationships"""
        if not self.connected:
            raise Exception("Not connected to Power BI")

        self._check_pyadomd()

        # Return cached tables if already discovered
        if self.tables:
            return self.tables

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

            with Pyadomd(self.connection_string) as pyadomd_conn:
                adomd_connection = pyadomd_conn.conn
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

                # Batch fetch descriptions and relationships for performance
                logger.info(f"Fetching metadata for {len(user_table_names)} tables using optimized batch queries")
                table_descriptions = self._get_all_table_descriptions(user_table_names)
                table_relationships = self._get_all_relationships(user_table_names)

                # Build the final tables list
                for table_name in user_table_names:
                    description = table_descriptions.get(table_name) or "No description available"
                    relationships = table_relationships.get(table_name, [])

                    tables_list.append(
                        {
                            "name": table_name,
                            "description": description,
                            "relationships": relationships,
                        }
                    )

            self.tables = tables_list
            logger.info(f"Discovered {len(tables_list)} tables with relationships using optimized queries")
            return tables_list
        except Exception as e:
            logger.error(f"Failed to discover tables: {str(e)}")
            raise Exception(f"Failed to discover tables: {str(e)}")

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table including description and column descriptions"""
        if not self.connected:
            raise Exception("Not connected to Power BI")

        self._check_pyadomd()

        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string) as conn:
                cursor = conn.cursor()

                # Get table description
                table_description = self._get_table_description_direct(table_name)

                # Try to get column information
                try:
                    dax_query = f"EVALUATE TOPN(1, '{table_name}')"
                    cursor.execute(dax_query)
                    columns = [desc[0] for desc in cursor.description]
                    cursor.close()

                    # Get column descriptions from TMSCHEMA_COLUMNS
                    column_descriptions = self._get_column_descriptions(table_name)

                    # Create enhanced columns list with descriptions
                    enhanced_columns = []
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
                    logger.warning(f"Failed to get column information for table '{table_name}', treating as measure table: {e}")
                    cursor.close()
                    measure_info = self.get_measures_for_table(table_name)
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

            with Pyadomd(self.connection_string) as conn:
                cursor = conn.cursor()
                # Try different approaches to get table description

                # First try: Direct query
                desc_query = f"SELECT [Description] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = '{table_name}'"
                logger.debug(f"Trying query: {desc_query}")
                cursor.execute(desc_query)
                results = cursor.fetchall()  # Use fetchall instead of fetchone
                cursor.close()

                if results and len(results) > 0:
                    result = results[0]
                    if result and len(result) > 0 and result[0]:
                        logger.debug(f"Found description for {table_name}: {result[0]}")
                        return str(result[0])
                    else:
                        logger.debug(f"Description is empty for table {table_name}")
                else:
                    logger.debug(f"No results found for table {table_name}")

                # Second try: Show all columns to understand the schema
                cursor = conn.cursor()
                debug_query = "SELECT TOP 5 [Name], [Description] FROM $SYSTEM.TMSCHEMA_TABLES"
                logger.debug(f"Debug query: {debug_query}")
                cursor.execute(debug_query)
                debug_results = cursor.fetchall()
                cursor.close()

                logger.debug(f"Debug results from TMSCHEMA_TABLES: {debug_results}")

                return None
        except Exception as e:
            logger.debug(f"Failed to get description for table '{table_name}': {str(e)}")
            return None

    def _get_table_relationships(self, table_name: str) -> List[Dict[str, Any]]:
        """Get relationships for a specific table"""
        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string) as conn:
                # First get the table ID
                cursor = conn.cursor()
                table_id_query = f"SELECT [ID] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = '{table_name}'"
                logger.debug(f"Table ID query: {table_id_query}")
                cursor.execute(table_id_query)
                table_id_result = cursor.fetchone()
                logger.debug(f"fetchone() returned: {table_id_result} (type: {type(table_id_result)})")

                if not table_id_result:
                    cursor.close()
                    logger.debug(f"Table ID not found for {table_name}")
                    return []

                # fetchone() returns a generator that yields tuples, we need the first value from the first tuple
                table_id_tuple = list(table_id_result)[0]  # Get first tuple from generator: (13,)
                table_id = table_id_tuple[0]  # Get the integer from the tuple: 13
                cursor.close()
                logger.debug(f"Found table ID {table_id} (type: {type(table_id)}) for table '{table_name}'")
                relationships = []

                # First, let's see what relationships exist in the model at all
                cursor = conn.cursor()
                all_rels_query = "SELECT [FromTableID], [ToTableID], [IsActive] FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS"
                logger.debug(f"All relationships query: {all_rels_query}")
                cursor.execute(all_rels_query)
                all_rels = cursor.fetchall()
                cursor.close()
                logger.debug(f"Found {len(all_rels)} total relationships in model: {all_rels}")

                # Get relationships where this table is the "From" table (Many side)
                cursor = conn.cursor()
                from_rel_query = f"""
                SELECT
                    [ToTableID], [ToColumnID], [FromColumnID],
                    [IsActive], [Type], [CrossFilteringBehavior],
                    [FromCardinality], [ToCardinality]
                FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS
                WHERE [FromTableID] = {table_id}
                """
                logger.debug(f"From relationships query: {from_rel_query}")
                cursor.execute(from_rel_query)
                from_relationships = cursor.fetchall()
                cursor.close()
                logger.debug(
                    f"Found {len(from_relationships)} 'from' relationships for table {table_name}: {from_relationships}"
                )

                # Process "From" relationships (where current table is Many side)
                for rel in from_relationships:
                    to_table_id, to_column_id, from_column_id = rel[0], rel[1], rel[2]
                    is_active, _, cross_filter = rel[3], rel[4], rel[5]
                    from_cardinality, to_cardinality = rel[6], rel[7]

                    # Get related table name
                    cursor = conn.cursor()
                    to_table_query = f"SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [ID] = {to_table_id}"
                    cursor.execute(to_table_query)
                    to_table_result = cursor.fetchone()

                    if to_table_result:
                        to_table_name = list(to_table_result)[0][0]  # Extract string from tuple
                        cursor.close()

                        # Get column names
                        cursor = conn.cursor()
                        from_col_query = (
                            f"SELECT [ExplicitName] FROM $SYSTEM.TMSCHEMA_COLUMNS WHERE [ID] = {from_column_id}"
                        )
                        cursor.execute(from_col_query)
                        from_col_result = cursor.fetchone()
                        from_col_name = (
                            list(from_col_result)[0][0] if from_col_result else None
                        )  # Extract string from tuple
                        cursor.close()

                        cursor = conn.cursor()
                        to_col_query = (
                            f"SELECT [ExplicitName] FROM $SYSTEM.TMSCHEMA_COLUMNS WHERE [ID] = {to_column_id}"
                        )
                        cursor.execute(to_col_query)
                        to_col_result = cursor.fetchone()
                        to_col_name = list(to_col_result)[0][0] if to_col_result else None  # Extract string from tuple
                        cursor.close()

                        if from_col_name and to_col_name:
                            relationships.append(
                                {
                                    "relatedTable": to_table_name,
                                    "fromColumn": from_col_name,
                                    "toColumn": to_col_name,
                                    "cardinality": self._format_cardinality(from_cardinality, to_cardinality),
                                    "isActive": bool(is_active),
                                    "crossFilterDirection": self._format_cross_filter(cross_filter),
                                    "relationshipType": "Many-to-One",
                                }
                            )
                    else:
                        cursor.close()

                # Get relationships where this table is the "To" table (One side)
                cursor = conn.cursor()
                to_rel_query = f"""
                SELECT
                    [FromTableID], [FromColumnID], [ToColumnID],
                    [IsActive], [Type], [CrossFilteringBehavior],
                    [FromCardinality], [ToCardinality]
                FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS
                WHERE [ToTableID] = {table_id}
                """
                logger.debug(f"To relationships query: {to_rel_query}")
                cursor.execute(to_rel_query)
                to_relationships = cursor.fetchall()
                cursor.close()
                logger.debug(
                    f"Found {len(to_relationships)} 'to' relationships for table {table_name}: {to_relationships}"
                )

                # Process "To" relationships (where current table is One side)
                for rel in to_relationships:
                    from_table_id, from_column_id, to_column_id = rel[0], rel[1], rel[2]
                    is_active, _, cross_filter = rel[3], rel[4], rel[5]
                    from_cardinality, to_cardinality = rel[6], rel[7]

                    # Get related table name
                    cursor = conn.cursor()
                    from_table_query = f"SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [ID] = {from_table_id}"
                    cursor.execute(from_table_query)
                    from_table_result = cursor.fetchone()

                    if from_table_result:
                        from_table_name = list(from_table_result)[0][0]  # Extract string from tuple
                        cursor.close()

                        # Get column names
                        cursor = conn.cursor()
                        from_col_query = (
                            f"SELECT [ExplicitName] FROM $SYSTEM.TMSCHEMA_COLUMNS WHERE [ID] = {from_column_id}"
                        )
                        cursor.execute(from_col_query)
                        from_col_result = cursor.fetchone()
                        from_col_name = (
                            list(from_col_result)[0][0] if from_col_result else None
                        )  # Extract string from tuple
                        cursor.close()

                        cursor = conn.cursor()
                        to_col_query = (
                            f"SELECT [ExplicitName] FROM $SYSTEM.TMSCHEMA_COLUMNS WHERE [ID] = {to_column_id}"
                        )
                        cursor.execute(to_col_query)
                        to_col_result = cursor.fetchone()
                        to_col_name = list(to_col_result)[0][0] if to_col_result else None  # Extract string from tuple
                        cursor.close()

                        if from_col_name and to_col_name:
                            relationships.append(
                                {
                                    "relatedTable": from_table_name,
                                    "fromColumn": to_col_name,  # Current table column
                                    "toColumn": from_col_name,  # Related table column
                                    "cardinality": self._format_cardinality(to_cardinality, from_cardinality),
                                    "isActive": bool(is_active),
                                    "crossFilterDirection": self._format_cross_filter(cross_filter),
                                    "relationshipType": "One-to-Many",
                                }
                            )
                    else:
                        cursor.close()

                logger.debug(f"Found {len(relationships)} relationships for table {table_name}")
                return relationships

        except Exception as e:
            logger.warning(f"Failed to get relationships for table '{table_name}': {str(e)}")
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")
            return []

    def _get_all_table_descriptions(self, table_names: List[str]) -> Dict[str, Optional[str]]:
        """Get descriptions for all tables in a single query for performance"""
        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string) as conn:
                cursor = conn.cursor()
                # Get all table descriptions in one query
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
            return {name: self._get_table_description_direct(name) for name in table_names}

    def _get_all_relationships(self, table_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get relationships for all tables in optimized batch queries"""
        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string) as conn:
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
                                "cardinality": self._format_cardinality(from_cardinality, to_cardinality),
                                "isActive": bool(is_active),
                                "crossFilterDirection": self._format_cross_filter(cross_filter),
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
                                "cardinality": self._format_cardinality(to_cardinality, from_cardinality),
                                "isActive": bool(is_active),
                                "crossFilterDirection": self._format_cross_filter(cross_filter),
                                "relationshipType": "One-to-Many",
                            }
                        )

                return table_relationships

        except Exception as e:
            logger.warning(f"Failed to get batch relationships: {str(e)}")
            # Fallback to individual queries if batch fails
            return {name: self._get_table_relationships(name) for name in table_names}

    def _get_column_descriptions(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column descriptions for a specific table"""
        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string) as conn:
                # First get the table ID
                cursor = conn.cursor()
                table_id_query = f"SELECT [ID] FROM $SYSTEM.TMSCHEMA_TABLES WHERE [Name] = '{table_name}'"
                logger.debug(f"Table ID query for column descriptions: {table_id_query}")
                cursor.execute(table_id_query)
                table_id_result = cursor.fetchone()

                if not table_id_result:
                    cursor.close()
                    logger.debug(f"Table ID not found for {table_name}")
                    return []

                # Extract table ID from generator and tuple
                table_id_tuple = list(table_id_result)[0]  # Get first tuple from generator
                table_id = table_id_tuple[0]  # Get the integer from the tuple
                cursor.close()
                logger.debug(f"Found table ID: {table_id} for column descriptions")

                # Get column descriptions from TMSCHEMA_COLUMNS
                cursor = conn.cursor()
                columns_query = f"""
                SELECT
                    [ExplicitName] as ColumnName,
                    [Description] as ColumnDescription,
                    [ExplicitDataType] as DataType
                FROM $SYSTEM.TMSCHEMA_COLUMNS
                WHERE [TableID] = {table_id}
                ORDER BY [ExplicitName]
                """
                logger.debug(f"Columns query: {columns_query}")
                cursor.execute(columns_query)
                columns_results = cursor.fetchall()
                cursor.close()

                logger.debug(f"Found {len(columns_results)} columns with metadata")

                # Process results
                column_descriptions = []
                for col_result in columns_results:
                    col_name = col_result[0] if col_result[0] else "Unknown"
                    col_description = col_result[1] if len(col_result) > 1 and col_result[1] else None
                    col_data_type = col_result[2] if len(col_result) > 2 else None

                    column_descriptions.append(
                        {"name": col_name, "description": col_description, "data_type": col_data_type}
                    )

                    # Debug output
                    desc_text = col_description if col_description else "No description"
                    logger.debug(f"Column {col_name} ({col_data_type}): {desc_text}")

                return column_descriptions

        except Exception as e:
            logger.warning(f"Failed to get column descriptions for table '{table_name}': {str(e)}")
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")
            return []

    def _format_cardinality(self, from_cardinality: int, to_cardinality: int) -> str:
        """Format cardinality based on numeric codes"""
        cardinality_map = {1: "One", 2: "Many"}
        from_card = cardinality_map.get(from_cardinality, "Unknown")
        to_card = cardinality_map.get(to_cardinality, "Unknown")
        return f"{from_card}-to-{to_card}"

    def _format_cross_filter(self, cross_filter_behavior: int) -> str:
        """Format cross filter direction based on numeric codes"""
        cross_filter_map = {1: "Single", 2: "Both", 3: "Automatic", 4: "None"}
        return cross_filter_map.get(cross_filter_behavior, "Unknown")

    def get_measures_for_table(self, table_name: str) -> Dict[str, Any]:
        """Get measures for a measure table"""
        if not self.connected:
            raise Exception("Not connected to Power BI")

        self._check_pyadomd()
        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string) as conn:
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

    def execute_dax_query(self, dax_query: str) -> List[Dict[str, Any]]:
        """Execute a DAX query and return results"""
        if not self.connected:
            raise Exception("Not connected to Power BI")

        self._check_pyadomd()

        # Clean the DAX query
        cleaned_query = clean_dax_query(dax_query)
        logger.info(f"Executing DAX query: {cleaned_query}")

        try:
            global Pyadomd
            # Update from server module if available
            try:
                import server

                if hasattr(server, "Pyadomd"):
                    Pyadomd = server.Pyadomd
            except ImportError:
                pass

            with Pyadomd(self.connection_string) as conn:
                cursor = conn.cursor()
                cursor.execute(cleaned_query)

                headers = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                cursor.close()

                # Convert to list of dictionaries
                results = []
                for row in rows:
                    results.append(dict(zip(headers, row)))

                logger.info(f"Query returned {len(results)} rows")
                return results

        except Exception as e:
            logger.error(f"DAX query failed: {str(e)}")
            raise Exception(f"DAX query failed: {str(e)}")

    def get_sample_data(self, table_name: str, num_rows: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        dax_query = f"EVALUATE TOPN({num_rows}, '{table_name}')"
        return self.execute_dax_query(dax_query)
