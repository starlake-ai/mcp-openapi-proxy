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

def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Sets up logging for the application, ALL output to stderr like a proper cunt.

    Args:
        debug (bool): If True, sets log level to DEBUG; otherwise, INFO.

    Returns:
        logging.Logger: Configured logger instance, screamin’ to stderr.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    
    # Clear any old handlers, ya wanker
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Stderr handler, all levels, no bullshit
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)
    
    logger.debug("Logging initialized, all shit goin’ to stderr like it fuckin’ should!")
    return logger

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

logger.debug(f"OpenAPI Spec URL: {OPENAPI_SPEC_URL}")
logger.debug("utils.py initialized")

def redact_api_key(key: str) -> str:
    """Redacts an API key for secure logging."""
    if not key or len(key) <= 4:
        return "<not set>"
    return f"{key[:2]}{'*' * (len(key) - 4)}{key[-2:]}"

def normalize_tool_name(name: str) -> str:
    """Normalizes tool names to lowercase, replaces non-alphanum with underscores."""
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
    """Gets tool name prefix from env, ensures it ends with an underscore."""
    prefix = os.getenv("TOOL_NAME_PREFIX", "")
    if prefix and not prefix.endswith("_"):
        prefix += "_"
    return prefix

def is_tool_whitelisted(endpoint: str) -> bool:
    """Checks if an endpoint’s in TOOL_WHITELIST, supports exact, prefix, and path params."""
    whitelist = os.getenv("TOOL_WHITELIST", "")
    logger.debug(f"Checking whitelist - endpoint: {endpoint}, TOOL_WHITELIST: {whitelist}")
    if not whitelist:
        logger.debug("No TOOL_WHITELIST set, allowing all endpoints.")
        return True

    whitelist_items = [item.strip() for item in whitelist.split(",") if item.strip()]
    if endpoint in whitelist_items:
        logger.debug(f"Direct match found for {endpoint} in whitelist")
        return True

    for item in whitelist_items:
        if not '{' in item and endpoint.startswith(item):
            logger.debug(f"Prefix match found: {item} starts {endpoint}")
            return True

    for item in whitelist_items:
        if '{' in item and '}' in item:
            pattern = re.escape(item)
            pattern = pattern.replace(r"\{", "{").replace(r"\}", "}")
            pattern = re.sub(r"\{[^}]+\}", r"[^/]+", pattern)
            pattern = f"^{pattern}(/.*)?$"
            if re.match(pattern, endpoint):
                logger.debug(f"Pattern match found for {endpoint} using {item}")
                return True

    logger.debug(f"No whitelist match found for {endpoint}")
    return False

def fetch_openapi_spec(spec_url: str) -> dict:
    """Fetches and parses OpenAPI spec from URL or file, supports JSON/YAML."""
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
    """Determines auth type from OpenAPI spec’s securityDefinitions."""
    security_defs = spec.get("securityDefinitions", {})
    for name, definition in security_defs.items():
        if definition.get("type") == "apiKey" and definition.get("in") == "header" and definition.get("name") == "Authorization":
            logger.debug(f"Detected ApiKeyAuth in spec: {name}")
            return "Api-Key"
    logger.debug("No ApiKeyAuth found in spec, defaulting to Bearer")
    return "Bearer"

def map_schema_to_tools(schema: dict) -> list:
    """Maps a schema to a list of MCP tools."""
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
