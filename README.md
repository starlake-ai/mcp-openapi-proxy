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
  - [Fly.io Example](#flyio-example)
  - [Slack Example](#slack-example)
  - [GetZep Example](#getzep-example)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

The package offers two operational modes:

- **Low-Level Mode (Default):** Dynamically registers tools corresponding to all API endpoints specified in an OpenAPI document (e.g., `/chat/completions` becomes `chat_completions()`).
- **FastMCP Mode (Simple Mode):** Provides a streamlined approach, exposing a predefined set of tools (e.g., `list_functions()` and `call_function()`) based on static configurations.

## Features

- **Dynamic Tool Generation:** Automatically creates MCP tools from OpenAPI endpoint definitions.
- **Simple Mode Option:** Offers a static configuration alternative via FastMCP mode.
- **OpenAPI Specification Support:** Compatible with OpenAPI v3, with potential support for v2.
- **Flexible Filtering:** Allows endpoint filtering through whitelisting by paths or other criteria.
- **Payload Authentication:** Supports custom authentication via JMESPath expressions (e.g., for APIs like Slack that expect tokens in the payload, not the HTTP header).
- **Header Authentication:** Uses `Bearer` by default for `API_KEY` in the Authorization header, customizable for APIs like Fly.io requiring `Api-Key`.
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
                "TOOL_NAME_PREFIX": "",
                "API_KEY_JMESPATH": "",
                "API_AUTH_TYPE": ""
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

- `OPENAPI_SPEC_URL`: (Required) The URL to the OpenAPI specification JSON file (e.g., `https://example.com/spec.json` or `file:///path/to/local/spec.json`).
- `OPENAPI_LOGFILE_PATH`: (Optional) Specifies the log file path.
- `OPENAPI_SIMPLE_MODE`: (Optional) Set to `true` to enable FastMCP mode.
- `TOOL_WHITELIST`: (Optional) A comma-separated list of endpoint paths to expose as tools.
- `TOOL_NAME_PREFIX`: (Optional) A prefix to prepend to all tool names.
- `API_KEY`: (Optional) Authentication token for the API, sent as `Bearer <API_KEY>` in the Authorization header by default.
- `API_KEY_JMESPATH`: (Optional) JMESPath expression to map `API_KEY` into request parameters (e.g., `query.token` for Slack).
- `API_AUTH_TYPE`: (Optional) Overrides the default `Bearer` Authorization header type (e.g., `Api-Key` for Fly.io).

## Examples

This section provides examples to demonstrate configuration simplicity, authentication flexibility, and detailed tool generation.

### Fly.io Example

![image](https://github.com/user-attachments/assets/18899803-be36-4efc-942c-566097d69300)

Fly.io provides a simple API for managing machines, making it an ideal starting point. Obtain an API token from [Fly.io documentation](https://fly.io/docs/hands-on/install-flyctl/).

#### 1. Verify the OpenAPI Specification

Retrieve the Fly.io OpenAPI specification:

```bash
curl https://raw.githubusercontent.com/abhiaagarwal/peristera/refs/heads/main/fly-machines-gen/fixed_spec.json
```

Ensure the response is a valid OpenAPI JSON document.

#### 2. Configure mcp-openapi-proxy for Fly.io

Update your MCP ecosystem configuration:

```json
{
    "mcpServers": {
        "flyio": {
            "command": "uvx",
            "args": ["mcp-openapi-proxy"],
            "env": {
                "OPENAPI_SPEC_URL": "https://raw.githubusercontent.com/abhiaagarwal/peristera/refs/heads/main/fly-machines-gen/fixed_spec.json",
                "API_KEY": "<your_flyio_token_here>",
                "API_AUTH_TYPE": "Api-Key"
            }
        }
    }
}
```

- **OPENAPI_SPEC_URL**: Points to the Fly.io OpenAPI specification.
- **API_KEY**: Your Fly.io API token (replace `<your_flyio_token_here>`). Find it in `~/.fly/config.yml` under `access_token`.
- **API_AUTH_TYPE**: Set to `Api-Key` for Fly.io’s header-based authentication (overrides default `Bearer`).

#### 3. Resulting Tools

This generates tools like:
- `get_machines` (lists machines).
- `post_machines` (creates machines).

Run `list_functions` in FastMCP mode to see the full set.

#### 4. Testing

Verify with:

```bash
OPENAPI_SPEC_URL="https://raw.githubusercontent.com/abhiaagarwal/peristera/refs/heads/main/fly-machines-gen/fixed_spec.json" API_KEY="<your_flyio_token_here>" API_AUTH_TYPE="Api-Key" uvx mcp-openapi-proxy
```

### Slack Example

![image](https://github.com/user-attachments/assets/6ae7f708-9494-41a1-9075-e685f2cd8873)

Slack’s API showcases payload-based authentication with JMESPath. Obtain a bot token from [Slack API documentation](https://api.slack.com/authentication/token-types#bot).

#### 1. Verify the OpenAPI Specification

Retrieve the Slack OpenAPI specification:

```bash
curl https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json
```

Ensure it’s a valid OpenAPI JSON document.

#### 2. Configure mcp-openapi-proxy for Slack

Update your configuration:

```json
{
    "mcpServers": {
        "slack": {
            "command": "uvx",
            "args": ["mcp-openapi-proxy"],
            "env": {
                "OPENAPI_SPEC_URL": "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json",
                "SERVER_URL_OVERRIDE": "https://slack.com/api",
                "TOOL_WHITELIST": "/chat,/bots,/conversations,/reminders,/files",
                "API_KEY": "<your_slack_bot_token>",
                "API_KEY_JMESPATH": "query.token",
                "TOOL_NAME_PREFIX": "slack_"
            }
        }
    }
}
```

- **OPENAPI_SPEC_URL**: Slack’s OpenAPI spec.
- **SERVER_URL_OVERRIDE**: Slack’s API base URL.
- **TOOL_WHITELIST**: Limits tools to specific endpoint groups.
- **API_KEY**: Your Slack bot token (e.g., `xoxb-...`).
- **API_KEY_JMESPATH**: Maps `API_KEY` to `query.token`, overwriting any existing `token` in the payload.
- **TOOL_NAME_PREFIX**: Adds `slack_` to tool names (e.g., `slack_post_chat_postmessage`).

#### 3. Resulting Tools

Example tools in FastMCP mode:
- `slack_post_chat_postmessage`: Posts a message to a channel.
- `slack_get_users_info`: Retrieves user information.

#### 4. Testing

Test with:

```bash
OPENAPI_SPEC_URL="https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json" API_KEY="<your_slack_bot_token>" API_KEY_JMESPATH="query.token" uvx mcp-openapi-proxy
```

Call `slack_post_chat_postmessage` with `{"channel": "C12345678", "text": "Hello from MCP!"}` to post to a channel your bot is in.

### GetZep Example

![image](https://github.com/user-attachments/assets/6ae7f708-9494-41a1-9075-e685f2cd8873)

GetZep offers a free cloud API for memory management with detailed endpoints. Notably, GetZep did not originally provide an OpenAPI specification. Thanks to the efforts of Matthew Hand, an OpenAPI spec was generated by converting their documentation using a chatbot and is hosted on GitHub for convenience. Users can also generate their own specs for any REST API and use a local file path (e.g., `file:///path/to/spec.json`). Obtain an API key from [GetZep's documentation](https://docs.getzep.com/).

#### 1. Verify the OpenAPI Specification

Retrieve the community-generated GetZep OpenAPI specification:

```bash
curl https://raw.githubusercontent.com/matthewhand/mcp-openapi-proxy/refs/heads/main/examples/getzep.swagger.json
```

Ensure it’s a valid OpenAPI JSON document. Alternatively, generate your own spec and use `file://` to point to a local file.

#### 2. Configure mcp-openapi-proxy for GetZep

Update your configuration:

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
                "TOOL_NAME_PREFIX": "getzep_"
            }
        }
    }
}
```

- **OPENAPI_SPEC_URL**: Points to Matthew Hand’s community-generated GetZep Swagger spec (or use `file:///path/to/your/spec.json` for a local file).
- **TOOL_WHITELIST**: Limits to `/sessions` endpoints.
- **API_KEY**: Your GetZep API key.
- **API_AUTH_TYPE**: Uses `Api-Key` for header-based authentication (overrides default `Bearer`).
- **SERVER_URL_OVERRIDE**: GetZep’s API base URL.
- **TOOL_NAME_PREFIX**: Prepends `getzep_` to tools.

#### 3. Resulting Tools

Example tools:
- `getzep_post_sessions`: Adds a session.
- `getzep_get_sessions_memory`: Retrieves session memory.

Full list (abbreviated):
```json
{
  "tools": [
    {
      "name": "getzep_post_sessions",
      "description": "Add Session",
      "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
      "name": "getzep_get_sessions_memory",
      "description": "Get Session Memory",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sessionId": {"type": "string", "description": "ID of the session"},
          "lastn": {"type": "integer", "description": "Number of recent entries"}
        },
        "required": ["sessionId"]
      }
    }
  ]
}
```

#### 4. Testing

Verify with the hosted spec:

```bash
OPENAPI_SPEC_URL="https://raw.githubusercontent.com/matthewhand/mcp-openapi-proxy/refs/heads/main/examples/getzep.swagger.json" API_KEY="<your_getzep_api_key>" API_AUTH_TYPE="Api-Key" uvx mcp-openapi-proxy
```

Or with a local spec:

```bash
OPENAPI_SPEC_URL="file:///path/to/your/getzep.swagger.json" API_KEY="<your_getzep_api_key>" API_AUTH_TYPE="Api-Key" uvx mcp-openapi-proxy
```

## Troubleshooting

- **Missing OPENAPI_SPEC_URL:** Ensure it’s set to a valid OpenAPI JSON URL or local file path.
- **Invalid Specification:** Verify the OpenAPI document is standard-compliant.
- **Tool Filtering Issues:** Check `TOOL_WHITELIST` matches desired endpoints.
- **Authentication Errors:** Confirm `API_KEY`, `API_KEY_JMESPATH`, and `API_AUTH_TYPE` are correct.
- **Logging:** Set `DEBUG=true` for detailed output to stderr.
- **Test Server:** Run directly:

```bash
uvx mcp-openapi-proxy
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
