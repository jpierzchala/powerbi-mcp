"""DAX query processing utilities."""

import re


def clean_dax_query(dax_query: str) -> str:
    """Remove HTML/XML tags and other artifacts from DAX queries"""
    # Remove HTML/XML tags like <oii>, </oii>, etc.
    cleaned = re.sub(r"<[^>]+>", "", dax_query)
    # Collapse extra whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned
