"""
Provides the FastMCP server logic for mcp-openapi-proxy.

This server exposes a pre-defined set of functions based on an OpenAPI specification.
Configuration is controlled via environment variables:

- OPENAPI_SPEC_URL: URL pointing to the OpenAPI JSON specification.
- OPENAPI_SIMPLE_MODE_FUNCTION_CONFIG: JSON configuration for available functions.
- DEBUG: Enables debug logging when set to true.
- TOOL_WHITELIST: Comma-separated list of allowed endpoint prefixes; supports placeholders (e.g. {name}) which
  are transformed into regex patterns matching one or more alphanumeric characters.
- SERVER_URL_OVERRIDE: (Optional) Overrides the base URL from the OpenAPI spec.
- API_AUTH_BEARER: (Optional) Token for endpoints requiring authentication.
- API_AUTH_TYPE: (Optional) 'Bearer' or 'Api-Key' - defaults to 'Bearer', ya farkin' cunt!

The server supports dynamic parsing of the OpenAPI document, filtering of endpoints based on the whitelist,
and executes API calls with the appropriate request parameters.
"""

import os
import sys
import json
import requests  # For external API calls

from mcp.server.fastmcp import FastMCP
from mcp_openapi_proxy.utils import setup_logging, fetch_openapi_spec, is_tool_whitelisted

# Retrieve configuration from environment variables
OPENAPI_SPEC_URL = os.getenv("OPENAPI_SPEC_URL")
FUNCTION_CONFIG_JSON = os.getenv("OPENAPI_SIMPLE_MODE_FUNCTION_CONFIG")  # JSON configuration for functions (if provided)
DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
API_AUTH_TYPE = os.getenv("API_AUTH_TYPE", "Bearer")  # Default to Bearer, ya twat!

# Set up logging with debug level if enabled
logger = setup_logging(debug=DEBUG)
logger.debug(f"OpenAPI Spec URL: {OPENAPI_SPEC_URL}")
logger.debug(f"Function Config JSON: {FUNCTION_CONFIG_JSON}")
logger.debug(f"API_AUTH_TYPE: {API_AUTH_TYPE}")

# Initialize FastMCP server with a descriptive name
mcp = FastMCP("OpenApiProxy-Fast")

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

    functions = []
    # Iterate over all paths defined in the OpenAPI spec and filter based on TOOL_WHITELIST
    for path, path_item in spec.get("paths", {}).items():
        if not is_tool_whitelisted(path):
            logger.debug(f"Skipping non-whitelisted path: {path}")
            continue
        for method, operation in path_item.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue  # Skip non-standard HTTP methods
            function_name = f"{method.upper()} {path}"
            function_description = operation.get("summary", operation.get("description", "No description provided."))
            logger.debug(f"Found function: {function_name} - {function_description}")
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
    # Locate the function definition within the OpenAPI spec
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

    # Enforce whitelist filtering; only proceed if the endpoint is whitelisted
    if not is_tool_whitelisted(function_def["path"]):
        error_msg = f"Access to function '{function_name}' is not allowed."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})

    # Determine the base URL for API calls, with optional override or spec fallback
    SERVER_URL_OVERRIDE = os.getenv("SERVER_URL_OVERRIDE")
    if SERVER_URL_OVERRIDE:
        override_urls = SERVER_URL_OVERRIDE.strip().split()
        base_url = override_urls[0] if override_urls else ""
        logger.debug(f"Using SERVER_URL_OVERRIDE, base_url set to: {base_url}")
    else:
        # Try OpenAPI 3.0 'servers' first
        servers = spec.get("servers", [])
        if servers:
            base_url = servers[0].get("url", "")
            logger.debug(f"Using base_url from OpenAPI 3.0 servers: {base_url}")
        else:
            # Fallback to Swagger 2.0 'schemes' and 'basePath'
            schemes = spec.get("schemes", ["https"])  # Default to https if no schemes, ya twat
            base_path = spec.get("basePath", "")
            base_url = f"{schemes[0]}://example.com{base_path}"  # Placeholder domain, ya cunt
            logger.debug(f"Using Swagger 2.0 fallback base_url: {base_url}")
        if not base_url:
            logger.warning("No valid base URL found in spec or override; using empty string.")
            base_url = ""

    api_url = base_url.rstrip("/") + function_def["path"]
    logger.debug(f"Constructed API URL: {api_url}")

    # Prepare request parameters or body based on the HTTP method
    request_params = {}
    request_body = None
    if parameters:
        if function_def["method"] == "GET":
            request_params = parameters  # GET method: use query parameters
        else:
            request_body = parameters  # Non-GET method: use JSON body
    logger.debug(f"Request params: {request_params}, Request body: {request_body}")

    headers = {}
    api_auth = os.getenv("API_AUTH_BEARER")
    if api_auth:
        headers["Authorization"] = f"{API_AUTH_TYPE} {api_auth}"  # Bearer or Api-Key, ya farkin' genius!

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
