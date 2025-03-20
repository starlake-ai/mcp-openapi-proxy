"""
Utility functions for mcp-openapi-proxy.
"""

import os
import sys
import json
import logging
import requests
import yaml
import jmespath
from typing import Dict, Optional, Tuple
from mcp import types

# Global logger - initialized in setup_logging
logger = None

def setup_logging(debug: bool = False) -> logging.Logger:
    """Set up logging with the specified debug level."""
    global logger
    logger = logging.getLogger("mcp_openapi_proxy")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.debug("Logging initialized, all output to stderr")
    return logger

def normalize_tool_name(raw_name: str) -> str:
    """Convert an HTTP method and path into a normalized tool name."""
    try:
        method, path = raw_name.split(" ", 1)
        method = method.lower()
        path_parts = [part for part in path.split("/") if part and not part.startswith("{")]
        name = "_".join([method] + path_parts)
        if "{" in path:  # If path has parameters, append '_id' to distinguish
            name += "_id"
        return name if name else "unknown_tool"
    except ValueError:
        logger.debug(f"Failed to normalize tool name: {raw_name}")
        return "unknown_tool"

def is_tool_whitelist_set() -> bool:
    """Check if TOOL_WHITELIST environment variable is set."""
    return bool(os.getenv("TOOL_WHITELIST"))

def is_tool_whitelisted(endpoint: str) -> bool:
    """Check if an endpoint is allowed based on TOOL_WHITELIST."""
    whitelist = os.getenv("TOOL_WHITELIST")
    logger.debug(f"Checking whitelist - endpoint: {endpoint}, TOOL_WHITELIST: {whitelist}")
    if not whitelist:
        logger.debug("No TOOL_WHITELIST set, allowing all endpoints.")
        return True
    whitelist_entries = [entry.strip() for entry in whitelist.split(",")]
    for entry in whitelist_entries:
        if entry in endpoint:
            logger.debug(f"Endpoint {endpoint} matches whitelist entry {entry}")
            return True
    logger.debug(f"Endpoint {endpoint} not in whitelist - skipping.")
    return False

def fetch_openapi_spec(url: str) -> Optional[Dict]:
    """Fetch and parse an OpenAPI specification from a URL."""
    logger.debug(f"OpenAPI Spec URL: {url}")
    try:
        if url.startswith("file://"):
            with open(url[7:], "r") as f:
                content = f.read()
        else:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            logger.debug(f"Fetched OpenAPI spec from {url}")
            content = response.text
        try:
            spec = json.loads(content)
            logger.debug(f"Parsed JSON OpenAPI spec from {url} (no suffix assumed JSON)")
        except json.JSONDecodeError:
            spec = yaml.safe_load(content)
            logger.debug(f"Parsed YAML OpenAPI spec from {url}")
        return spec
    except Exception as e:
        logger.error(f"Failed to fetch or parse OpenAPI spec from {url}: {e}", exc_info=True)
        return None

def build_base_url(spec: Dict) -> Optional[str]:
    """Construct the base URL from the OpenAPI spec or override."""
    override = os.getenv("SERVER_URL_OVERRIDE")
    if override:
        urls = [url.strip() for url in override.split(",")]
        for url in urls:
            if url.startswith("http://") or url.startswith("https://"):
                logger.debug(f"SERVER_URL_OVERRIDE set, using first valid URL: {url}")
                return url
        logger.error(f"No valid URLs found in SERVER_URL_OVERRIDE: {override}")
        return None
    if "servers" in spec and spec["servers"]:
        return spec["servers"][0]["url"]
    elif "host" in spec and "schemes" in spec:
        scheme = spec["schemes"][0] if spec["schemes"] else "https"
        return f"{scheme}://{spec['host']}{spec.get('basePath', '')}"
    logger.error("No servers or host/schemes defined in spec and no SERVER_URL_OVERRIDE.")
    return None

def get_tool_prefix() -> str:
    """Get the tool name prefix from TOOL_NAME_PREFIX environment variable."""
    return os.getenv("TOOL_NAME_PREFIX", "")

def handle_auth(operation: Dict) -> Dict[str, str]:
    """Handle authentication based on environment variables and operation security."""
    headers = {}
    api_key = os.getenv("API_KEY")
    auth_type = os.getenv("API_AUTH_TYPE", "Bearer").lower()
    if api_key:
        if auth_type == "bearer":
            logger.debug(f"Using API_KEY as Bearer: {api_key[:5]}...")
            headers["Authorization"] = f"Bearer {api_key}"
        elif auth_type == "basic":
            logger.debug("API_AUTH_TYPE is Basic, but Basic Auth not implemented yet.")
        elif auth_type == "api-key":
            key_name = os.getenv("API_AUTH_HEADER", "Authorization")
            headers[key_name] = api_key
            logger.debug(f"Using API_KEY as API-Key in header {key_name}: {api_key[:5]}...")
    return headers

def strip_parameters(parameters: Dict) -> Dict:
    """Strip specified parameters from the input based on STRIP_PARAM."""
    strip_param = os.getenv("STRIP_PARAM")
    if not strip_param or not isinstance(parameters, dict):
        return parameters
    logger.debug(f"Raw parameters before stripping: {parameters}")
    result = parameters.copy()
    if strip_param in result:
        del result[strip_param]
    logger.debug(f"Parameters after stripping: {result}")
    return result

def detect_response_type(response_text: str) -> Tuple[types.TextContent, str]:
    """Detect if the response is JSON or plain text."""
    try:
        json.loads(response_text)
        logger.debug("Response detected as JSON")
        return types.TextContent(type="text", text=f'{{"text": {json.dumps(response_text)}}}', id=None), "Response detected as JSON"
    except json.JSONDecodeError:
        logger.debug("Response detected as non-JSON text")
        return types.TextContent(type="text", text=response_text, id=None), "Response detected as non-JSON text"

def get_additional_headers() -> Dict[str, str]:
    """Parse additional headers from EXTRA_HEADERS environment variable."""
    headers = {}
    extra_headers = os.getenv("EXTRA_HEADERS")
    if extra_headers:
        for line in extra_headers.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()
    return headers
