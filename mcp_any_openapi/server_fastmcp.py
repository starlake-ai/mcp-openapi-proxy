"""
Provides the FastMCP server logic for mcp_any_openapi.

This server exposes a pre-defined set of functions based on OpenAPI specifications,
configured via environment variables.
"""

import os
import sys
import json
import requests  # Import requests to make API calls
from mcp.server.fastmcp import FastMCP
from mcp_any_openapi.utils import setup_logging, fetch_openapi_spec  # Import utils if needed

# Environment variables
OPENAPI_SPEC_URL = os.getenv("OPENAPI_SPEC_URL")
# Example configurations for specific functions (you'll need to define these)
FUNCTION_CONFIG_JSON = os.getenv("OPENAPI_SIMPLE_MODE_FUNCTION_CONFIG") # JSON config for functions

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

# Configure logging
logger = setup_logging(debug=DEBUG)

# Log key environment variable values
logger.debug(f"OpenAPI Spec URL: {OPENAPI_SPEC_URL}")
logger.debug(f"Function Config JSON: {FUNCTION_CONFIG_JSON}")


# Initialize FastMCP Server
mcp = FastMCP("AnyOpenAPIMCP-Fast")


@mcp.tool()
def list_functions() -> str:
    """
    List available functions (API endpoints) from the OpenAPI specification.

    Returns:
        str: A JSON-encoded string of available function descriptions.
    """
    logger.debug("Handling list_functions tool.")
    if not OPENAPI_SPEC_URL:
        return json.dumps({"error": "OPENAPI_SPEC_URL is not configured."})

    spec = fetch_openapi_spec(OPENAPI_SPEC_URL)
    if not spec:
        return json.dumps({"error": "Failed to fetch or parse OpenAPI specification."})

    functions = []
    for path, path_item in spec.get('paths', {}).items():
        for method, operation in path_item.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                continue # Skip OPTIONS, HEAD etc.

            function_name = f"{method.upper()} {path}" # Simple function name
            function_description = operation.get('summary', operation.get('description', 'No description'))

            functions.append({
                "name": function_name,
                "description": function_description,
                "path": path,
                "method": method.upper(),
                "operationId": operation.get('operationId') # useful for later?
            })

    return json.dumps(functions, indent=2)


@mcp.tool()
def call_function(*, function_name: str, parameters: dict = None) -> str:
    """
    Call a specific API function (OpenAPI endpoint).

    Args:
        function_name (str): The name of the function to call (e.g., 'GET /pets').
        parameters (dict, optional): Parameters for the API call. Defaults to None.

    Returns:
        str: The JSON response from the API call, or an error message.
    """
    logger.debug(f"call_function called with function_name={function_name}, parameters={parameters}")

    if not OPENAPI_SPEC_URL:
        return json.dumps({"error": "OPENAPI_SPEC_URL is not configured."})

    spec = fetch_openapi_spec(OPENAPI_SPEC_URL)
    if not spec:
        return json.dumps({"error": "Failed to fetch or parse OpenAPI specification."})

    # Find the function definition from the spec (very basic matching for now)
    function_def = None
    for path, path_item in spec.get('paths', {}).items():
        for method, operation in path_item.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                continue
            current_function_name = f"{method.upper()} {path}"
            if current_function_name == function_name:
                function_def = {
                    "path": path,
                    "method": method.upper(),
                    "operation": operation
                }
                break
        if function_def:
            break

    if not function_def:
        return json.dumps({"error": f"Function '{function_name}' not found in OpenAPI spec."})

    # Construct API request URL (basic - you'll need to handle server URL from spec)
    base_url = spec.get('servers', [{}])[0].get('url', '') # Very basic server URL extraction
    api_url = base_url.rstrip('/') + function_def["path"]

    # Prepare parameters (query parameters for GET, request body for others - needs more robust handling)
    request_params = {}
    request_body = None

    if parameters:
        if function_def["method"] == "GET":
            request_params = parameters # Assume GET params are query params
        else:
            request_body = parameters # Assume other methods use request body


    try:
        response = requests.request(
            method=function_def["method"],
            url=api_url,
            params=request_params if function_def["method"] == "GET" else None,
            json=request_body if function_def["method"] != "GET" and request_body else None # Send body as JSON if not GET and body exists
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.text # Return raw response text for now (you might want to parse JSON and format)

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"API request failed: {e}"})



def run_simple_server():
    """
    Run the FastMCP version of the Any OpenAPI server.

    This function initializes and runs the FastMCP server, making sure
    required configurations are in place.
    """
    if not OPENAPI_SPEC_URL:
        logger.error("OPENAPI_SPEC_URL environment variable is required for simple mode.")
        sys.exit(1)

    try:
        logger.debug("Starting MCP server (FastMCP version)...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error("Unhandled exception in MCP server (FastMCP).", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_simple_server()