# mcp-openapi-proxy

**mcp-openapi-proxy** is a Python package that implements a Model Context Protocol (MCP) server, designed to dynamically expose REST APIs—defined by OpenAPI specifications—as MCP tools. This facilitates seamless integration of OpenAPI-described APIs into MCP-based workflows.

## Overview

The package offers two operational modes:

- **Low-Level Mode (Default):** Dynamically registers tools corresponding to all API endpoints specified in an OpenAPI document (e.g., `/chat/completions` becomes `chat_completions()`).
- **FastMCP Mode (Simple Mode):** Provides a streamlined approach, exposing a predefined set of tools (e.g., `list_functions()` and `call_functions()`) based on static configurations.

## Features

- **Dynamic Tool Generation:** Automatically creates MCP tools from OpenAPI endpoint definitions.
- **Simple Mode Option:** Offers a static configuration alternative via FastMCP mode.
- **OpenAPI Specification Support:** Compatible with OpenAPI v3, with potential support for v2.
- **Flexible Filtering:** Allows endpoint filtering through whitelisting by paths or other criteria.
- **MCP Integration:** Seamlessly integrates with MCP ecosystems for invoking REST APIs as tools.

## Installation

Install the package directly from PyPI using the following command:

```bash
uvx mcp-openapi-proxy
```

### MCP Ecosystem Integration

To incorporate **mcp-openapi-proxy** into your MCP ecosystem, configure it within your `mcpServers` settings. Below is a generic example:

```json
{
    "mcpServers": {
        "mcp-openapi-proxy": {
            "command": "uvx",
            "args": ["mcp-openapi-proxy"],
            "env": {
                "OPENAPI_SPEC_URL": "${OPENAPI_SPEC_URL}",
                "API_AUTH_BEARER": "",
                "TOOL_WHITELIST": "",
                "TOOL_NAME_PREFIX": ""
            }
        }
    }
}
```

Refer to the **Examples** section below for practical configurations tailored to specific APIs.

## Modes of Operation

### FastMCP Mode (Simple Mode)

- **Enabled by:** Setting the environment variable `OPENAPI_SIMPLE_MODE=true`.
- **Description:** Exposes a fixed set of tools derived from specific OpenAPI endpoints, as defined in the code.
- **Configuration:** Relies on environment variables to specify tool behavior.

### Low-Level Mode (Default)

- **Description:** Automatically registers all valid API endpoints from the provided OpenAPI specification as individual tools.
- **Tool Naming:** Derives tool names from normalized OpenAPI paths and methods.
- **Behavior:** Generates tool descriptions from OpenAPI operation summaries and descriptions.

## Environment Variables

- `OPENAPI_SPEC_URL`: (Required) The URL to the OpenAPI specification JSON file.
- `OPENAPI_LOGFILE_PATH`: (Optional) Specifies the log file path.
- `OPENAPI_SIMPLE_MODE`: (Optional) Set to `true` to enable FastMCP mode.
- `TOOL_WHITELIST`: (Optional) A comma-separated list of endpoint paths to expose as tools.
- `TOOL_NAME_PREFIX`: (Optional) A prefix to prepend to all tool names.

## Examples

This section will expand incrementally with new examples added periodically. Each example demonstrates how to configure **mcp-openapi-proxy** for a specific API, starting with GetZep, which leverages a free cloud API accessible with a GetZep API key.

### GetZep Example

GetZep provides a free cloud API for memory management, making it an excellent starting point for testing. Obtain an API key from [GetZep's documentation](https://docs.getzep.com/).

#### 1. Verify the OpenAPI Specification

Retrieve the GetZep OpenAPI specification:

```bash
curl https://raw.githubusercontent.com/matthewhand/mcp-openapi-proxy/refs/heads/main/examples/getzep.swagger.json
```

Ensure the response is a valid OpenAPI JSON document.

#### 2. Configure mcp-openapi-proxy for GetZep

Update your MCP ecosystem configuration as follows:

```json
{
    "mcpServers": {
        "getzep": {
            "command": "uvx",
            "args": ["mcp-openapi-proxy"],
            "env": {
                "OPENAPI_SPEC_URL": "https://raw.githubusercontent.com/matthewhand/mcp-openapi-proxy/refs/heads/main/examples/getzep.swagger.json",
                "TOOL_WHITELIST": "/sessions,/sessions/{sessionId},/sessions-ordered,/sessions/{sessionId}/memory,/sessions/{sessionId}/messages",
                "API_AUTH_BEARER": "<your_getzep_api_key>",
                "API_AUTH_TYPE": "Api-Key",
                "SERVER_URL_OVERRIDE": "https://api.getzep.com",
                "TOOL_NAME_PREFIX": "getzep"
            }
        }
    }
}
```

- **OPENAPI_SPEC_URL**: Points to the GetZep Swagger specification.
- **TOOL_WHITELIST**: Limits tools to specific endpoints (e.g., `/sessions`, `/sessions/{sessionId}/memory`).
- **API_AUTH_BEARER**: Your GetZep API key (replace `<your_getzep_api_key>`).
- **API_AUTH_TYPE**: Specifies `Api-Key` for GetZep’s authentication.
- **SERVER_URL_OVERRIDE**: Sets the base URL to GetZep’s API.
- **TOOL_NAME_PREFIX**: Prepends `getzep` to tool names (e.g., `getzep_sessions`).

#### 3. Resulting Tools

This configuration generates tools such as:

```json
[
    {"name": "getzep_sessions", "description": "List all sessions"},
    {"name": "getzep_sessions_sessionid", "description": "Get a specific session by ID"},
    {"name": "getzep_sessions_ordered", "description": "List sessions in order"},
    {"name": "getzep_sessions_sessionid_memory", "description": "Retrieve memory for a session"},
    {"name": "getzep_sessions_sessionid_messages", "description": "Get messages for a session"}
]
```

#### 4. Testing

Run the server with `uvx` to verify:

```bash
OPENAPI_SPEC_URL="https://raw.githubusercontent.com/matthewhand/mcp-openapi-proxy/refs/heads/main/examples/getzep.swagger.json" API_AUTH_BEARER="<your_getzep_api_key>" uvx mcp-openapi-proxy
```

Additional examples (e.g., OpenWebUI, Fly.io) will be added incrementally to this section over time.

## Troubleshooting

- **Missing OPENAPI_SPEC_URL:** Ensure the environment variable is set to a valid OpenAPI JSON URL.
- **Invalid Specification:** Confirm the OpenAPI document adheres to the standard.
- **Tool Filtering Issues:** Verify `TOOL_WHITELIST` correctly specifies desired endpoints.
- **Logging:** Check logs at `OPENAPI_LOGFILE_PATH` (if set) for diagnostic details.
- **Installation Verification:** Test the server directly:

```bash
uvx mcp-openapi-proxy
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.