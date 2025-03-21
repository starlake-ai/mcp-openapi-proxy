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
        # Take only the last meaningful part, skip prefixes like /api/v*
        path_parts = [part for part in path.split("/") if part and not part.startswith("{")]
        if not path_parts:
            return "unknown_tool"
        last_part = path_parts[-1].lower()  # Force lowercase
        name = f"{method}_{last_part}"
        if "{" in path:
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
    import re
    whitelist_entries = [entry.strip() for entry in whitelist.split(",")]
    for entry in whitelist_entries:
        if "{" in entry:
            # Build a regex pattern from the whitelist entry by replacing placeholders with a non-empty segment match ([^/]+)
            pattern = re.escape(entry)
            pattern = re.sub(r"\\\{[^\\\}]+\\\}", r"([^/]+)", pattern)
            pattern = "^" + pattern + "($|/.*)$"
            if re.match(pattern, endpoint):
                logger.debug(f"Endpoint {endpoint} matches whitelist entry {entry} using regex {pattern}")
                return True
        else:
            if endpoint.startswith(entry):
                logger.debug(f"Endpoint {endpoint} matches whitelist entry {entry}")
                return True
    logger.debug(f"Endpoint {endpoint} not in whitelist - skipping.")
    return False

def fetch_openapi_spec(url: str, retries: int = 3) -> Optional[Dict]:
    """Fetch and parse an OpenAPI specification from a URL with retries."""
    logger.debug(f"Fetching OpenAPI spec from URL: {url}")
    attempt = 0
    while attempt < retries:
        try:
            if url.startswith("file://"):
                with open(url[7:], "r") as f:
                    content = f.read()
            else:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                content = response.text
            logger.debug(f"Fetched content length: {len(content)} bytes")
            try:
                spec = json.loads(content)
                logger.debug(f"Parsed as JSON from {url}")
            except json.JSONDecodeError:
                try:
                    spec = yaml.safe_load(content)
                    logger.debug(f"Parsed as YAML from {url}")
                except yaml.YAMLError as ye:
                    logger.error(f"YAML parsing failed: {ye}. Raw content: {content[:500]}...")
                    return None
            return spec
        except requests.RequestException as e:
            attempt += 1
            logger.warning(f"Fetch attempt {attempt}/{retries} failed: {e}")
            if attempt == retries:
                logger.error(f"Failed to fetch spec from {url} after {retries} attempts: {e}")
                return None
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
    """Determine response type based on JSON validity.
    If response_text is valid JSON, return a wrapped JSON string;
    otherwise, return the plain text.
    """
    try:
        json.loads(response_text)
        wrapped_text = json.dumps({"text": response_text})
        return types.TextContent(type="text", text=wrapped_text, id=None), "JSON response"
    except json.JSONDecodeError:
        return types.TextContent(type="text", text=response_text.strip(), id=None), "non-JSON text"

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
