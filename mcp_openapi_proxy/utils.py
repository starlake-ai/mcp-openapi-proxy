"""
Utility functions for mcp_any_openapi, including logging setup,
OpenAPI fetching, and name normalization.
"""

import os
import sys
import logging
import requests
import re
import json
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# OpenAPI related configurations (add more if needed)
OPENAPI_SPEC_URL = os.getenv("OPENAPI_SPEC_URL") # Example - you can log this

def setup_logging(debug: bool = False, log_dir: str = None, log_file: str = "debug-mcp-any-openapi.log") -> logging.Logger:
    """
    Sets up logging for the application, including outputting CRITICAL and ERROR logs to stdout.

    Args:
        debug (bool): If True, set log level to DEBUG; otherwise, INFO.
        log_dir (str): Directory where log files will be stored. Ignored if `MCP_OPENAPI_LOGFILE_PATH` is set.
        log_file (str): Name of the log file. Ignored if `MCP_OPENAPI_LOGFILE_PATH` is set.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_path = os.getenv("MCP_OPENAPI_LOGFILE_PATH")
    if not log_path:
        if log_dir is None:
            log_dir = os.path.join(os.path.expanduser("~"), "mcp_logs")
        try:
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, log_file)
        except PermissionError as e:
            # Fallback to stdout logging if directory creation fails
            log_path = None
            print(f"[ERROR] Failed to create log directory: {e}", file=sys.stderr)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False  # Prevent log messages from propagating to the root logger

    # Remove all existing handlers to prevent accumulation
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handlers = []

    if log_path:
        try:
            file_handler = logging.FileHandler(log_path, mode="a")
            file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
            formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            print(f"[ERROR] Failed to create log file handler: {e}", file=sys.stderr)

    # Attempt to create StreamHandler for ERROR level logs (and above) to stdout
    try:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.ERROR) # Output ERROR and CRITICAL to stdout
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        stdout_handler.setFormatter(formatter)
        handlers.append(stdout_handler)
    except Exception as e:
        print(f"[ERROR] Failed to create stdout log handler: {e}", file=sys.stderr)

    # Add all handlers to the logger
    for handler in handlers:
        logger.addHandler(handler)

    if log_path:
        logger.debug(f"Logging initialized. Writing logs to {log_path}")
    else:
        logger.debug("Logging initialized. Logs will only appear in stdout.")
    return logger


def redact_api_key(key: str) -> str:
    """
    Redacts a generic API key or secret for safe logging output.

    Args:
        key (str): The API key to redact.

    Returns:
        str: The redacted API key or '<not set>' if the key is invalid.
    """
    if not key or len(key) <= 4:
        return "<not set>"
    return f"{key[:2]}{'*' * (len(key) - 4)}{key[-2:]}"


def normalize_tool_name(name: str) -> str:
    """
    Normalize tool names by converting to lowercase and replacing non-alphanumeric characters with underscores.

    Args:
        name (str): Original tool name.

    Returns:
        str: Normalized tool name. Returns 'unknown_tool' if the input is invalid.
    """
    logger = logging.getLogger(__name__)
    if not name or not isinstance(name, str):
        logger.warning(f"Invalid tool name input: {name}. Using default 'unknown_tool'.")
        return "unknown_tool"
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower() # Keep underscores, remove other non-alphanumeric
    normalized = re.sub(r"_+", "_", normalized) # Replace multiple underscores with single
    normalized = normalized.strip('_') # Remove leading/trailing underscores
    logger.debug(f"Normalized tool name from '{name}' to '{normalized}'")
    return normalized or "unknown_tool"


def fetch_openapi_spec(spec_url: str) -> dict:
    """
    Fetches and parses the OpenAPI specification from a URL.

    Args:
        spec_url (str): URL of the OpenAPI specification JSON file.

    Returns:
        dict: Parsed OpenAPI specification as a dictionary, or None if an error occurs.
    """
    logger = logging.getLogger(__name__)
    try:
        response = requests.get(spec_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        spec = response.json()
        logger.debug(f"Successfully fetched OpenAPI spec from {spec_url}")
        return spec
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching OpenAPI spec from {spec_url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response from {spec_url}: {e}")
        return None


# Set up logging before obtaining the logger
DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

# Log key environment variable values
logger.debug(f"OpenAPI Spec URL: {OPENAPI_SPEC_URL}") # Log spec URL
# Example of logging a redacted API key if you introduce API key auth later:
# OPENAPI_API_KEY = os.getenv("OPENAPI_API_KEY")
# logger.debug(f"OpenAPI API Key (redacted): {redact_api_key(OPENAPI_API_KEY)}")

logger.debug("utils.py initialized")

def map_verba_schema_to_tools(verba_schema: dict) -> list:
    """
    Map the schema returned by the /v1/verba endpoint to a list of MCP tools.

    Each class entry in the schema is expected to have a "class" field.
    This function creates an MCP tool for each class in the schema.
    """
    import json
    from mcp import types
    tools = []
    classes = verba_schema.get("classes", [])
    for entry in classes:
        cls = entry.get("class", "")
        if not cls:
            continue
        tool_name = normalize_tool_name(cls)
        # Insert tool prefix if the TOOL_NAME_PREFIX environment variable is set
        prefix = os.getenv("TOOL_NAME_PREFIX", "")
        if prefix:
            if not prefix.endswith("_"):
                prefix += "_"
            tool_name = prefix + tool_name
        description = f"Tool for class {cls}: " + json.dumps(entry)
        tool = types.Tool(name=tool_name, description=description, inputSchema={"type": "object"})
        tools.append(tool)
    return tools