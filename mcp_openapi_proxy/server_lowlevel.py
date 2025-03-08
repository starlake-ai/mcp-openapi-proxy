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
from mcp_openapi_proxy.utils import setup_logging, normalize_tool_name, is_tool_whitelisted, fetch_openapi_spec, get_auth_headers, detect_response_type, build_base_url, handle_custom_auth

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

tools: List[types.Tool] = []
openapi_spec_data = None

mcp = Server("OpenApiProxy-LowLevel")

async def dispatcher_handler(request: types.CallToolRequest) -> types.ServerResult:
    """Dispatcher handler that routes CallToolRequest to the appropriate function (tool)."""
    global openapi_spec_data
    try:
        function_name = request.params.name
        logger.debug(f"Dispatcher received CallToolRequest for function: {function_name}")
        logger.debug(f"API_KEY from env: {os.getenv('API_KEY', '<not set>')[:5] + '...' if os.getenv('API_KEY') else '<not set>'}")
        logger.debug(f"API_KEY_JMESPATH from env: {os.getenv('API_KEY_JMESPATH', '<not set>')}")
        tool = next((tool for tool in tools if tool.name == function_name), None)
        if not tool:
            logger.error(f"Unknown function requested: {function_name}")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text="Unknown function requested")]
                )
            )
        arguments = request.params.arguments or {}
        logger.debug(f"Raw function arguments: {arguments}")

        operation_details = lookup_operation_details(function_name, openapi_spec_data)
        if not operation_details:
            logger.error(f"Could not find OpenAPI operation for function: {function_name}")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text=f"Could not find OpenAPI operation for function: {function_name}")]
                )
            )

        # Apply custom auth mapping if API_KEY_JMESPATH is set
        arguments = handle_custom_auth(operation_details, arguments)
        logger.debug(f"Arguments after auth handling: {arguments}")

        path = operation_details['path']
        method = operation_details['method']
        operation = operation_details['operation']

        base_url = build_base_url(openapi_spec_data)
        if not base_url:
            logger.critical("Failed to construct base URL from spec or SERVER_URL_OVERRIDE.")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text="No base URL defined in spec or SERVER_URL_OVERRIDE")]
                )
            )

        api_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        path_params = {}
        query_params = {}
        headers = {}
        if method != "GET":
            headers["Content-Type"] = "application/json"
        headers.update(get_auth_headers(openapi_spec_data))
        request_body = None

        if isinstance(arguments, dict):
            params = arguments
            if 'parameters' in arguments:
                params = arguments['parameters']
            if not isinstance(params, dict):
                logger.error(f"Expected arguments or parameters to be a dict, got: {type(params)}")
                return types.ServerResult(
                    root=types.CallToolResult(
                        content=[types.TextContent(type="text", text="Invalid parameters format")]
                    )
                )
            path_params_in_openapi = [
                param['name'] for param in operation.get('parameters', []) if param['in'] == 'path'
            ]
            for param_name in path_params_in_openapi:
                if param_name in params:
                    path_params[param_name] = params.pop(param_name)
                    api_url = api_url.replace(f"{{{param_name}}}", str(path_params[param_name]))
            query_params = params if method == "GET" else {}
            request_body = params if method != "GET" else None
        else:
            logger.debug("No valid arguments, proceeding without query params")

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
            content, log_message = detect_response_type(response_text)
            logger.debug(log_message)
            final_content = [content]
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text=str(e))]
                )
            )

        logger.debug(f"Response content type: {content.type}")
        logger.debug(f"Response sent to client: {content.text}")

        return types.ServerResult(
            root=types.CallToolResult(
                content=final_content
            )
        )
    except Exception as e:
        logger.error(f"Unhandled exception in dispatcher_handler: {e}", exc_info=True)
        return types.ServerResult(
            root=types.CallToolResult(
                content=[types.TextContent(type="text", text=str(e))]
            )
        )

async def list_tools(request: types.ListToolsRequest) -> types.ServerResult:
    """Handler for ListToolsRequest to list all registered functions (tools)."""
    logger.debug("Handling list_tools request - start")
    logger.debug(f"Tools list length: {len(tools)}")
    result = types.ServerResult(root=types.ListToolsResult(tools=tools))
    logger.debug("list_tools result prepared")
    sys.stderr.flush()
    return result

def register_functions(spec: Dict) -> List[types.Tool]:
    """Registers functions (tools) dynamically based on the OpenAPI specification."""
    global tools
    tools = []

    if not spec:
        logger.error("OpenAPI spec is None or empty.")
        return tools

    if 'paths' not in spec:
        logger.error("No 'paths' key in OpenAPI spec.")
        return tools

    logger.debug(f"Spec paths available: {list(spec['paths'].keys())}")
    filtered_paths = {path: item for path, item in spec['paths'].items() if is_tool_whitelisted(path)}
    logger.debug(f"Filtered paths: {list(filtered_paths.keys())}")

    if not filtered_paths:
        logger.warning("No whitelisted paths found in OpenAPI spec after filtering.")
        return tools

    for path, path_item in filtered_paths.items():
        if not path_item:
            logger.debug(f"Empty path item for {path}")
            continue
        for method, operation in path_item.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                logger.debug(f"Skipping unsupported method {method} for {path}")
                continue
            try:
                raw_name = f"{method.upper()} {path}"
                function_name = normalize_tool_name(raw_name)
                description = operation.get('summary', operation.get('description', 'No description available'))

                input_schema = {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False
                }
                parameters = operation.get('parameters', [])
                for param in parameters:
                    param_name = param.get('name')
                    param_in = param.get('in')
                    if param_in in ['path', 'query']:
                        param_type = param.get('schema', {}).get('type', 'string')
                        schema_type = param_type if param_type in ['string', 'integer', 'boolean', 'number'] else 'string'
                        input_schema['properties'][param_name] = {
                            "type": schema_type,
                            "description": param.get('description', f"{param_in} parameter {param_name}")
                        }
                        if param.get('required', False):
                            input_schema['required'].append(param_name)

                tool = types.Tool(
                    name=function_name,
                    description=description,
                    inputSchema=input_schema,
                )
                tools.append(tool)
                logger.debug(f"Registered function: {function_name} ({method.upper()} {path}) with inputSchema: {json.dumps(input_schema)}")
            except Exception as e:
                logger.error(f"Error registering function for {method.upper()} {path}: {e}", exc_info=True)

    logger.info(f"Registered {len(tools)} functions from OpenAPI spec.")
    return tools

def lookup_operation_details(function_name: str, spec: Dict) -> Dict or None:
    """Looks up OpenAPI operation details based on function name."""
    if not spec or 'paths' not in spec:
        return None
    for path, path_item in spec['paths'].items():
        for method, operation in path_item.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                continue
            raw_name = f"{method.upper()} {path}"
            current_function_name = normalize_tool_name(raw_name)
            if current_function_name == function_name:
                return {"path": path, "method": method.upper(), "operation": operation}
    return None

async def start_server():
    """Starts the Low-Level MCP server."""
    logger.debug("Starting Low-Level MCP server...")
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

def run_server():
    """Runs the Low-Level Any OpenAPI server."""
    global openapi_spec_data
    try:
        openapi_url = os.getenv('OPENAPI_SPEC_URL')
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

        mcp.request_handlers[types.ListToolsRequest] = list_tools
        mcp.request_handlers[types.CallToolRequest] = dispatcher_handler
        logger.debug("Handlers registered.")

        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.debug("MCP server shutdown initiated by user.")
    except Exception as e:
        logger.critical(f"Failed to start MCP server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_server()
