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
import yaml
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

OPENAPI_SPEC_URL = os.getenv("OPENAPI_SPEC_URL")

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
            log_path = None
            print(f"[ERROR] Failed to create log directory: {e}", file=sys.stderr)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
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

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

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
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    normalized = re.sub(r"_+", "_", normalized)
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
    Checks if an endpoint is in the TOOL_WHITELIST, supporting exact matches, prefixes, and path parameters.

    Args:
        endpoint (str): The API endpoint path to check.

    Returns:
        bool: True if whitelisted or no whitelist set, False otherwise.
    """
    whitelist = os.getenv("TOOL_WHITELIST", "")
    logger.debug(f"Checking whitelist - endpoint: {endpoint}, TOOL_WHITELIST: {whitelist}")
    if not whitelist:
        logger.debug("No TOOL_WHITELIST set, allowing all endpoints.")
        return True
    
    whitelist_items = [item.strip() for item in whitelist.split(",") if item.strip()]
    
    # Direct match
    if endpoint in whitelist_items:
        logger.debug(f"Direct match found for {endpoint} in whitelist")
        return True
    
    # Prefix match (e.g., /tasks matches /tasks/123)
    for item in whitelist_items:
        if not '{' in item and endpoint.startswith(item):
            logger.debug(f"Prefix match found: {item} starts {endpoint}")
            return True
    
    # Path parameter match (e.g., /sessions/{sessionId} matches /sessions/abc123 or /sessions/abc123/items)
    for item in whitelist_items:
        if '{' in item and '}' in item:
            pattern = re.escape(item)
            pattern = pattern.replace(r"\{", "{").replace(r"\}", "}")
            pattern = re.sub(r"\{[^}]+\}", r"[^/]+", pattern)
            pattern = f"^{pattern}(/.*)?$"  # Allow optional trailing segments
            if re.match(pattern, endpoint):
                logger.debug(f"Pattern match found for {endpoint} using {item}")
                return True
                
    logger.debug(f"No whitelist match found for {endpoint}")
    return False

def fetch_openapi_spec(spec_url: str) -> dict:
    """
    Fetches and parses an OpenAPI specification from a URL or local file, supporting JSON and YAML.

    Args:
        spec_url (str): The URL or file path (e.g., file:///path/to/spec.json) of the OpenAPI spec.

    Returns:
        dict: The parsed OpenAPI specification, or None if an error occurs.
    """
    logger = logging.getLogger(__name__)
    try:
        if spec_url.startswith("file://"):
            spec_path = spec_url.replace("file://", "")
            with open(spec_path, 'r') as f:
                content = f.read()
            logger.debug(f"Read local OpenAPI spec from {spec_path}")
        else:
            response = requests.get(spec_url)
            response.raise_for_status()
            content = response.text
            logger.debug(f"Fetched OpenAPI spec from {spec_url}")

        if spec_url.endswith(('.yaml', '.yml')):
            spec = yaml.safe_load(content)
            logger.debug(f"Parsed YAML OpenAPI spec from {spec_url}")
        else:
            spec = json.loads(content)
            logger.debug(f"Parsed JSON OpenAPI spec from {spec_url}")
        return spec
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching OpenAPI spec from {spec_url}: {e}")
        return None
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error(f"Error parsing OpenAPI spec from {spec_url}: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(f"Local file not found for OpenAPI spec at {spec_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with OpenAPI spec from {spec_url}: {e}")
        return None

def get_auth_type(spec: dict) -> str:
    """
    Determines the authentication type from the OpenAPI spec's securityDefinitions.

    Args:
        spec (dict): The OpenAPI specification.

    Returns:
        str: 'Api-Key' if apiKey auth is defined in Authorization header, 'Bearer' otherwise.
    """
    security_defs = spec.get("securityDefinitions", {})
    for name, definition in security_defs.items():
        if definition.get("type") == "apiKey" and definition.get("in") == "header" and definition.get("name") == "Authorization":
            logger.debug(f"Detected ApiKeyAuth in spec: {name}")
            return "Api-Key"
    logger.debug("No ApiKeyAuth found in spec, defaulting to Bearer")
    return "Bearer"

def map_schema_to_tools(schema: dict) -> list:
    """
    Maps a given schema to a list of MCP tools.

    Args:
        schema (dict): The schema containing a list of classes.

    Returns:
        list: A list of tool objects configured from the schema.
    """
    from mcp import types
    tools = []
    classes = schema.get("classes", [])
    for entry in classes:
        cls = entry.get("class", "")
        if not cls:
            continue
        tool_name = normalize_tool_name(cls)
        prefix = os.getenv("TOOL_NAME_PREFIX", "")
        if prefix:
            if not prefix.endswith("_"):
                prefix += "_"
            tool_name = prefix + tool_name
        description = f"Tool for class {cls}: " + json.dumps(entry)
        tool = types.Tool(name=tool_name, description=description, inputSchema={"type": "object"})
        tools.append(tool)
    return tools
