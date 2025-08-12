"""Environment setup and configuration loading."""

import logging
import os
import sys

from dotenv import load_dotenv


def setup_logging():
    """Configure logging for MCP debugging."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr
    )
    return logging.getLogger(__name__)


def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()


logger = setup_logging()
