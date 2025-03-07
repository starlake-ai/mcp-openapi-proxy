"""
Provides the FastMCP server logic for mcp-openapi-proxy.

This server exposes a pre-defined set of functions based on an OpenAPI specification.
Configuration is controlled via environment variables:

- OPENAPI_SPEC_URL_<hash>: Unique URL per test, falls back to OPENAPI_SPEC_URL.
- TOOL_WHITELIST: Comma-separated list of allowed endpoint paths.
- SERVER_URL_OVERRIDE: (Optional) Overrides the base URL from the OpenAPI spec.
- API_AUTH_BEARER: (Optional) Token for endpoints requiring authentication.
- API_AUTH_TYPE_OVERRIDE: (Optional) 'Bearer' or 'Api-Key'.
"""

import os
import sys
import json
import requests

from mcp.server.fastmcp import FastMCP
from mcp_openapi_proxy.utils import setup_logging, is_tool_whitelisted, get_auth_type

# Logger sorted via utils, all to stderr, ya wanker
logger = setup_logging(debug=os.getenv("DEBUG", "").lower() in ("true", "1", "yes"))

logger.debug(f"Server CWD: {os.getcwd()}")
logger.debug(f"Server sys.path: {sys.path}")

mcp = FastMCP("OpenApiProxy-Fast")

def fetch_openapi_spec(spec_url: str) -> dict:
    logger.debug(f"Starting fetch_openapi_spec with spec_url: {spec_url}")
    if not spec_url:
        logger.error("spec_url is empty or None")
        return None
    logger.debug(f"Current CWD in fetch_openapi_spec: {os.getcwd()}")
    try:
        if spec_url.startswith("file://"):
            spec_path = os.path.abspath(spec_url.replace("file://", ""))
            logger.debug(f"Spec path after file:// strip and abspath: {spec_path}")
            if not os.path.exists(spec_path):
                logger.error(f"File does not exist at: {spec_path}")
                return None
            logger.debug(f"File exists at: {spec_path}")
            with open(spec_path, 'r') as f:
                spec = json.load(f)
            logger.debug(f"Successfully read local OpenAPI spec from {spec_path}")
        else:
            logger.debug(f"Fetching remote spec from {spec_url}")
            response = requests.get(spec_url)
            response.raise_for_status()
            spec = json.loads(response.text)
            logger.debug(f"Successfully fetched OpenAPI spec from {spec_url}")
        if not spec:
            logger.error(f"Spec is empty after loading from {spec_url}")
            return None
        logger.debug(f"Spec keys loaded: {list(spec.keys())}")
        logger.debug(f"Spec paths: {list(spec.get('paths', {}).keys())}")
        return spec
    except Exception as e:
        logger.error(f"Failed to fetch or parse spec from {spec_url}: {e}", exc_info=True)
        return None

@mcp.tool()
def list_functions(*, env_key: str = "OPENAPI_SPEC_URL") -> str:
    logger.debug("Executing list_functions tool.")
    spec_url = os.environ.get(env_key, os.environ.get("OPENAPI_SPEC_URL"))
    whitelist = os.getenv('TOOL_WHITELIST')
    logger.debug(f"Using spec_url: {spec_url}")
    logger.debug(f"TOOL_WHITELIST value: {whitelist}")
    if not spec_url:
        logger.error("No OPENAPI_SPEC_URL or custom env_key configured.")
        return json.dumps([])
    logger.debug(f"Calling fetch_openapi_spec with: {spec_url}")
    spec = fetch_openapi_spec(spec_url)
    if spec is None:
        logger.error("Spec is None after fetch_openapi_spec")
        return json.dumps([])
    logger.debug(f"Raw spec loaded: {json.dumps(spec, indent=2)}")
    logger.debug(f"Spec loaded with keys: {list(spec.keys())}")
    paths = spec.get("paths", {})
    logger.debug(f"Paths extracted from spec: {list(paths.keys())}")
    if not paths:
        logger.debug("No paths found in spec.")
        return json.dumps([])
    functions = []
    for path, path_item in paths.items():
        logger.debug(f"Processing path: {path}")
        if not path_item:
            logger.debug(f"Path item is empty for {path}")
            continue
        whitelist_check = is_tool_whitelisted(path)
        logger.debug(f"Whitelist check for {path}: {whitelist_check}")
        if not whitelist_check:
            logger.debug(f"Path {path} not in whitelist - skipping.")
            continue
        for method, operation in path_item.items():
            logger.debug(f"Found method: {method} for path: {path}")
            if not method:
                logger.debug(f"Method is empty for {path}")
                continue
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                logger.debug(f"Method {method} not supported for {path} - skipping.")
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
    logger.debug(f"Functions list: {functions}")
    return json.dumps(functions, indent=2)

@mcp.tool()
def call_function(*, function_name: str, parameters: dict = None, env_key: str = "OPENAPI_SPEC_URL") -> str:
    logger.debug(f"call_function invoked with function_name='{function_name}' and parameters={parameters}")
    if not function_name:
        logger.error("function_name is empty or None")
        return json.dumps({"error": "function_name is required"})
    spec_url = os.environ.get(env_key, os.environ.get("OPENAPI_SPEC_URL"))
    if not spec_url:
        logger.error("No OPENAPI_SPEC_URL or custom env_key configured.")
        return json.dumps({"error": "OPENAPI_SPEC_URL is not configured"})
    logger.debug(f"Fetching spec for call_function: {spec_url}")
    spec = fetch_openapi_spec(spec_url)
    if spec is None:
        logger.error("Spec is None for call_function")
        return json.dumps({"error": "Failed to fetch or parse the OpenAPI specification"})
    logger.debug(f"Spec keys for call_function: {list(spec.keys())}")
    API_AUTH_TYPE = os.getenv("API_AUTH_TYPE_OVERRIDE", get_auth_type(spec))
    logger.debug(f"API_AUTH_TYPE set to: {API_AUTH_TYPE}")
    function_def = None
    paths = spec.get("paths", {})
    logger.debug(f"Paths for function lookup: {list(paths.keys())}")
    for path, path_item in paths.items():
        logger.debug(f"Checking path: {path}")
        for method, operation in path_item.items():
            logger.debug(f"Checking method: {method} for {path}")
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                logger.debug(f"Skipping unsupported method: {method}")
                continue
            current_function_name = f"{method.upper()} {path}"
            logger.debug(f"Comparing {current_function_name} with {function_name}")
            if current_function_name == function_name:
                function_def = {
                    "path": path,
                    "method": method.upper(),
                    "operation": operation
                }
                logger.debug(f"Matched function definition for '{function_name}': {function_def}")
                break
        if function_def:
            break
    if not function_def:
        logger.error(f"Function '{function_name}' not found in the OpenAPI specification.")
        return json.dumps({"error": f"Function '{function_name}' not found"})
    logger.debug(f"Function def found: {function_def}")
    if not is_tool_whitelisted(function_def["path"]):
        logger.error(f"Access to function '{function_name}' is not allowed.")
        return json.dumps({"error": f"Access to function '{function_name}' is not allowed"})
    SERVER_URL_OVERRIDE = os.getenv("SERVER_URL_OVERRIDE")
    if SERVER_URL_OVERRIDE:
        base_url = SERVER_URL_OVERRIDE.strip()
        logger.debug(f"Using SERVER_URL_OVERRIDE: {base_url}")
    else:
        servers = spec.get("servers", [])
        logger.debug(f"Servers from spec: {servers}")
        if servers:
            base_url = servers[0].get("url", "")
            logger.debug(f"Using base_url from OpenAPI 3.0 servers: {base_url}")
        else:
            schemes = spec.get("schemes", ["https"])
            host = spec.get("host", "example.com")
            base_url = f"{schemes[0]}://{host}"
            logger.debug(f"Using Swagger 2.0 fallback base_url: {base_url}")
        if not base_url:
            logger.warning("No valid base URL found in spec or override; using empty string.")
            base_url = ""
    base_url = base_url.rstrip("/")
    logger.debug(f"Normalized base_url: {base_url}")
    base_path = spec.get("basePath", "")
    if base_path:
        base_path = "/" + base_path.strip("/")
        logger.debug(f"Normalized base_path: {base_path}")
        if base_path not in base_url:
            base_url = base_url + base_path
            logger.debug(f"Added base_path to URL: {base_url}")
    path = function_def["path"]
    path = "/" + path.lstrip("/")
    logger.debug(f"Normalized path: {path}")
    api_url = base_url + path
    logger.debug(f"Final API URL: {api_url}")
    request_params = {}
    request_body = None
    headers = {"Content-Type": "application/json"}
    if parameters is None:
        logger.debug("Parameters is None, using empty dict")
        parameters = {}
    logger.debug(f"Parameters received: {parameters}")
    if parameters:
        if function_def["method"] == "GET":
            request_params = parameters
            logger.debug(f"Set request_params for GET: {request_params}")
        else:
            request_body = parameters
            logger.debug(f"Set request_body: {request_body}")
    api_auth = os.getenv("API_AUTH_BEARER")
    if api_auth:
        headers["Authorization"] = f"{API_AUTH_TYPE} {api_auth}"
        logger.debug(f"Added Authorization header with {API_AUTH_TYPE}")
    logger.debug(f"Sending request - Method: {function_def['method']}, URL: {api_url}, Headers: {headers}, Params: {request_params}, Body: {request_body}")
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
        logger.error(f"API request failed: {e}", exc_info=True)
        return json.dumps({"error": f"API request failed: {e}"})

def run_simple_server():
    logger.debug("Starting run_simple_server")
    spec_url = os.environ.get("OPENAPI_SPEC_URL")
    if not spec_url:
        logger.error("OPENAPI_SPEC_URL environment variable is required for FastMCP mode.")
        sys.exit(1)
    
    # Preload tools, ya fuckin’ genius
    logger.debug("Preloading tools from OpenAPI spec...")
    spec = fetch_openapi_spec(spec_url)
    if spec is None:
        logger.error("Failed to fetch OpenAPI spec, no tools to preload.")
        sys.exit(1)
    list_functions()  # Call it to register tools at startup, ya wanker
    
    try:
        logger.debug("Starting MCP server (FastMCP version)...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error("Unhandled exception in MCP server (FastMCP): %s", e, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_simple_server()
