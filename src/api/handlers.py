"""MCP tool handlers for PowerBI operations."""

import asyncio
import os
import threading
from typing import Any, Dict, List, Optional

from mcp.types import TextContent

from config.environment import logger
from models.analyzer import DataAnalyzer
from models.connector import PowerBIConnector
from utils.json_encoder import safe_json_dumps


class PowerBIHandlers:
    """Handles MCP tool operations for PowerBI functionality."""

    def __init__(self):
        self.connector = PowerBIConnector()
        self.analyzer = None
        self.is_connected = False
        self.connection_lock = threading.Lock()

    def _openai_enabled(self) -> bool:
        """Return True if OpenAI features are enabled"""
        return bool(os.getenv("OPENAI_API_KEY"))

    async def handle_connect(self, arguments: Dict[str, Any]) -> str:
        """Handle connection to Power BI"""
        try:
            with self.connection_lock:
                # Connect to Power BI
                tenant_id = arguments.get("tenant_id") or os.getenv("DEFAULT_TENANT_ID")
                client_id = arguments.get("client_id") or os.getenv("DEFAULT_CLIENT_ID")
                client_secret = arguments.get("client_secret") or os.getenv("DEFAULT_CLIENT_SECRET")

                if not all([tenant_id, client_id, client_secret]):
                    return (
                        "Missing credentials. Provide tenant_id, client_id, and client_secret "
                        "either in the action arguments or via DEFAULT_* values in the .env file."
                    )

                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.connector.connect,
                    arguments["xmla_endpoint"],
                    tenant_id,
                    client_id,
                    client_secret,
                    arguments["initial_catalog"],
                )

                # Initialize the analyzer with OpenAI API key
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OpenAI API key not provided - natural language features disabled")
                    self.analyzer = None
                else:
                    self.analyzer = DataAnalyzer(api_key)

                self.is_connected = True

                # Discover tables in background only if analyzer is available
                if self.analyzer:
                    asyncio.create_task(self._async_prepare_context())

                return f"Successfully connected to Power BI dataset '{arguments['initial_catalog']}'. Discovering tables..."

        except Exception as e:
            self.is_connected = False
            logger.error(f"Connection failed: {str(e)}")
            return f"Connection failed: {str(e)}"

    async def _async_prepare_context(self):
        """Prepare data context asynchronously"""
        try:
            # Discover tables
            tables = await asyncio.get_event_loop().run_in_executor(None, self.connector.discover_tables)

            schemas = {}
            sample_data = {}

            # Get schemas for first 5 tables only to speed up
            for table_info in tables[:5]:
                table_name = table_info["name"]
                try:
                    schema = await asyncio.get_event_loop().run_in_executor(
                        None, self.connector.get_table_schema, table_name
                    )
                    schemas[table_name] = schema

                    if schema["type"] == "data_table":
                        samples = await asyncio.get_event_loop().run_in_executor(
                            None, self.connector.get_sample_data, table_name, 3
                        )
                        sample_data[table_name] = samples
                except Exception as e:
                    logger.warning(f"Failed to get schema for table {table_name}: {e}")

            if self.analyzer:
                # Extract table names for the analyzer
                table_names = [table_info["name"] for table_info in tables]
                self.analyzer.set_data_context(table_names, schemas, sample_data)
                logger.info(f"Context prepared with {len(tables)} tables")

        except Exception as e:
            logger.error(f"Failed to prepare context: {e}")

    async def handle_list_tables(self) -> str:
        """List all available tables with descriptions and relationships"""
        if not self.is_connected:
            return "Not connected to Power BI. Please connect first using 'connect_powerbi'."

        try:
            tables = await asyncio.get_event_loop().run_in_executor(None, self.connector.discover_tables)

            if not tables:
                return "No tables found in the dataset."

            result = "Available tables with relationships:\n\n"
            for table in tables:
                result += f"📊 **{table['name']}**\n"
                result += f"   Description: {table['description']}\n"

                if table.get("relationships"):
                    result += f"   Relationships ({len(table['relationships'])}):\n"
                    for rel in table["relationships"]:
                        result += f"     • {rel['relationshipType']} with {rel['relatedTable']}\n"
                        result += (
                            f"       {table['name']}.{rel['fromColumn']} → {rel['relatedTable']}.{rel['toColumn']}\n"
                        )
                        result += f"       Cardinality: {rel['cardinality']}, Active: {rel['isActive']}\n"
                        result += f"       Cross Filter: {rel['crossFilterDirection']}\n"
                else:
                    result += "   Relationships: None\n"
                result += "\n"

            return result
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return f"Error listing tables: {str(e)}"

    async def handle_get_table_info(self, arguments: Dict[str, Any]) -> str:
        """Get information about a specific table"""
        if not self.is_connected:
            return "Not connected to Power BI. Please connect first."

        table_name = arguments.get("table_name")
        if not table_name:
            return "Please provide a table name."

        try:
            schema = await asyncio.get_event_loop().run_in_executor(None, self.connector.get_table_schema, table_name)

            if schema["type"] == "data_table":
                sample_data = await asyncio.get_event_loop().run_in_executor(
                    None, self.connector.get_sample_data, table_name, 5
                )
                # Extract column names from enhanced column objects
                column_names = [col["name"] for col in schema["columns"]]
                result = (
                    f"Table: {table_name}\n"
                    f"Type: Data Table\n"
                    f"Description: {schema.get('description', 'No description available')}\n"
                    f"Columns: {', '.join(column_names)}\n\nColumn Details:\n"
                )
                # Add detailed column information
                for col in schema["columns"]:
                    result += f"  - {col['name']}: {col.get('description', 'No description')} ({col.get('data_type', 'Unknown type')})\n"
                result += "\nSample data:\n"
                result += safe_json_dumps(sample_data, indent=2)
            elif schema["type"] == "measure_table":
                result = (
                    f"Table: {table_name}\n"
                    f"Type: Measure Table\n"
                    f"Description: {schema.get('description', 'No description available')}\n"
                    f"Measures:\n"
                )
                for measure in schema["measures"]:
                    result += f"\n- {measure['name']}:\n  DAX: {measure['dax']}\n"
            else:
                result = (
                    f"Table: {table_name}\n"
                    f"Type: {schema['type']}\n"
                    f"Description: {schema.get('description', 'No description available')}"
                )

            return result

        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return f"Error getting table info: {str(e)}"

    async def handle_query_data(self, arguments: Dict[str, Any]) -> str:
        """Handle natural language queries about data"""
        if not self.is_connected:
            return "Not connected to Power BI. Please connect first."

        if not self.analyzer:
            return "Data analyzer not initialized."

        question = arguments.get("question")
        if not question:
            return "Please provide a question."

        try:
            # Generate DAX query
            dax_query = await asyncio.get_event_loop().run_in_executor(None, self.analyzer.generate_dax_query, question)

            # Execute the query
            results = await asyncio.get_event_loop().run_in_executor(None, self.connector.execute_dax_query, dax_query)

            # Interpret results
            interpretation = await asyncio.get_event_loop().run_in_executor(
                None, self.analyzer.interpret_results, question, results, dax_query
            )

            response = f"Question: {question}\n\nDAX Query:\n{dax_query}\n\nAnswer:\n{interpretation}"

            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"Error processing query: {str(e)}"

    async def handle_execute_dax(self, arguments: Dict[str, Any]) -> str:
        """Execute a custom DAX query"""
        if not self.is_connected:
            return "Not connected to Power BI. Please connect first."

        dax_query = arguments.get("dax_query")
        if not dax_query:
            return "Please provide a DAX query."

        try:
            results = await asyncio.get_event_loop().run_in_executor(None, self.connector.execute_dax_query, dax_query)
            return safe_json_dumps(results, indent=2)
        except Exception as e:
            logger.error(f"DAX execution error: {e}")
            return f"DAX execution error: {str(e)}"

    async def handle_suggest_questions(self) -> str:
        """Suggest interesting questions about the data"""
        if not self.is_connected:
            return "Not connected to Power BI. Please connect first."

        if not self.analyzer:
            return "Data analyzer not initialized. Please wait for tables to be discovered."

        try:
            questions = await asyncio.get_event_loop().run_in_executor(None, self.analyzer.suggest_questions)
            result = "Here are some questions you might want to ask:\n\n"
            for i, q in enumerate(questions, 1):
                result += f"{i}. {q}\n"

            return result

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return f"Error generating suggestions: {str(e)}"

    async def handle_call_tool(self, name: str, arguments: Optional[Dict[str, Any]]) -> List[TextContent]:
        """Handle tool calls and return results as TextContent"""
        try:
            logger.info(f"Handling tool call: {name}")

            if name == "connect_powerbi":
                result = await self.handle_connect(arguments)
            elif name == "list_tables":
                result = await self.handle_list_tables()
            elif name == "get_table_info":
                result = await self.handle_get_table_info(arguments)
            elif name == "query_data":
                if not self._openai_enabled():
                    result = "OpenAI API key not configured."
                else:
                    result = await self.handle_query_data(arguments)
            elif name == "execute_dax":
                result = await self.handle_execute_dax(arguments)
            elif name == "suggest_questions":
                if not self._openai_enabled():
                    result = "OpenAI API key not configured."
                else:
                    result = await self.handle_suggest_questions()
            else:
                logger.warning(f"Unknown tool: {name}")
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            # Convert string result to TextContent
            return [TextContent(type="text", text=result)]

        except Exception as e:
            logger.error(f"Error executing {name}: {str(e)}", exc_info=True)
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
