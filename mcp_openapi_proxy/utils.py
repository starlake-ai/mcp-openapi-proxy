"""
Utility functions for mcp_openapi_proxy, including logging setup,
OpenAPI fetching, name normalization, whitelist filtering, auth handling,
and response type detection.
"""

import os
import sys
import logging
import requests
import re
import json
import yaml
import jmespath
from urllib.parse import urlparse
from dotenv import load_dotenv
from mcp import types

load_dotenv()

OPENAPI_SPEC_URL = os.getenv("OPENAPI_SPEC_URL")

def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configures logging for the application, directing all output to stderr.

    Args:
        debug (bool): If True, sets log level to DEBUG; otherwise, INFO.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    if debug:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)
        logger.debug("Logging initialized, all output to stderr")
    else:
        logger.addHandler(logging.NullHandler())
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
    """
    Normalizes tool names into a clean function name without parameters.

    Args:
        name (str): Raw method and path, e.g., 'GET /sessions/{sessionId}/messages/{messageUUID}'.

    Returns:
        str: Normalized tool name without special characters.
    """
    if not name or not isinstance(name, str):
        logger.warning(f"Invalid tool name input: {name}. Defaulting to 'unknown_tool'.")
        return "unknown_tool"
    parts = name.strip().split(" ", 1)
    if len(parts) != 2:
        if "." in name:
            parts = name.split(".", 1)
            method, path = parts[0].lower(), parts[1].replace(".", "_")
        else:
            logger.warning(f"Malformed tool name '{name}', expected 'METHOD /path'. Defaulting to 'unknown_tool'.")
            return "unknown_tool"
    else:
        method, path = parts
        method = method.lower()
    path_parts = [p for p in path.split("/") if p and p not in ("api", "v2")]
    if not path_parts:
        logger.warning(f"No valid path segments in '{path}'. Using '{method}_unknown'.")
        return f"{method}_unknown"
    func_name = method
    for part in path_parts:
        if "{" in part and "}" in part:
            continue
        func_name += f"_{part.replace('.', '_')}"
    func_name = re.sub(r"[^a-zA-Z0-9_-]", "_", func_name)
    func_name = re.sub(r"_+", "_", func_name).strip("_").lower()
    if len(func_name) > 64:
        func_name = func_name[:64]
    logger.debug(f"Normalized tool name from '{name}' to '{func_name}'")
    return func_name or "unknown_tool"

def get_tool_prefix() -> str:
    """Retrieves tool name prefix from environment, ensuring it ends with an underscore."""
    prefix = os.getenv("TOOL_NAME_PREFIX", "")
    if prefix and not prefix.endswith("_"):
        prefix += "_"
    return prefix

def is_tool_whitelisted(endpoint: str) -> bool:
    """
    Checks if an endpoint matches any partial path in TOOL_WHITELIST.

    Args:
        endpoint (str): The endpoint path from the OpenAPI spec.

    Returns:
        bool: True if the endpoint matches any whitelist item, False otherwise.
    """
    whitelist = os.getenv("TOOL_WHITELIST", "")
    logger.debug(f"Checking whitelist - endpoint: {endpoint}, TOOL_WHITELIST: {whitelist}")
    if not whitelist:
        logger.debug("No TOOL_WHITELIST set, allowing all endpoints.")
        return True
    whitelist_items = [item.strip() for item in whitelist.split(",") if item.strip()]
    if not whitelist_items:
        logger.debug("TOOL_WHITELIST is empty after splitting, allowing all endpoints.")
        return True
    endpoint_parts = [p for p in endpoint.split("/") if p]
    for item in whitelist_items:
        if endpoint == item:
            logger.debug(f"Exact match found for {endpoint} in whitelist")
            return True
        if '{' not in item and endpoint.startswith(item):
            logger.debug(f"Prefix match found: {item} starts {endpoint}")
            return True
        item_parts = [p for p in item.split("/") if p]
        if len(item_parts) <= len(endpoint_parts):
            match = True
            for i, item_part in enumerate(item_parts):
                if i >= len(endpoint_parts):
                    match = False
                    break
                endpoint_part = endpoint_parts[i]
                if "{" in item_part and "}" in item_part:
                    continue
                elif item_part != endpoint_part:
                    match = False
                    break
            if match:
                logger.debug(f"Partial path match found for {endpoint} using {item}")
                return True
    logger.debug(f"No whitelist match found for {endpoint}")
    return False

def fetch_openapi_spec(spec_url: str) -> dict:
    """Fetches and parses OpenAPI specification from a URL or file."""
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
    except (requests.exceptions.RequestException, FileNotFoundError) as e:
        logger.error(f"Error fetching OpenAPI spec from {spec_url}: {e}")
        return None
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error(f"Error parsing OpenAPI spec from {spec_url}: {e}")
        return None

def get_auth_headers(spec: dict, api_key_env: str = "API_KEY") -> dict:
    """
    Constructs authorization headers based on spec and environment variables.

    Args:
        spec (dict): OpenAPI specification.
        api_key_env (str): Environment variable name for the API key (default: "API_KEY").

    Returns:
        dict: Headers dictionary with Authorization set appropriately.
    """
    headers = {}
    auth_token = os.getenv(api_key_env)
    if not auth_token:
        logger.debug(f"No {api_key_env} set, skipping auth headers.")
        return headers
    auth_type_override = os.getenv("API_AUTH_TYPE")
    if auth_type_override:
        headers["Authorization"] = f"{auth_type_override} {auth_token}"
        logger.debug(f"Using API_AUTH_TYPE override: Authorization: {auth_type_override} {redact_api_key(auth_token)}")
        return headers
    security_defs = spec.get('securityDefinitions', {})
    for name, definition in security_defs.items():
        if definition.get('type') == 'apiKey' and definition.get('in') == 'header' and definition.get('name') == 'Authorization':
            desc = definition.get('description', '')
            match = re.search(r'(\w+(?:-\w+)*)\s+<token>', desc)
            if match:
                prefix = match.group(1)
                headers["Authorization"] = f"{prefix} {auth_token}"
                logger.debug(f"Using apiKey with prefix from spec description: Authorization: {prefix} {redact_api_key(auth_token)}")
            else:
                headers["Authorization"] = auth_token
                logger.debug(f"Using raw apiKey auth from spec: Authorization: {redact_api_key(auth_token)}")
            return headers
        elif definition.get('type') == 'oauth2':
            headers["Authorization"] = f"Bearer {auth_token}"
            logger.debug(f"Using Bearer auth from spec: Authorization: Bearer {redact_api_key(auth_token)}")
            return headers
    headers["Authorization"] = auth_token
    logger.warning(f"No clear auth type in spec, using raw API key: Authorization: {redact_api_key(auth_token)}")
    return headers

def handle_custom_auth(operation: dict, parameters: dict = None) -> dict:
    """
    Applies custom authentication mapping using API_KEY_JMESPATH if provided, overwriting existing keys.

    Args:
        operation (dict): The OpenAPI operation object for the endpoint.
        parameters (dict, optional): Existing parameters or arguments to modify.

    Returns:
        dict: Updated parameters with API_KEY mapped according to API_KEY_JMESPATH, overwriting conflicts.
    """
    if parameters is None:
        parameters = {}
    
    api_key = os.getenv("API_KEY")
    jmespath_expr = os.getenv("API_KEY_JMESPATH")
    
    if not api_key or not jmespath_expr:
        logger.debug("No API_KEY or API_KEY_JMESPATH set, skipping custom auth handling.")
        return parameters

    # Structure to apply JMESPath: separate query params and body
    request_data = {"query": {}, "body": {}}
    if parameters:
        # Assume GET params go to query, others to body (simplified heuristic)
        for key, value in parameters.items():
            if operation.get("method", "GET").upper() == "GET":
                request_data["query"][key] = value
            else:
                request_data["body"][key] = value

    try:
        # Compile JMESPath expression and set the API key, overwriting existing
        expr = jmespath.compile(jmespath_expr)
        updated_data = expr.search(request_data, options=jmespath.Options(dict_cls=dict))
        if updated_data is None:
            # If path doesn't exist, create it
            parts = jmespath_expr.split('.')
            current = request_data
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = api_key  # Overwrite here
                else:
                    current.setdefault(part, {})
                    current = current[part]
        else:
            # Overwrite existing value at the JMESPath location
            parts = jmespath_expr.split('.')
            current = request_data
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = api_key  # Force overwrite
                else:
                    current = current.setdefault(part, {})
        logger.debug(f"Applied API_KEY to {jmespath_expr}, overwriting any existing: {redact_api_key(api_key)}")
    except Exception as e:
        logger.error(f"Failed to apply API_KEY_JMESPATH '{jmespath_expr}': {e}")
        return parameters

    # Flatten back to parameters, overwriting original params
    if operation.get("method", "GET").upper() == "GET":
        parameters = {**parameters, **request_data["query"]}
    else:
        parameters = {**parameters, **request_data["body"]}
    
    return parameters

def map_schema_to_tools(schema: dict) -> list:
    """Maps a schema to a list of MCP tools."""
    tools = []
    classes = schema.get("classes", [])
    for entry in classes:
        cls = entry.get("class", "")
        if not cls:
            continue
        tool_name = normalize_tool_name(cls)
        prefix = get_tool_prefix()
        if prefix:
            tool_name = prefix + tool_name
        description = f"Tool for class {cls}: " + json.dumps(entry)
        tool = types.Tool(name=tool_name, description=description, inputSchema={"type": "object"})
        tools.append(tool)
    return tools

def detect_response_type(response_text: str) -> tuple[types.TextContent, str]:
    """
    Detects the response type (JSON or text) and returns the appropriate MCP content object.

    Args:
        response_text (str): The raw response text from the HTTP request.

    Returns:
        Tuple: (content object, log message)
    """
    try:
        json_data = json.loads(response_text)
        structured_text = {"text": response_text}
        content = types.TextContent(type="text", text=json.dumps(structured_text))
        log_message = "Detected JSON response, wrapped in structured text format"
    except json.JSONDecodeError:
        content = types.TextContent(type="text", text=response_text)
        log_message = "Detected non-JSON response, falling back to text"
    return content, log_message

def build_base_url(spec: dict) -> str:
    """
    Constructs the base URL for API requests, prioritizing SERVER_URL_OVERRIDE.

    Args:
        spec (dict): OpenAPI specification containing servers or host information.

    Returns:
        str: The constructed base URL, or empty string if not determinable.
    """
    override = os.getenv("SERVER_URL_OVERRIDE", "").strip()
    if override:
        urls = override.split()
        for url in urls:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                logger.debug(f"SERVER_URL_OVERRIDE set, using first valid URL: {url}")
                return url.rstrip('/')
        logger.error(f"No valid URLs found in SERVER_URL_OVERRIDE: {override}")
    if 'servers' in spec and spec['servers']:
        default_server = spec['servers'][0].get('url', '').rstrip('/')
        if "{tenant}" in default_server or "your-domain" in default_server:
            logger.warning(f"Placeholder detected in spec server URL: {default_server}. Consider setting SERVER_URL_OVERRIDE.")
            return default_server
        logger.debug(f"Using OpenAPI 3.0 servers base URL: {default_server}")
        return default_server
    if 'host' in spec:
        scheme = spec.get('schemes', ['https'])[0]
        host = spec['host'].strip()
        base_url = f"{scheme}://{host}"
        base_path = spec.get('basePath', '').strip('/')
        if base_path:
            base_url += f"/{base_path}"
        logger.debug(f"Using Swagger 2.0 host/basePath base URL: {base_url}")
        return base_url.rstrip('/')
    logger.critical("No servers or host defined in OpenAPI spec, and no SERVER_URL_OVERRIDE set.")
    return ""
