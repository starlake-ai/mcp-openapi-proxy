"""
High-Level Server for mcp-openapi-proxy.

This server dynamically registers functions (tools) based on an OpenAPI specification,
using the high-level MCP abstractions.
"""

import os
import sys
import asyncio
import requests
from typing import List, Dict, Any
from mcp import types, Server, Tool, Parameter, SchemaType
from mcp_openapi_proxy.utils import setup_logging, normalize_tool_name, is_tool_whitelisted, fetch_openapi_spec, get_auth_headers, detect_response_type

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

tools: List[Tool] = []
openapi_spec_data = None

mcp = Server("OpenApiProxy-HighLevel")

@mcp.tool()
async def call_openapi_operation(*, operation_id: str, parameters: Dict[str, Any] = None) -> types.Content:
    """Call an OpenAPI operation by its operationId with the provided parameters."""
    global openapi_spec_data
    parameters = parameters or {}
    logger.debug(f"Calling operation: {operation_id} with parameters: {parameters}")
    
    # Find the operation in the OpenAPI spec
    operation_details = None
    for path, path_item in openapi_spec_data.get("paths", {}).items():
        for method, operation in path_item.items():
            if operation.get("operationId") == operation_id:
                operation_details = {"path": path, "method": method.upper(), "operation": operation}
                break
        if operation_details:
            break
    
    if not operation_details:
        return types.TextContent(type="text", text=f"Operation {operation_id} not found in OpenAPI spec.")
    
    path = operation_details["path"]
    method = operation_details["method"]
    operation = operation_details["operation"]

    # Build base URL from spec - Swagger 2.0 or OpenAPI 3.0
    base_url = ""
    if "servers" in openapi_spec_data and openapi_spec_data["servers"]:
        base_url = openapi_spec_data["servers"][0].get("url", "").rstrip('/')
        logger.debug(f"Using OpenAPI 3.0 servers base URL: {base_url}")
    elif "host" in openapi_spec_data:
        scheme = openapi_spec_data.get("schemes", ["https"])[0]
        host = openapi_spec_data["host"].strip()
        base_url = f"{scheme}://{host}"
        base_path = openapi_spec_data.get("basePath", "").strip('/')
        if base_path:
            base_url += f"/{base_path}"
        logger.debug(f"Using Swagger 2.0 host/basePath base URL: {base_url}")
    else:
        logger.critical("No servers or host defined in OpenAPI spec - cannot construct base URL.")
        return types.TextContent(type="text", text="No base URL defined in spec.")

    if not base_url:
        logger.critical("Base URL is empty after spec parsing - check spec configuration.")
        return types.TextContent(type="text", text="Empty base URL from spec.")

    api_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    path_params = {}
    query_params = parameters.copy()
    headers = get_auth_headers(openapi_spec_data)
    request_body = None

    # Handle path parameters
    path_params_in_openapi = [
        param["name"] for param in operation.get("parameters", []) if param["in"] == "path"
    ]
    for param_name in path_params_in_openapi:
        if param_name in query_params:
            path_params[param_name] = query_params.pop(param_name)
            api_url = api_url.replace(f"{{{param_name}}}", str(path_params[param_name]))

    logger.debug(f"API Request URL: {api_url}")
    logger.debug(f"Request Method: {method}")
    logger.debug(f"Path Parameters: {path_params}")
    logger.debug(f"Query Parameters: {query_params}")
    logger.debug(f"Request Headers: {headers}")

    try:
        response = requests.request(
            method=method,
            url=api_url,
            params=query_params if query_params else None,
            headers=headers,
            json=request_body if request_body else None
        )
        response.raise_for_status()
        response_text = response.text or "No response body"

        # Detect response type using shared utility
        content, log_message = detect_response_type(response_text)
        logger.debug(log_message)

        logger.debug(f"Response sent to client: {response_text}")
        return content

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return types.TextContent(type="text", text=str(e))

def register_functions(spec: Dict) -> None:
    """Register functions (tools) dynamically based on the OpenAPI specification."""
    global tools
    tools = []

    if not spec:
        logger.error("OpenAPI spec is None or empty.")
        return

    if "paths" not in spec:
        logger.error("No 'paths' key in OpenAPI spec.")
        return

    logger.debug(f"Spec paths available: {list(spec['paths'].keys())}")
    filtered_paths = {path: item for path, item in spec["paths"].items() if is_tool_whitelisted(path)}
    logger.debug(f"Filtered paths: {list(filtered_paths.keys())}")

    if not filtered_paths:
        logger.warning("No whitelisted paths found in OpenAPI spec after filtering.")
        return

    for path, path_item in filtered_paths.items():
        if not path_item:
            logger.debug(f"Empty path item for {path}")
            continue
        for method, operation in path_item.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                logger.debug(f"Skipping unsupported method {method} for {path}")
                continue
            try:
                operation_id = operation.get("operationId")
                if not operation_id:
                    operation_id = normalize_tool_name(f"{method.upper()} {path}")
                description = operation.get("summary", operation.get("description", "No description available"))

                # Build parameters schema
                parameters = []
                for param in operation.get("parameters", []):
                    param_name = param.get("name")
                    param_in = param.get("in")
                    if param_in in ["path", "query"]:
                        param_type = param.get("type", "string")
                        schema_type = {
                            "string": SchemaType.STRING,
                            "integer": SchemaType.INTEGER,
                            "boolean": SchemaType.BOOLEAN,
                            "number": SchemaType.NUMBER
                        }.get(param_type, SchemaType.STRING)
                        parameters.append(
                            Parameter(
                                name=param_name,
                                type=schema_type,
                                description=param.get("description", f"{param_in} parameter {param_name}"),
                                required=param.get("required", False)
                            )
                        )

                # Register the tool
                tool = mcp.register_tool(
                    operation_id,
                    description=description,
                    parameters=parameters,
                    handler=call_openapi_operation
                )
                tools.append(tool)
                logger.debug(f"Registered function: {operation_id} ({method.upper()} {path}) with parameters: {[p.name for p in parameters]}")
            except Exception as e:
                logger.error(f"Error registering function for {method.upper()} {path}: {e}", exc_info=True)

    logger.info(f"Registered {len(tools)} functions from OpenAPI spec.")

async def start_server():
    """Start the High-Level MCP server."""
    logger.debug("Starting High-Level MCP server...")
    await mcp.run()

def run_server():
    """Run the High-Level Any OpenAPI server."""
    global openapi_spec_data
    try:
        openapi_url = os.getenv("OPENAPI_SPEC_URL")
        if not openapi_url:
            logger.critical("OPENAPI_SPEC_URL environment variable is required but not set.")
            sys.exit(1)

        openapi_spec_data = fetch_openapi_spec(openapi_url)
        if not openapi_spec_data:
            logger.critical("Failed to fetch or parse OpenAPI specification from OPENAPI_SPEC_URL.")
            sys.exit(1)
        logger.info("OpenAPI specification fetched successfully.")
        logger.debug(f"Full OpenAPI spec: {json.dumps(openapi_spec_data, indent=2)}")

        register_functions(openapi_spec_data)
        logger.debug(f"Tools after registration: {[tool.name for tool in tools]}")
        if not tools:
            logger.critical("No valid tools registered. Shutting down.")
            sys.exit(1)

        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.debug("MCP server shutdown initiated by user.")
    except Exception as e:
        logger.critical(f"Failed to start MCP server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_server()
