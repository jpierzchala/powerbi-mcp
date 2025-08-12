"""JSON encoding utilities for PowerBI data types."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class PowerBIJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Power BI data types"""

    def default(self, obj):
        """
        Convert Power BI data types to JSON-serializable formats.

        Handles datetime objects (converts to ISO format), Decimal objects (converts to float),
        and other objects with __dict__ attribute (converts to string representation).

        Args:
            obj: The object to be serialized

        Returns:
            JSON-serializable representation of the object
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, "__dict__"):
            return str(obj)
        return super().default(obj)


def safe_json_dumps(data: Any, indent: int = 2) -> str:
    """Safely serialize data containing datetime and other non-JSON types"""
    return json.dumps(data, indent=indent, cls=PowerBIJSONEncoder)
