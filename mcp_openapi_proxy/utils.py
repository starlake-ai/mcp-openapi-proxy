"""
Utility functions for mcp_openapi_proxy, including logging setup,
OpenAPI fetching, name normalization, and whitelist filtering for tools.
"""

import os
import sys
import logging
import requests
import re
import json
import yaml  # Added for YAML parsing, ya bloody genius
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# OpenAPI related configuration (extend as needed)
OPENAPI_SPEC_URL = os.getenv("OPENAPI_SPEC_URL")  # Example - used to specify the OpenAPI spec URL

def setup_logging(debug: bool = False, log_dir: str = None, log_file: str = "debug-mcp-any-openapi.log") -> logging.Logger:
    """
    Sets up logging for the application, including outputting CRITICAL and ERROR logs to stdout.

    Args:
        debug (bool): If True, sets log level to DEBUG; otherwise, INFO.
        log_dir (str): Directory where log files will be stored. Ignored if OPENAPI_LOGFILE_PATH is set.
        log_file (str): Name of the log file. Ignored if OPENAPI_LOGFILE_PATH is set.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_path = os.getenv("OPENAPI_LOGFILE_PATH")
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
    # Create StreamHandler for ERROR level logs (and above) to stdout
    try:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        stdout_handler.setFormatter(formatter)
        handlers.append(stdout_handler)
    except Exception as e:
        print(f"[ERROR] Failed to create stdout log handler: {e}", file=sys.stderr)
    for handler in handlers:
        logger.addHandler(handler)
    if log_path:
        logger.debug(f"Logging initialized. Writing logs to {log_path}")
    else:
        logger.debug("Logging initialized. Logs will only appear in stdout.")
    return logger

# Set up logging immediately
DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

# Log key configuration values
logger.debug(f"OpenAPI Spec URL: {OPENAPI_SPEC_URL}")
logger.debug("utils.py initialized")

def redact_api_key(key: str) -> str:
    """
    Redacts an API key for secure logging.

    Args:
        key (str): The API key or secret.

    Returns:
        str: The redacted API key, or '<not set>' if key is invalid.
    """
    if not key or len(key) <= 4:
        return "<not set>"
    return f"{key[:2]}{'*' * (len(key) - 4)}{key[-2:]}"

def normalize_tool_name(name: str) -> str:
    """
    Normalizes tool names by converting to lowercase and replacing non-alphanumeric characters with underscores.

    Args:
        name (str): The original tool name.

    Returns:
        str: A normalized tool name. Returns 'unknown_tool' if input is invalid.
    """
    logger = logging.getLogger(__name__)
    if not name or not isinstance(name, str):
        logger.warning(f"Invalid tool name input: {name}. Using default 'unknown_tool'.")
        return "unknown_tool"
    # Replace non-alphanumeric characters (except underscores) with underscores
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    normalized = re.sub(r"_+", "_", normalized)  # Replace multiple underscores with a single underscore
    normalized = normalized.strip('_')
    logger.debug(f"Normalized tool name from '{name}' to '{normalized}'")
    return normalized or "unknown_tool"

def get_tool_prefix() -> str:
    """
    Obtains the tool name prefix from the environment variable, ensuring it ends with an underscore.

    Returns:
        str: The tool name prefix.
    """
    prefix = os.getenv("TOOL_NAME_PREFIX", "")
    if prefix and not prefix.endswith("_"):
        prefix += "_"
    return prefix

def is_tool_whitelisted(endpoint: str) -> bool:
    """
    Determines whether a given endpoint is allowed based on the TOOL_WHITELIST environment variable.

    The whitelist can specify fixed prefixes or use placeholders (e.g., {collection_name})
    which are translated into regex patterns matching one or more alphanumeric characters.

    Args:
        endpoint (str): The API endpoint path to check.

    Returns:
        bool: True if the endpoint is whitelisted, False otherwise.
    """
    import re
    whitelist = os.getenv("TOOL_WHITELIST", "")
    logger.debug(f"Checking whitelist for endpoint: {endpoint}, TOOL_WHITELIST: {whitelist}")
    if not whitelist:
        logger.debug("No TOOL_WHITELIST set, allowing all endpoints.")
        return True
    items = [item.strip() for item in whitelist.split(",") if item.strip()]
    for item in items:
        logger.debug(f"Comparing against whitelist item: {item}")
        if "{" in item and "}" in item:
            # Convert whitelist pattern with placeholders to regex
            pattern = re.escape(item)
            pattern = pattern.replace(r"\{", "{").replace(r"\}", "}")
            pattern = re.sub(r"\{[^}]+\}", r"[A-Za-z0-9_-]+", pattern)  # Placeholders match alphanum, _, -
            pattern = "^" + pattern  # Start match, no $ to allow trailing, ya cunt
            if re.match(pattern, endpoint):
                logger.debug(f"Matched regex pattern: {pattern} for {endpoint}")
                return True
        elif endpoint.startswith(item):  # Simple prefix match, ya wanker
            logger.debug(f"Prefix match found: {item} starts {endpoint}")
            return True
    logger.debug(f"Endpoint {endpoint} not whitelisted.")
    return False

def fetch_openapi_spec(spec_url: str) -> dict:
    """
    Fetches and parses an OpenAPI specification from the given URL, supporting both JSON and YAML.

    Args:
        spec_url (str): The URL of the OpenAPI specification (JSON or YAML format).

    Returns:
        dict: The parsed OpenAPI specification, or None if an error occurs.
    """
    logger = logging.getLogger(__name__)
    try:
        response = requests.get(spec_url)
        response.raise_for_status()  # Raises HTTPError for bad responses
        content_type = response.headers.get('Content-Type', '').lower()
        content = response.text
        
        # Check if it's YAML or JSON based on content-type or file extension
        if 'yaml' in content_type or spec_url.endswith(('.yaml', '.yml')):
            spec = yaml.safe_load(content)  # Parse YAML like a bloody pro
            logger.debug(f"Successfully parsed YAML OpenAPI spec from {spec_url}")
        else:
            spec = json.loads(content)  # Parse JSON like the old days
            logger.debug(f"Successfully parsed JSON OpenAPI spec from {spec_url}")
        return spec
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching OpenAPI spec from {spec_url}: {e}")
        return None
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error(f"Error parsing response from {spec_url}: {e}")
        return None

def map_schema_to_tools(schema: dict) -> list:
    """
    Maps a given schema to a list of MCP tools.

    Each entry in the schema is expected to have a "class" field, and a tool is created based on it.

    Args:
        schema (dict): The schema containing a list of classes.

    Returns:
        list: A list of tool objects configured from the schema.
    """
    import json
    from mcp import types
    tools = []
    classes = schema.get("classes", [])
    for entry in classes:
        cls = entry.get("class", "")
        if not cls:
            continue
        tool_name = normalize_tool_name(cls)
        # Prepend tool prefix if configured via environment variable
        prefix = os.getenv("TOOL_NAME_PREFIX", "")
        if prefix:
            if not prefix.endswith("_"):
                prefix += "_"
            tool_name = prefix + tool_name
        description = f"Tool for class {cls}: " + json.dumps(entry)
        tool = types.Tool(name=tool_name, description=description, inputSchema={"type": "object"})
        tools.append(tool)
    return tools
