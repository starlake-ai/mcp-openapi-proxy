import os
import requests
import pytest
import json
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Local V2 Swagger file path—please adjust if incorrect
GETZEP_SWAGGER_URL = "file:///home/matthewh/mcp-openapi-proxy/examples/getzep.swagger.json"

def test_getzep_swagger_and_tools():
    # Skip the test if the API key is not provided
    getzep_api_key = os.getenv("GETZEP_API_KEY")
    if not getzep_api_key:
        pytest.skip("GETZEP_API_KEY not set in .env, skipping test.")

    # Read the local Swagger file directly
    spec_path = GETZEP_SWAGGER_URL.replace("file://", "")
    with open(spec_path, 'r') as f:
        spec = json.load(f)

    # Validate the OpenAPI/Swagger structure
    assert "swagger" in spec or "openapi" in spec, "Invalid OpenAPI/Swagger document: missing version key."
    assert "paths" in spec and spec["paths"], "No API paths found in the specification."

    print(f"DEBUG: GetZep spec version: {spec.get('swagger') or spec.get('openapi')}")
    print(f"DEBUG: First endpoint found: {next(iter(spec['paths'] or {}), 'none')}")
    print(f"DEBUG: Total paths in spec: {len(spec.get('paths', {}))}")
    print(f"DEBUG: Base path from spec: {spec.get('basePath', 'none')}")

    # Configure server environment variables
    os.environ["OPENAPI_SPEC_URL"] = GETZEP_SWAGGER_URL
    whitelist = ",".join(spec["paths"].keys())  # Include all paths for testing
    os.environ["TOOL_WHITELIST"] = whitelist
    os.environ["API_AUTH_BEARER"] = getzep_api_key
    os.environ["API_AUTH_TYPE"] = "Api-Key"  # Required for V2
    os.environ["SERVER_URL_OVERRIDE"] = "https://api.getzep.com"  # V2 base URL
    print(f"DEBUG: TOOL_WHITELIST set to: {whitelist}")
    print(f"DEBUG: API_AUTH_TYPE set to: {os.environ['API_AUTH_TYPE']}")
    print(f"DEBUG: SERVER_URL_OVERRIDE set to: {os.environ['SERVER_URL_OVERRIDE']}")

    # Test tool generation
    from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

    tools_json = list_functions()
    print(f"DEBUG: Raw tools_json output: {tools_json}")
    tools = json.loads(tools_json)
    print(f"DEBUG: Parsed tools list: {tools}")
    print(f"DEBUG: Number of tools generated: {len(tools)}")

    # Verify tool creation
    assert isinstance(tools, list), "list_functions returned invalid data (not a list)."
    assert len(tools) > 0, "No tools were generated from the GetZep specification."

    # Validate the first tool
    first_tool = tools[0]
    assert "name" in first_tool, "Tool definition is missing the 'name' field."
    assert "path" in first_tool, "Tool definition is missing the 'path' field."

    print(f"DEBUG: First tool created: {json.dumps(first_tool, indent=2)}")

    # Test an API call using POST /api/v2/sessions
    example_tool = next((t for t in tools if t["name"] == "POST /api/v2/sessions"), tools[0])
    result = call_function(
        function_name=example_tool["name"],
        parameters={"session_id": "test_session_123", "user_id": "test_user_456"}  # Sample test data
    )
    result_data = json.loads(result)
    print(f"DEBUG: API call result: {result_data}")
    assert "error" not in result_data, f"API call failed: {result_data.get('error', 'No error message provided')}"
