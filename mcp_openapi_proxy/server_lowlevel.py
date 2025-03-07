"""
Low-Level Server for mcp-openapi-proxy.

This server dynamically registers functions (tools) based on an OpenAPI specification,
directly utilizing the spec for tool definitions and invocation.
"""

import os
import sys
import asyncio
import json
import requests
from typing import List, Dict, Any
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp_openapi_proxy.utils import setup_logging, fetch_openapi_spec, normalize_tool_name, is_tool_whitelisted

# Configure logging
DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

# Global function (tool) list
tools: List[types.Tool] = []
openapi_spec_data = None  # Store OpenAPI spec globally (or use caching)

# Initialize the Low-Level MCP Server
mcp = Server("OpenApiProxy-LowLevel")

async def dispatcher_handler(request: types.CallToolRequest) -> types.ServerResult:
    """
    Dispatcher handler that routes CallToolRequest to the appropriate function (tool)
    and makes the actual API call, now handling path parameters.
    """
    global openapi_spec_data

    try:
        function_name = request.params.name
        logger.debug(f"Dispatcher received CallToolRequest for function: {function_name}")

        tool = next((tool for tool in tools if tool.name == function_name), None)
        if not tool:
            logger.error(f"Unknown function requested: {function_name}")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text="Unknown function requested")]
                )
            )

        arguments = request.params.arguments
        logger.debug(f"Function arguments: {arguments}")

        operation_details = lookup_operation_details(function_name, openapi_spec_data)
        if not operation_details:
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text=f"Could not find OpenAPI operation for function: {function_name}")]
                )
            )

        path = operation_details['path']
        method = operation_details['method']
        operation = operation_details['operation']

        # Construct API request URL
        base_url = openapi_spec_data.get('servers', [{}])[0].get('url', '').rstrip('/')
        api_url = base_url + path
        path_params = {}  # Dictionary to hold path parameters

        # Extract path parameters from arguments and replace in URL
        if arguments and 'parameters' in arguments:
            path_params_in_openapi = [
                param['name'] for param in operation.get('parameters', []) if param['in'] == 'path'
            ]
            for param_name in path_params_in_openapi:
                if param_name in arguments['parameters']:
                    path_params[param_name] = arguments['parameters'].pop(param_name)  # Remove from arguments as it's a path param
                    api_url = api_url.replace(f"{{{param_name}}}", str(path_params[param_name]))  # Replace placeholder in URL

        # Prepare remaining parameters as query parameters (after removing path params)
        query_params = {}
        headers = {}
        auth_token = os.getenv("API_AUTH_BEARER")
        if auth_token:
            headers["Authorization"] = "Bearer " + auth_token
        request_body = None

        if arguments and 'parameters' in arguments:  # 'parameters' now only contains query params (after path params removed)
            query_params = arguments['parameters'].copy()

        logger.debug(f"API Request URL: {api_url}")
        logger.debug(f"Request Method: {method}")
        logger.debug(f"Path Parameters: {path_params}")
        logger.debug(f"Query Parameters: {query_params}")

        try:
            response = requests.request(
                method=method,
                url=api_url,
                params=query_params if query_params else None,
                headers=headers,
                json=request_body if request_body else None
            )
            response.raise_for_status()

            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text=json.dumps({
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "body": response_data
                    }, indent=2))]
                )
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text=json.dumps({
                        "error": f"API request failed: {e}"
                    }, indent=2))]
                )
            )

    except Exception as e:
        logger.error(f"Unhandled exception in dispatcher_handler: {e}", exc_info=True)
        return types.ServerResult(
            root=types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps({"error": "Internal server error."}, indent=2))]
            )
        )

async def list_tools(request: types.ListToolsRequest) -> types.ServerResult:
    """
    Handler for ListToolsRequest to list all registered functions (tools).
    """
    logger.debug("Handling list_tools request.")
    return types.ServerResult(root=types.ListToolsResult(tools=tools))

def register_functions(spec: Dict) -> List[types.Tool]:
    """
    Register functions (tools) dynamically based on the OpenAPI specification.
    No longer stores metadata in tool.metadata, relies on spec lookup.
    """
    global tools
    tools = []  # Clear existing functions before re-registration

    if not spec or 'paths' not in spec:
        logger.warning("No paths found in OpenAPI spec, no functions registered.")
        return tools

    for path, path_item in spec['paths'].items():
        if not is_tool_whitelisted(path):
            logger.debug(f"Skipping non-whitelisted path: {path}")
            continue
        for method, operation in path_item.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                continue  # Skip OPTIONS, HEAD etc.

            try:
                # Create a function name from method and path
                function_name = normalize_tool_name(f"{method.upper()} {path}")  # Normalize function name

                description = operation.get('summary', operation.get('description', 'No description available'))

                # Define a generic input schema - you can expand on this later
                input_schema = {
                    "type": "object",
                    "properties": {
                        "parameters": {  # Generic 'parameters' field for now
                            "type": "object",
                            "description": "Parameters for the API call",
                            "additionalProperties": True  # Allow any properties for parameters
                        }
                    },
                    "additionalProperties": False  # No other top-level properties allowed
                }

                tool = types.Tool(
                    name=function_name,
                    description=description,
                    inputSchema=input_schema,
                )
                tools.append(tool)
                logger.debug(f"Registered function: {function_name} ({method.upper()} {path})")

            except Exception as e:
                logger.error(f"Error registering function for {method.upper()} {path}: {e}")

    logger.info(f"Registered {len(tools)} functions from OpenAPI spec.")
    return tools

def lookup_operation_details(function_name: str, spec: Dict) -> Dict or None:
    """
    Lookup OpenAPI operation details (path, method, operation) based on function name.
    """
    if not spec or 'paths' not in spec:
        return None

    for path, path_item in spec['paths'].items():
        for method, operation in path_item.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                continue

            current_function_name = normalize_tool_name(f"{method.upper()} {path}")
            if current_function_name == function_name:
                return {
                    "path": path,
                    "method": method.upper(),
                    "operation": operation
                }
    return None

async def start_server():
    """
    Start the Low-Level MCP server.
    """
    logger.debug("Starting Low-Level MCP server...")
    try:
        async with stdio_server() as (read_stream, write_stream):
            await mcp.run(
                read_stream,
                write_stream,
                initialization_options=InitializationOptions(
                    server_name="AnyOpenAPIMCP-LowLevel",
                    server_version="0.1.0",
                    capabilities=types.ServerCapabilities(),
                ),
            )
    except Exception as e:
        logger.critical(f"Unhandled exception in MCP server: {e}", exc_info=True)
        sys.exit(1)

def run_server():
    """
    Run the Low-Level Any OpenAPI server.
    Fetches OpenAPI spec, registers functions, and makes it available globally.
    """
    global openapi_spec_data  # To store it globally

    try:
        openapi_url = os.getenv('OPENAPI_SPEC_URL', 'https://raw.githubusercontent.com/seriousme/fastify-openapi-glue/refs/heads/master/examples/petstore/petstore-openapi.v3.json')
        openapi_spec_data = fetch_openapi_spec(openapi_url)  # Fetch and store globally
        if not openapi_spec_data:
            logger.critical("Failed to fetch or parse OpenAPI specification.")
            sys.exit(1)
        logger.info("OpenAPI specification fetched successfully.")

        # Preload tools before running server, ya fuckin’ genius
        register_functions(openapi_spec_data)  # Register tools at startup, ya wanker

        mcp.request_handlers[types.ListToolsRequest] = list_tools
        logger.debug("Registered list_tools handler.")

        mcp.request_handlers[types.CallToolRequest] = dispatcher_handler
        logger.debug("Registered dispatcher_handler for CallToolRequest.")

        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.debug("MCP server shutdown initiated by user.")
    except Exception as e:
        logger.critical(f"Failed to start MCP server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_server()
