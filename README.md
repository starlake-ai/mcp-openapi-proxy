# mcp-any-openapi

`mcp-any-openapi` is a Python package implementing a Model Context Protocol (MCP) server that dynamically exposes REST APIs defined by OpenAPI specifications as MCP tools. This allows you to easily integrate any OpenAPI-described API into MCP-based workflows.

It supports two operation modes:

- **LowLevel Mode (Default)**: Dynamically registers tools for all API endpoints defined in a given OpenAPI specification.
- **FastMCP Mode (Simple Mode)**: Provides a simplified mode for exposing specific pre-configured API endpoints as tools. (If you implement FastMCP mode with specific tools)

<p align="center">
[/* You can add a relevant image or diagram here if you have one */]
</p>

---

## Features

- **Dynamic Tool Generation**: LowLevel mode automatically creates MCP tools from OpenAPI endpoint definitions.
- **Simple Mode Option**: FastMCP mode (if implemented) allows for simpler, static tool configurations.
- **OpenAPI Specification Support**:  Works with OpenAPI v3 specifications (and potentially v2, depending on your parsing).
- **Flexible Filtering**:  (If you implement filtering) Allows filtering OpenAPI endpoints to be exposed as tools based on criteria like tags, paths, methods, etc.
- **MCP Integration**:  Seamlessly integrates into MCP ecosystems, allowing you to invoke REST APIs as tools within MCP-compatible clients.

---

## Installation

Confirm you can run the server directly from the GitHub repository using uvx:

uvx --from git+https://github.com/matthewhand/mcp-any-openapi mcp-any-openapi

Adding to MCP Ecosystem (mcpServers Configuration)
You can integrate mcp-any-openapi into your MCP ecosystem by adding it to the mcpServers configuration. Example:

{
    "mcpServers": {
        "mcp-any-openapi": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/matthewhand/mcp-any-openapi", 
                "mcp-any-openapi"
            ],
            "env": {
                "OPENAPI_SPEC_URL": "${OPENAPI_SPEC_URL}" 
            }
        }
    }
}
Use code with caution.

Modes of Operation
1. FastMCP Mode (Simple Mode) (If implemented)
Enabled by setting OPENAPI_SIMPLE_MODE=true. This mode:

Exposes a pre-defined set of tools for specific OpenAPI endpoints. (Describe the tools you will create in FastMCP mode)

Requires configuration via specific environment variables to define the tools and their corresponding OpenAPI operations.

<p align="center">
[/* Image or diagram for FastMCP mode if applicable */]
</p>
2. LowLevel Mode (OPENAPI_SIMPLE_MODE=False or not set - Default)
Features:

Dynamically registers all valid API endpoints from the provided OpenAPI specification as separate tools.

Tool names are derived from the OpenAPI path and method (normalized).

Tool descriptions are generated from OpenAPI operation summaries and descriptions.

Example:

A tool like get_pet_petId(petId: integer) -> string might be dynamically created for a GET /pet/{petId} endpoint.

Environment Variables
General
OPENAPI_SPEC_URL: URL to the OpenAPI specification JSON file (required).

MCP_API_PREFIX: Prefix for the generated MCP tool names (default: any_openapi).

MCP_OPENAPI_LOGFILE_PATH: Path to the log file for mcp-any-openapi.

FastMCP Mode (OPENAPI_SIMPLE_MODE=true) (If implemented)
OPENAPI_SIMPLE_MODE=true: Enables FastMCP/Simple mode.

LowLevel Mode (Default)
(Potentially add environment variables for filtering if you implement it, like OPENAPI_TAG_WHITELIST, OPENAPI_PATH_BLACKLIST, etc.)

Filtering OpenAPI Endpoints (If implemented)
(Describe your filtering mechanisms here, if you implement them. For example, filtering by tags, paths, methods using environment variables)

Security
Protect OpenAPI Access: Ensure the OpenAPI specification URL and any API keys (if used by the OpenAPI) are kept secure.

Environment Configuration: Use .env files or environment variables for sensitive configurations and API keys.

Troubleshooting
Missing OPENAPI_SPEC_URL: Ensure OPENAPI_SPEC_URL environment variable is set and points to a valid OpenAPI JSON file.

Invalid OpenAPI Spec: If the server fails to start or tool registration fails, check if the OpenAPI specification is valid JSON and conforms to the OpenAPI standard.

Connection Errors: Verify that the OPENAPI_SPEC_URL is accessible and that there are no network issues preventing fetching the specification.

Tool Invocation Errors: If tool invocations fail, check the server logs for detailed error messages and verify the API request parameters and format.

License
This project is licensed under the MIT License. See the LICENSE file for details.

