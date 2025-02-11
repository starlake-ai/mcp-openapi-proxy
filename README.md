# mcp-openapi-proxy

**mcp-openapi-proxy** is a Python package implementing a Model Context Protocol (MCP) server that dynamically exposes REST APIs defined by OpenAPI specifications as MCP tools. This allows you to easily integrate any OpenAPI-described API into MCP-based workflows.

## Overview

The package supports two operation modes:

- **Low-Level Mode (Default):** Dynamically registers tools for all API endpoints defined in an OpenAPI specification.
- **FastMCP Mode (Simple Mode):** Provides a simplified mode for exposing specific pre-configured API endpoints as tools.

## Features

- **Dynamic Tool Generation:** Automatically creates MCP tools from OpenAPI endpoint definitions.
- **Simple Mode Option:** Offers a static configuration option with FastMCP mode.
- **OpenAPI Specification Support:** Works with OpenAPI v3 specifications, and potentially v2.
- **Flexible Filtering:** Supports filtering endpoints by tags, paths, methods, etc. (if implemented)
- **MCP Integration:** Integrates seamlessly with MCP ecosystems to invoke REST APIs as tools.

## Installation

Run the server directly from the GitHub repository using `uvx`:

```bash
uvx --from git+https://github.com/matthewhand/mcp-openapi-proxy mcp-openapi-proxy
```

## MCP Ecosystem Integration

Add **mcp-openapi-proxy** to your MCP ecosystem by configuring your `mcpServers`. Example:

```json
{
    "mcpServers": {
        "mcp-openapi-proxy": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/matthewhand/mcp-openapi-proxy",
                "mcp-openapi-proxy"
            ],
            "env": {
                "OPENAPI_SPEC_URL": "${OPENAPI_SPEC_URL}",
                "TOOL_WHITELIST": "VERBA_",
                "TOOL_NAME_PREFIX": "api"
            }
        }
    }
}
```

## Modes of Operation

### FastMCP Mode (Simple Mode)

- **Enabled by:** Setting `OPENAPI_SIMPLE_MODE=true`
- **Description:** Exposes a pre-defined set of tools based on specific OpenAPI endpoints defined in code.
- **Configuration:** Requires environment variables for tool definitions.

### Low-Level Mode (Default)

- **Description:** Dynamically registers all valid API endpoints from the provided OpenAPI specification as separate tools.
- **Tool Naming:** Tools are named based on normalized OpenAPI path and method.
- **Behavior:** Descriptions are generated from the OpenAPI operation summaries and descriptions.

## Environment Variables

- `OPENAPI_SPEC_URL`: URL to the OpenAPI specification JSON file (required).
- `MCP_API_PREFIX`: Prefix for the generated MCP tool names (default: `any_openapi`).
- `MCP_OPENAPI_LOGFILE_PATH`: Path for the log file.
- `OPENAPI_SIMPLE_MODE`: Set to `true` for FastMCP mode.
- `TOOL_WHITELIST`: (Optional) A prefix filter to select only certain tools.
- `TOOL_NAME_PREFIX`: (Optional) A string to prepend to all tool names when mapping.

## Examples

### OpenWebUI Example

**1. Confirming the OpenAPI Endpoint**

Run the following command to retrieve the OpenAPI specification:
 
```bash
curl http://localhost:3000/openapi.json
```
 
If the output is a valid OpenAPI JSON document, it confirms that the endpoint is working correctly.

**2. Configuring mcp-openapi-proxy**

In your MCP ecosystem configuration file, set the `OPENAPI_SPEC_URL` to the above endpoint. For example:
 
```json
{
    "mcpServers": {
        "mcp-openapi-proxy": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/matthewhand/mcp-openapi-proxy",
                "mcp-openapi-proxy"
            ],
            "env": {
                "OPENAPI_SPEC_URL": "http://localhost:3000/openapi.json",
                "TOOL_WHITELIST": "/api/models,/api/chat/completions",
                "API_AUTH_BEARER": "your_api_bearer_token_here"
            }
        }
    }
}
```
 
- **OPENAPI_SPEC_URL**: The URL to the OpenAPI specification.
- **TOOL_WHITELIST**: A comma-separated list of endpoint paths to expose as tools. In this example, only the `/api/models` and `/api/chat/completions` endpoints are allowed.
- **API_AUTH_BEARER**: The bearer token for endpoints requiring authentication.

**3. Resulting Tools**

With this configuration, the MCP server will dynamically generate tools for the whitelisted endpoints. For example:
 
```json
[
    {
        "name": "api_models",
        "description": "Fetches available models from /api/models"
    },
    {
        "name": "api_chat_completions",
        "description": "Generates chat completions via /api/chat/completions"
    }
]
```
 
**4. Visual Verification**
 
You can verify the registration of these tools by inspecting the MCP server logs or using your MCP client.
 
## Quivr Example

**1. Verify the OpenAPI Endpoint**

Run the following command to retrieve the Quivr OpenAPI JSON specification:

```bash
curl https://api.quivr.app/openapi.json
```

Ensure the response is a valid OpenAPI JSON document containing an "openapi" field (e.g., "openapi": "3.0.0") and defined API paths.

**2. Configure mcp-openapi-proxy for Quivr**

Update your MCP ecosystem configuration to point to the Quivr endpoint. For example:

```json
{
    "mcpServers": {
        "mcp-openapi-proxy": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/matthewhand/mcp-openapi-proxy",
                "mcp-openapi-proxy"
            ],
            "env": {
                "OPENAPI_SPEC_URL": "https://api.quivr.app/openapi.json",
                "TOOL_WHITELIST": "/api/models,/api/chat/completions",
                "API_AUTH_BEARER": "your_quivr_token_here"
            }
        }
    }
}
```

**3. Resulting Tools**

With this configuration, the MCP server will dynamically generate tools for the whitelisted endpoints. For example:

```json
[
    {
        "name": "api_models",
        "description": "Fetches available models from /api/models"
    },
    {
        "name": "api_chat_completions",
        "description": "Generates chat completions via /api/chat/completions"
    }
]
```

## Troubleshooting

- **Missing OPENAPI_SPEC_URL:** Verify that the `OPENAPI_SPEC_URL` environment variable is set and points to a valid OpenAPI JSON file.
- **Invalid OpenAPI Spec:** Ensure the JSON specification complies with the OpenAPI standard.
- **Filtering Issues:** Check that `TOOL_WHITELIST` is correctly defined to filter the desired classes.
- **Logging:** Consult the logs (as defined by `MCP_OPENAPI_LOGFILE_PATH`) for debugging information.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## GetZep Example

**1. Verify the Swagger Endpoint**

Run the following command to retrieve the GetZep Swagger JSON specification:

```bash
curl https://getzep.github.io/zep/swagger.json
```

Ensure the response is a valid Swagger document containing a "swagger" field (e.g., "swagger": "2.0") and defined API paths.

**2. Configure mcp-openapi-proxy for GetZep**

Update your MCP ecosystem configuration to point to the GetZep Swagger endpoint. For example:

```json
{
    "mcpServers": {
        "mcp-openapi-proxy": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/matthewhand/mcp-openapi-proxy",
                "mcp-openapi-proxy"
            ],
            "env": {
                "OPENAPI_SPEC_URL": "https://getzep.github.io/zep/swagger.json",
                "TOOL_WHITELIST": "/api/models,/api/chat/completions",
                "API_AUTH_BEARER": "your_getzep_token_if_required"
            }
        }
    }
}
```

**3. Resulting Tools**

With this configuration, the MCP server will dynamically generate tools for the whitelisted endpoints. For example:

```json
[
    {
        "name": "api_models",
        "description": "Fetches available models from /api/models"
    },
    {
        "name": "api_chat_completions",
        "description": "Generates chat completions via /api/chat/completions"
    }
]
```
