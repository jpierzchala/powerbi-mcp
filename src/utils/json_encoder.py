"""JSON encoding utilities for PowerBI data types."""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class PowerBIJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Power BI data types"""

    def default(self, obj):
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
