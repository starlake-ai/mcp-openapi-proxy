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
from urllib.parse import unquote
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp_openapi_proxy.utils import setup_logging, normalize_tool_name, is_tool_whitelisted, fetch_openapi_spec, build_base_url, handle_auth, strip_parameters, detect_response_type

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
logger = setup_logging(debug=DEBUG)

tools: List[types.Tool] = []  # Global tools list
openapi_spec_data = None

mcp = Server("OpenApiProxy-LowLevel")

async def dispatcher_handler(request: types.CallToolRequest) -> types.ServerResult:
    """Dispatcher handler that routes CallToolRequest to the appropriate function (tool)."""
    global openapi_spec_data
    try:
        function_name = request.params.name
        logger.debug(f"Dispatcher received CallToolRequest for function: {function_name}")
        logger.debug(f"API_KEY: {os.getenv('API_KEY', '<not set>')[:5] + '...' if os.getenv('API_KEY') else '<not set>'}")
        logger.debug(f"STRIP_PARAM: {os.getenv('STRIP_PARAM', '<not set>')}")
        tool = next((tool for tool in tools if tool.name == function_name), None)
        if not tool:
            logger.error(f"Unknown function requested: {function_name}")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text="Unknown function requested")]
                )
            )
        arguments = request.params.arguments or {}
        logger.debug(f"Raw arguments before processing: {arguments}")

        operation_details = lookup_operation_details(function_name, openapi_spec_data)
        if not operation_details:
            logger.error(f"Could not find OpenAPI operation for function: {function_name}")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text=f"Could not find OpenAPI operation for function: {function_name}")]
                )
            )

        operation = operation_details['operation']
        operation['method'] = operation_details['method']
        headers = handle_auth(operation)
        parameters = strip_parameters(arguments)
        method = operation_details['method']
        if method != "GET":
            headers["Content-Type"] = "application/json"

        path = operation_details['path']

        base_url = build_base_url(openapi_spec_data)
        if not base_url:
            logger.critical("Failed to construct base URL from spec or SERVER_URL_OVERRIDE.")
            return types.ServerResult(
                root=types.CallToolResult(
                    content=[types.TextContent(type="text", text="No base URL defined in spec or SERVER_URL_OVERRIDE")]
                )
            )

        api_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        request_params = {}
        request_body = None

        if isinstance(parameters, dict):
            path_params_in_openapi = [
                param['name'] for param in operation.get('parameters', []) if param.get('in') == 'path'
            ]
            if path_params_in_openapi:
                missing_required = [
                    param['name'] for param in operation.get('parameters', [])
                    if param.get('in') == 'path' and param.get('required', False) and param['name'] not in parameters
                ]
                if missing_required:
                    logger.error(f"Missing required path parameters: {missing_required}")
                    return types.ServerResult(
                        root=types.CallToolResult(
                            content=[types.TextContent(type="text", text=f"Missing required path parameters: {missing_required}")]
                        )
                    )
                for param_name in path_params_in_openapi:
                    if param_name in parameters:
                        value = str(parameters.pop(param_name))
                        api_url = api_url.replace(f"{{{param_name}}}", value)
                        api_url = api_url.replace(f"%7B{param_name}%7D", value)
                        logger.debug(f"Replaced path param {param_name} in URL: {api_url}")
            if method == "GET":
                request_params = parameters
            else:
                request_body = parameters
        else:
            logger.debug("No valid parameters provided, proceeding without params/body")

        logger.debug(f"API Request - URL: {api_url}, Method: {method}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Query Params: {request_params}")
        logger.debug(f"Request Body: {request_body}")

        try:
            response = requests.request(
                method=method,
                url=api_url,
                headers=headers,
                params=request_params if method == "GET" else None,
                json=request_body if method != "GET" else None
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
                content=[types.TextContent(type="text", text=f"Internal error: {str(e)}")]
            )
        )

async def list_tools(request: types.ListToolsRequest) -> types.ServerResult:
    logger.debug("Handling list_tools request - start")
    logger.debug(f"Tools list length: {len(tools)}")
    result = types.ServerResult(root=types.ListToolsResult(tools=tools))
    logger.debug("list_tools result prepared")
    sys.stderr.flush()
    return result

def register_functions(spec: Dict) -> List[types.Tool]:
    """Register tools from OpenAPI spec, preserving across calls if already populated."""
    global tools
    if tools:  # If tools already exist, don’t reset unless spec changes
        logger.debug("Tools already registered, skipping re-registration")
        return tools
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
