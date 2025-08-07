"""Query operations for PowerBI data models."""

import logging
from typing import Any, Dict, List

from utils.json_encoder import PowerBIJSONEncoder
from utils.dax_utils import clean_dax_query

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


class QueryService:
    """Handles query and data operations for PowerBI data models."""
    
    def __init__(self, connector):
        """Initialize with a PowerBI connector."""
        self.connector = connector
        
    def execute_dax_query(self, dax_query: str) -> List[Dict[str, Any]]:
        """Execute a DAX query and return results"""
        if not self.connector.connected:
            raise Exception("Not connected to Power BI")

        self.connector._check_pyadomd()

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

            with Pyadomd(self.connector.connection_string) as conn:
                cursor = conn.cursor()
                cursor.execute(cleaned_query)
                
                # Get column names from cursor description
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Fetch all results
                results = cursor.fetchall()
                cursor.close()
                
                # Convert to list of dictionaries with proper JSON encoding
                data = []
                for row in results:
                    row_dict = {}
                    for i, value in enumerate(row):
                        if i < len(column_names):
                            # Use our custom encoder logic for individual values
                            if hasattr(value, 'isoformat'):  # datetime objects
                                row_dict[column_names[i]] = value.isoformat()
                            elif hasattr(value, '__float__'):  # Decimal objects
                                row_dict[column_names[i]] = float(value)
                            else:
                                row_dict[column_names[i]] = value
                    data.append(row_dict)
                
                logger.info(f"Query returned {len(data)} rows")
                return data

        except Exception as e:
            logger.error(f"DAX query failed: {str(e)}")
            raise Exception(f"DAX query failed: {str(e)}")

    def get_sample_data(self, table_name: str, num_rows: int = 10) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        dax_query = f"EVALUATE TOPN({num_rows}, {table_name})"
        return self.execute_dax_query(dax_query)