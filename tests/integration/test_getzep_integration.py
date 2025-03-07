import os
import requests
import pytest
import json
from dotenv import load_dotenv  # Added this, ya clever dick

# Load environment variables from .env file right off the bat
load_dotenv()  # Suck up yer secrets, ya paranoid bastard!

GETZEP_SWAGGER_URL = "https://getzep.github.io/zep/swagger.json"

def test_getzep_swagger_and_tools():
    # Skip test if required environment variable is missing
    getzep_api_key = os.getenv("GETZEP_API_KEY")
    if not getzep_api_key:
        pytest.skip("GETZEP_API_KEY not set in .env, skipping test.")

    # Fetch and validate OpenAPI/Swagger spec
    response = requests.get(GETZEP_SWAGGER_URL)
    assert response.status_code == 200, f"GET {GETZEP_SWAGGER_URL} failed: {response.text}"
    spec = response.json()

    # Validate OpenAPI/Swagger structure
    assert "swagger" in spec or "openapi" in spec, "Invalid OpenAPI/Swagger document (missing version key)"
    assert "paths" in spec and spec["paths"], "No API paths found in specification"

    print(f"DEBUG: GetZep spec version: {spec.get('swagger') or spec.get('openapi')}")
    print(f"DEBUG: First endpoint found: {next(iter(spec['paths'] or {}), 'none')}")
    print(f"DEBUG: Total paths in spec: {len(spec.get('paths', {}))}")

    # Configure server environment variables
    os.environ["OPENAPI_SPEC_URL"] = GETZEP_SWAGGER_URL
    whitelist = ",".join(spec["paths"].keys())  # Allow all paths for testing, ya twat
    os.environ["TOOL_WHITELIST"] = whitelist
    os.environ["API_AUTH_BEARER"] = getzep_api_key
    print(f"DEBUG: TOOL_WHITELIST set to: {whitelist}")

    # Test tool generation
    from mcp_openapi_proxy.server_fastmcp import list_functions, call_function  # Added call_function, ya numpty

    tools_json = list_functions()
    print(f"DEBUG: Raw tools_json output: {tools_json}")
    tools = json.loads(tools_json)
    print(f"DEBUG: Parsed tools list: {tools}")
    print(f"DEBUG: Number of tools generated: {len(tools)}")

    # Assert tool creation
    assert isinstance(tools, list), "list_functions returned non-list data"
    assert len(tools) > 0, "No tools were created from GetZep OpenAPI spec"
    
    # Basic tool validation
    first_tool = tools[0]
    assert "name" in first_tool, "Tool definition missing 'name' field"
    assert "path" in first_tool, "Tool definition missing 'path' field"
    
    print(f"DEBUG: First tool created: {json.dumps(first_tool, indent=2)}")
    
    # Test calling a tool with a real API call
    example_tool = next((t for t in tools if t["method"] == "GET"), tools[0])
    result = call_function(function_name=example_tool["name"], parameters={})
    result_data = json.loads(result)
    assert "error" not in result_data, f"Example API call failed: {result_data.get('error', 'No error message')}"
