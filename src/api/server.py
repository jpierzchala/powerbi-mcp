"""PowerBI MCP Server implementation."""

import asyncio
import os
from typing import List, Optional

import uvicorn
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp.types import Tool
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route

from api.handlers import PowerBIHandlers
from config.environment import logger

# Updated imports
try:
    from mcp.server.types import ToolResult
    from mcp.types import Prompt, Resource, TextContent
except ImportError:
    from mcp.types import TextContent

    # Define missing types as stubs if not available
    Resource = None
    Prompt = None


class PowerBIMCPServer:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.getenv("HOST", "0.0.0.0")
        self.port = int(port or os.getenv("PORT", "8000"))
        self.server = Server("powerbi-mcp-server")
        self.handlers = PowerBIHandlers()

        # Setup server handlers
        self._setup_handlers()

    @property
    def connector(self):
        """Expose the connector for backward compatibility with tests."""
        return self.handlers.connector

    @connector.setter
    def connector(self, value):
        """Allow setting the connector for backward compatibility with tests."""
        self.handlers.connector = value

    @property
    def analyzer(self):
        """Expose the analyzer for backward compatibility with tests."""
        return self.handlers.analyzer

    @property
    def is_connected(self):
        """Expose the connection status for backward compatibility with tests."""
        return self.handlers.is_connected

    @is_connected.setter
    def is_connected(self, value):
        """Allow setting the connection status for backward compatibility with tests."""
        self.handlers.is_connected = value

    async def _async_prepare_context(self):
        """Expose the async prepare context method for backward compatibility with tests."""
        return await self.handlers._async_prepare_context()

    async def _handle_connect(self, arguments):
        """Legacy method removed: explicit connect is no longer supported."""
        return "The 'connect_powerbi' tool has been removed. Please pass connection parameters directly to each call."

    async def _handle_list_tables(self, arguments):
        """Expose the handle list tables method for backward compatibility with tests."""
        return await self.handlers.handle_list_tables(arguments)

    async def _handle_get_table_info(self, arguments):
        """Expose the handle get table info method for backward compatibility with tests."""
        return await self.handlers.handle_get_table_info(arguments)

    async def _handle_query_data(self, arguments):
        """Expose the handle query data method for backward compatibility with tests."""
        return await self.handlers.handle_query_data(arguments)

    async def _handle_execute_dax(self, arguments):
        """Expose the handle execute dax method for backward compatibility with tests."""
        return await self.handlers.handle_execute_dax(arguments)

    async def _handle_suggest_questions(self):
        """Expose the handle suggest questions method for backward compatibility with tests."""
        return await self.handlers.handle_suggest_questions()

    def _openai_enabled(self) -> bool:
        """Return True if OpenAI features are enabled"""
        return bool(os.getenv("OPENAI_API_KEY"))

    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            tools = [
                Tool(
                    name="list_tables",
                    description="List all tables in a Power BI dataset (stateless)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            # Endpoint aliases for user convenience
                            "xmla_endpoint": {"type": "string", "description": "XMLA endpoint URL"},
                            "server": {"type": "string", "description": "Alias for xmla_endpoint"},
                            "data_source": {"type": "string", "description": "Alias for xmla_endpoint"},
                            "workspace_connection": {"type": "string", "description": "Alias for xmla_endpoint"},
                            # Catalog/dataset aliases
                            "initial_catalog": {"type": "string", "description": "Dataset name"},
                            "database": {"type": "string", "description": "Alias for initial_catalog"},
                            "catalog": {"type": "string", "description": "Alias for initial_catalog"},
                            "dataset": {"type": "string", "description": "Alias for initial_catalog"},
                            "model": {"type": "string", "description": "Alias for initial_catalog"},
                            # Credentials (optional; fallback to DEFAULT_* env vars)
                            "tenant_id": {"type": "string"},
                            "client_id": {"type": "string"},
                            "client_secret": {"type": "string"},
                        },
                        "required": ["initial_catalog"],
                    },
                ),
                Tool(
                    name="get_table_info",
                    description="Get detailed information about a specific table (stateless)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string", "description": "Name of the table"},
                            # Connection parameters (same aliases as list_tables)
                            "xmla_endpoint": {"type": "string"},
                            "server": {"type": "string"},
                            "data_source": {"type": "string"},
                            "workspace_connection": {"type": "string"},
                            "initial_catalog": {"type": "string"},
                            "database": {"type": "string"},
                            "catalog": {"type": "string"},
                            "dataset": {"type": "string"},
                            "model": {"type": "string"},
                            "tenant_id": {"type": "string"},
                            "client_id": {"type": "string"},
                            "client_secret": {"type": "string"},
                        },
                        "required": ["table_name", "initial_catalog"],
                    },
                ),
                Tool(
                    name="execute_dax",
                    description="Execute a custom DAX query (stateless)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dax_query": {"type": "string", "description": "DAX query to execute"},
                            # Connection parameters (same aliases as list_tables)
                            "xmla_endpoint": {"type": "string"},
                            "server": {"type": "string"},
                            "data_source": {"type": "string"},
                            "workspace_connection": {"type": "string"},
                            "initial_catalog": {"type": "string"},
                            "database": {"type": "string"},
                            "catalog": {"type": "string"},
                            "dataset": {"type": "string"},
                            "model": {"type": "string"},
                            "tenant_id": {"type": "string"},
                            "client_id": {"type": "string"},
                            "client_secret": {"type": "string"},
                        },
                        "required": ["dax_query", "initial_catalog"],
                    },
                ),
            ]

            if self._openai_enabled():
                tools.append(
                    Tool(
                        name="query_data",
                        description="Ask a question about the data in natural language",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "question": {"type": "string", "description": "Your question about the data"}
                            },
                            "required": ["question"],
                        },
                    )
                )
                tools.append(
                    Tool(
                        name="suggest_questions",
                        description="Get suggestions for interesting questions to ask about the data",
                        inputSchema={"type": "object", "properties": {}},
                    )
                )

            return tools

        @self.server.list_resources()
        async def handle_list_resources():
            """Return empty list of resources - stub implementation"""
            return []

        @self.server.list_prompts()
        async def handle_list_prompts():
            """Return empty list of prompts - stub implementation"""
            return []

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[dict]) -> List[TextContent]:
            """Handle tool calls and return results as TextContent"""
            return await self.handlers.handle_call_tool(name, arguments)

    async def run(self):
        """Run the MCP server over SSE"""
        persist = os.getenv("MCP_PERSIST", "1") != "0"
        host = self.host
        port = self.port

        sse = SseServerTransport("/messages/")

        class SseApp:
            async def __call__(self, scope, receive, send):
                async with sse.connect_sse(scope, receive, send) as (
                    read_stream,
                    write_stream,
                ):
                    await self_server.run(
                        read_stream,
                        write_stream,
                        InitializationOptions(
                            server_name="powerbi-mcp-server",
                            server_version="1.0.0",
                            capabilities=self_server.get_capabilities(
                                notification_options=NotificationOptions(),
                                experimental_capabilities={},
                            ),
                        ),
                    )
                # Return empty response once stream closes
                await Response()(scope, receive, send)

        self_server = self.server
        sse_app = SseApp()

        routes = [
            Route("/sse", sse_app, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ]

        app = Starlette(routes=routes)
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)

        try:
            logger.info("Starting Power BI MCP Server on %s:%s...", host, port)
            await server.serve()
            logger.info("Server run completed")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            if persist:
                logger.info("Entering idle loop to keep server running")
                try:
                    while True:
                        await asyncio.sleep(3600)
                except asyncio.CancelledError:
                    pass
            logger.info("Server shutting down")
