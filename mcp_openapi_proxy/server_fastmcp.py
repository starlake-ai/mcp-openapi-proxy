"""
Provides the FastMCP server logic for mcp-openapi-proxy.

This server exposes a pre-defined set of functions based on an OpenAPI specification.
Configuration is controlled via environment variables:

- OPENAPI_SPEC_URL: URL pointing to the OpenAPI JSON specification or local file.
- OPENAPI_SIMPLE_MODE_FUNCTION_CONFIG: JSON configuration for available functions.
- DEBUG: Enables debug logging when set to true.
- TOOL_WHITELIST: Comma-separated list of allowed endpoint paths.
- SERVER_URL_OVERRIDE: (Optional) Overrides the base URL from the OpenAPI spec.
- API_AUTH_BEARER: (Optional) Token for endpoints requiring authentication.
- API_AUTH_TYPE: (Optional) 'Bearer' or 'Api-Key' - defaults to 'Bearer'.
"""

import os
import sys
import json
import requests

from mcp.server.fastmcp import FastMCP
from mcp_openapi_proxy.utils import setup_logging, fetch_openapi_spec

OPENAPI_SPEC_URL = os.getenv("OPENAPI_SPEC_URL")
FUNCTION_CONFIG_JSON = os.getenv("OPENAPI_SIMPLE_MODE_FUNCTION_CONFIG")
DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
API_AUTH_TYPE = os.getenv("API_AUTH_TYPE", "Bearer")

logger = setup_logging(debug=DEBUG)
logger.debug(f"OpenAPI Spec URL: {OPENAPI_SPEC_URL}")
logger.debug(f"Function Config JSON: {FUNCTION_CONFIG_JSON}")
logger.debug(f"API_AUTH_TYPE: {API_AUTH_TYPE}")

mcp = FastMCP("OpenApiProxy-Fast")

def is_tool_whitelisted(endpoint: str) -> bool:
    """
    Checks if an endpoint is in the TOOL_WHITELIST.

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
    is_allowed = endpoint in whitelist_items
    logger.debug(f"Whitelist check result for {endpoint}: {is_allowed}")
    return is_allowed

@mcp.tool()
def list_functions() -> str:
    """
    Lists available API functions defined in the OpenAPI specification.

    Returns:
        A JSON-encoded string detailing available functions, or an error message if configuration is missing.
    """
    logger.debug("Executing list_functions tool.")
    if not OPENAPI_SPEC_URL:
        error_msg = "OPENAPI_SPEC_URL is not configured."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    spec = fetch_openapi_spec(OPENAPI_SPEC_URL)
    if not spec:
        error_msg = "Failed to fetch or parse the OpenAPI specification."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    logger.debug(f"Spec paths available: {list(spec.get('paths', {}).keys())}")
    functions = []
    for path, path_item in spec.get("paths", {}).items():
        logger.debug(f"Processing path: {path}")
        if not is_tool_whitelisted(path):
            logger.debug(f"Path {path} not in whitelist - skipping.")
            continue
        for method, operation in path_item.items():
            logger.debug(f"Found method: {method}")
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                logger.debug(f"Method {method} not supported - skipping.")
                continue
            function_name = f"{method.upper()} {path}"
            function_description = operation.get("summary", operation.get("description", "No description provided."))
            logger.debug(f"Registering function: {function_name} - {function_description}")
            functions.append({
                "name": function_name,
                "description": function_description,
                "path": path,
                "method": method.upper(),
                "operationId": operation.get("operationId")
            })
    logger.info(f"Discovered {len(functions)} functions from the OpenAPI specification.")
    return json.dumps(functions, indent=2)

@mcp.tool()
def call_function(*, function_name: str, parameters: dict = None) -> str:
    """
    Calls a specified API function (endpoint) defined in the OpenAPI specification with given parameters.

    Args:
        function_name (str): The name of the API function to call (e.g., "GET /pets").
        parameters (dict, optional): Parameters for the API call (query parameters, request body, etc.).

    Returns:
        str: The raw API response as a JSON-encoded string, or an error message.
    """
    logger.debug(f"call_function invoked with function_name='{function_name}' and parameters={parameters}")
    if not OPENAPI_SPEC_URL:
        error_msg = "OPENAPI_SPEC_URL is not configured."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    spec = fetch_openapi_spec(OPENAPI_SPEC_URL)
    if not spec:
        error_msg = "Failed to fetch or parse the OpenAPI specification."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    function_def = None
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue
            current_function_name = f"{method.upper()} {path}"
            if current_function_name == function_name:
                function_def = {
                    "path": path,
                    "method": method.upper(),
                    "operation": operation
                }
                logger.debug(f"Matched function definition for '{function_name}'.")
                break
        if function_def:
            break

    if not function_def:
        error_msg = f"Function '{function_name}' not found in the OpenAPI specification."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    if not is_tool_whitelisted(function_def["path"]):
        error_msg = f"Access to function '{function_name}' is not allowed."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    # Determine base URL, respecting spec's basePath if SERVER_URL_OVERRIDE doesn't include it
    SERVER_URL_OVERRIDE = os.getenv("SERVER_URL_OVERRIDE")
    if SERVER_URL_OVERRIDE:
        base_url = SERVER_URL_OVERRIDE.strip()
        logger.debug(f"Using SERVER_URL_OVERRIDE: {base_url}")
    else:
        servers = spec.get("servers", [])
        if servers:
            base_url = servers[0].get("url", "")
            logger.debug(f"Using base_url from OpenAPI 3.0 servers: {base_url}")
        else:
            schemes = spec.get("schemes", ["https"])
            base_path = spec.get("basePath", "")
            base_url = f"{schemes[0]}://example.com{base_path}"
            logger.debug(f"Using Swagger 2.0 fallback base_url: {base_url}")
        if not base_url:
            logger.warning("No valid base URL found in spec or override; using empty string.")
            base_url = ""

    # Append basePath from spec if not already in SERVER_URL_OVERRIDE
    base_path = spec.get("basePath", "")
    if base_path and not base_url.endswith(base_path.rstrip("/")):
        base_url = base_url.rstrip("/") + "/" + base_path.lstrip("/")
    api_url = base_url.rstrip("/") + function_def["path"]
    logger.debug(f"Constructed API URL: {api_url}")

    request_params = {}
    request_body = None
    if parameters:
        if function_def["method"] == "GET":
            request_params = parameters
        else:
            request_body = parameters
    logger.debug(f"Request params: {request_params}, Request body: {request_body}")

    headers = {}
    api_auth = os.getenv("API_AUTH_BEARER")
    if api_auth:
        headers["Authorization"] = f"{API_AUTH_TYPE} {api_auth}"

    try:
        response = requests.request(
            method=function_def["method"],
            url=api_url,
            headers=headers,
            params=request_params if function_def["method"] == "GET" else None,
            json=request_body if function_def["method"] != "GET" and request_body else None
        )
        response.raise_for_status()
        logger.debug(f"API response received: {response.text}")
        return response.text
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {e}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg})

def run_simple_server():
    """
    Runs the FastMCP version of the Any OpenAPI server.

    This function verifies the necessary configurations (e.g., OPENAPI_SPEC_URL) and starts the MCP server using stdio.
    """
    if not OPENAPI_SPEC_URL:
        logger.error("OPENAPI_SPEC_URL environment variable is required for FastMCP mode.")
        sys.exit(1)
    try:
        logger.debug("Starting MCP server (FastMCP version)...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error("Unhandled exception in MCP server (FastMCP).", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_simple_server()
