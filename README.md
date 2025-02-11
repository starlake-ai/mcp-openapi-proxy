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
                "OPENAPI_SPEC_URL": "${OPENAPI_SPEC_URL}"
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

## Filtering OpenAPI Endpoints

(If implemented, describe your available filtering options here, such as `OPENAPI_TAG_WHITELIST` or `OPENAPI_PATH_BLACKLIST`.)

## Security

- **OpenAPI Access:** Ensure that the OpenAPI URL and any API keys are kept secure.
- **Configuration:** Use environment variables or `.env` files for sensitive configuration.

## Troubleshooting

- **Missing OPENAPI_SPEC_URL:** Verify that the `OPENAPI_SPEC_URL` environment variable is set and points to a valid OpenAPI JSON file.
- **Invalid OpenAPI Spec:** Check that the OpenAPI specification is a valid JSON and adheres to the OpenAPI standard.
- **Connection Errors:** Confirm that the OpenAPI URL is accessible without network issues.
- **Tool Invocation Issues:** Check server logs for errors during tool invocations and verify input parameters.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
