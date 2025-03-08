# mcp-openapi-proxy

**mcp-openapi-proxy** is a Python package that implements a Model Context Protocol (MCP) server, designed to dynamically expose REST APIs—defined by OpenAPI specifications—as MCP tools. This facilitates seamless integration of OpenAPI-described APIs into MCP-based workflows.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [MCP Ecosystem Integration](#mcp-ecosystem-integration)
- [Modes of Operation](#modes-of-operation)
  - [FastMCP Mode (Simple Mode)](#fastmcp-mode-simple-mode)
  - [Low-Level Mode (Default)](#low-level-mode-default)
- [Environment Variables](#environment-variables)
- [Examples](#examples)
  - [GetZep Example](#getzep-example)
  - [Fly.io Example](#flyio-example)
- [Troubleshooting](#troubleshooting)
- [License](#license)

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
                "API_KEY": "",
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

This section will expand incrementally with new examples added periodically. Each example demonstrates how to configure **mcp-openapi-proxy** for a specific API, starting with GetZep, which leverages a free cloud API accessible with a GetZep API key, and including a simpler Fly.io setup.

### GetZep Example

![image](https://github.com/user-attachments/assets/6ae7f708-9494-41a1-9075-e685f2cd8873)

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
                "TOOL_WHITELIST": "/sessions",
                "API_KEY": "<your_getzep_api_key>",
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
- **API_KEY**: Your GetZep API key (replace `<your_getzep_api_key>`).
- **API_AUTH_TYPE**: Specifies `Api-Key` for GetZep’s authentication.
- **SERVER_URL_OVERRIDE**: Sets the base URL to GetZep’s API.
- **TOOL_NAME_PREFIX**: Prepends `getzep` to tool names (e.g., `getzep_sessions`).

#### 3. Resulting Tools

This configuration generates tools such as:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "post_sessions",
        "description": "Add Session",
        "inputSchema": {
          "type": "object",
          "properties": {},
          "required": [],
          "additionalProperties": false
        }
      },
      {
        "name": "get_sessions",
        "description": "Get Session",
        "inputSchema": {
          "type": "object",
          "properties": {
            "sessionId": {
              "type": "string",
              "description": "Unique identifier of the session"
            }
          },
          "required": ["sessionId"],
          "additionalProperties": false
        }
      },
      {
        "name": "get_sessions-ordered",
        "description": "Get Sessions",
        "inputSchema": {
          "type": "object",
          "properties": {
            "page_number": {
              "type": "integer",
              "description": "Page number for pagination, starting from 1"
            },
            "page_size": {
              "type": "integer",
              "description": "Number of sessions per page"
            },
            "order_by": {
              "type": "string",
              "description": "Field to order results by: created_at, updated_at, user_id, session_id"
            },
            "asc": {
              "type": "boolean",
              "description": "Order direction: true for ascending, false for descending"
            }
          },
          "required": [],
          "additionalProperties": false
        }
      },
      {
        "name": "get_sessions_memory",
        "description": "Get Session Memory",
        "inputSchema": {
          "type": "object",
          "properties": {
            "sessionId": {
              "type": "string",
              "description": "ID of the session to retrieve memory for"
            },
            "lastn": {
              "type": "integer",
              "description": "Number of most recent memory entries to retrieve"
            },
            "minRating": {
              "type": "number",
              "description": "Minimum rating to filter relevant facts"
            }
          },
          "required": ["sessionId"],
          "additionalProperties": false
        }
      },
      {
        "name": "post_sessions_memory",
        "description": "Add Memory to Session",
        "inputSchema": {
          "type": "object",
          "properties": {
            "sessionId": {
              "type": "string",
              "description": "ID of the session to add memory to"
            }
          },
          "required": ["sessionId"],
          "additionalProperties": false
        }
      },
      {
        "name": "delete_sessions_memory",
        "description": "Delete Session",
        "inputSchema": {
          "type": "object",
          "properties": {
            "sessionId": {
              "type": "string",
              "description": "ID of the session to delete"
            }
          },
          "required": ["sessionId"],
          "additionalProperties": false
        }
      },
      {
        "name": "get_sessions_messages",
        "description": "Get Messages for Session",
        "inputSchema": {
          "type": "object",
          "properties": {
            "sessionId": {
              "type": "string",
              "description": "Session ID"
            },
            "limit": {
              "type": "integer",
              "description": "Limit the number of results returned"
            },
            "cursor": {
              "type": "integer",
              "description": "Cursor for pagination"
            }
          },
          "required": ["sessionId"],
          "additionalProperties": false
        }
      },
      {
        "name": "post_sessions_messages_classify",
        "description": "Classify Session",
        "inputSchema": {
          "type": "object",
          "properties": {
            "sessionId": {
              "type": "string",
              "description": "Session ID"
            }
          },
          "required": ["sessionId"],
          "additionalProperties": false
        }
      },
      {
        "name": "get_sessions_messages",
        "description": "Get Message",
        "inputSchema": {
          "type": "object",
          "properties": {
            "sessionId": {
              "type": "string",
              "description": "Soon to be deprecated, not needed"
            },
            "messageUUID": {
              "type": "string",
              "description": "UUID of the message"
            }
          },
          "required": ["sessionId", "messageUUID"],
          "additionalProperties": false
        }
      }
    ]
  }
}
```

#### 4. Testing

Run the server with `uvx` to verify:

```bash
OPENAPI_SPEC_URL="https://raw.githubusercontent.com/matthewhand/mcp-openapi-proxy/refs/heads/main/examples/getzep.swagger.json" API_KEY="<your_getzep_api_key>" uvx mcp-openapi-proxy
```

### Fly.io Example

![image](https://github.com/user-attachments/assets/18899803-be36-4efc-942c-566097d69300)

Fly.io provides a simple API for managing machines, ideal for testing with a minimal setup. Obtain an API token from [Fly.io documentation](https://fly.io/docs/hands-on/install-flyctl/).

#### 1. Verify the OpenAPI Specification

Retrieve the Fly.io OpenAPI specification:

```bash
curl https://raw.githubusercontent.com/abhiaagarwal/peristera/refs/heads/main/fly-machines-gen/fixed_spec.json
```

Ensure the response is a valid OpenAPI JSON document.

#### 2. Configure mcp-openapi-proxy for Fly.io

Update your MCP ecosystem configuration as follows:

```json
{
    "mcpServers": {
        "flyio": {
            "command": "uvx",
            "args": ["mcp-openapi-proxy"],
            "env": {
                "OPENAPI_SPEC_URL": "https://raw.githubusercontent.com/abhiaagarwal/peristera/refs/heads/main/fly-machines-gen/fixed_spec.json",
                "API_KEY": "<your_flyio_token_here>"
            }
        }
    }
}
```

- **OPENAPI_SPEC_URL**: Points to the Fly.io OpenAPI specification.
- **SERVER_URL_OVERRIDE**: Specifies the Fly.io API endpoints (public and internal).
- **API_KEY**: Your Fly.io API token (replace `<your_flyio_token_here>`). Alternatively, you can find the API key in `~/.fly/config.yml` under the `access_token` field—simply copy that value as the `API_KEY` for a seamless setup.
- **Note**: The `access_token` in `~/.fly/config.yml` is pre-configured when you set up Fly.io, making it a quick and easy option.

#### 3. Resulting Tools

This configuration generates tools based on the Fly.io spec (e.g., machine management endpoints). Example tools might include:

- `get_machines` (for listing machines).
- `post_machines` (for creating machines).

Run `list_tools` to see the exact set.

#### 4. Testing

Run the server with `uvx` to verify:

```bash
OPENAPI_SPEC_URL="https://raw.githubusercontent.com/abhiaagarwal/peristera/refs/heads/main/fly-machines-gen/fixed_spec.json" API_KEY="<your_flyio_token_here>" uvx mcp-openapi-proxy
```

Additional examples (e.g., OpenWebUI) will be added incrementally to this section over time.

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
