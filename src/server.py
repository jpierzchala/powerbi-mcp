"""PowerBI MCP Server - Main entry point."""

import argparse
import asyncio
import os
import sys

# Add the src directory to the Python path for imports to work
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = current_dir
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import and re-export main classes for backward compatibility with tests
from src.api.server import PowerBIMCPServer
from src.config.adomd_setup import initialize_adomd
from src.config.environment import load_environment, logger
from src.models.analyzer import DataAnalyzer
from src.models.connector import PowerBIConnector
from src.utils.dax_utils import clean_dax_query
from src.utils.json_encoder import PowerBIJSONEncoder, safe_json_dumps

# Initialize ADOMD components for backward compatibility
clr, Pyadomd, adomd_loaded, AdomdSchemaGuid = initialize_adomd()

# Re-export for backward compatibility
__all__ = [
    'PowerBIMCPServer',
    'PowerBIConnector', 
    'DataAnalyzer',
    'clean_dax_query',
    'safe_json_dumps',
    'PowerBIJSONEncoder',
    'Pyadomd',
    'AdomdSchemaGuid',
    'clr',
    'adomd_loaded'
]


# Main entry point
async def main():
    """Main entry point for the PowerBI MCP Server."""
    # Load environment variables
    load_environment()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PowerBI MCP Server")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to bind to")
    args = parser.parse_args()

    # Create and run the server
    server = PowerBIMCPServer(host=args.host, port=args.port)
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)