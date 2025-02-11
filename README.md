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

Below is an example demonstrating how to use the Verba endpoint for tool discovery and mapping:

### 1. Discovering the Endpoint

Running the following command:

```bash
curl http://localhost:8080/v1/verba
```

might return a response similar to:

```json
{
  "classes": [
    {
      "class": "VERBA_Example_Class",
      "description": "Example description",
      "otherField": "value"
    },
    {
      "class": "VERBA_Sample",
      "description": "Another example",
      "otherField": "value"
    }
  ]
}
```

### 2. Configuring mcp-openapi-proxy

Using the MCP ecosystem configuration, you can instruct mcp-openapi-proxy to fetch the above endpoint, filter for classes starting with `VERBA_`, and prepend a prefix to tool names. For example:

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
                "OPENAPI_SPEC_URL": "http://localhost:8080/v1/verba",
                "TOOL_BLACKLIST": "delete_document,reset"
            }
        }
    }
}
```

### 3. Resulting Tools

With the above settings, the server will map the discovered classes to MCP tools. The resulting tools might look like:

```json
[
    {
        "name": "api_query",
        "description": "Tool for /api/query: ..."
    },
    {
        "name": "api_get_document",
        "description": "Tool for /api/get_document: ..."
    },
    {
        "name": "api_get_content",
        "description": "Tool for /api/get_content: ..."
    },
    {
        "name": "api_get_meta",
        "description": "Tool for /api/get_meta: ..."
    },
    "..."
]
```

### 4. Visual Verification

**Screenshot Placeholder:**  
[Insert screenshot of the registered tools in the Claude Desktop app here]

## Troubleshooting

- **Missing OPENAPI_SPEC_URL:** Verify that the `OPENAPI_SPEC_URL` environment variable is set and points to a valid OpenAPI JSON file.
- **Invalid OpenAPI Spec:** Ensure the JSON specification complies with the OpenAPI standard.
- **Filtering Issues:** Check that `TOOL_WHITELIST` is correctly defined to filter the desired classes.
- **Logging:** Consult the logs (as defined by `MCP_OPENAPI_LOGFILE_PATH`) for debugging information.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
