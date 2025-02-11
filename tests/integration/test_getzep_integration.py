import os
import requests
import pytest
import json

GETZEP_SWAGGER_URL = "https://getzep.github.io/zep/swagger.json"

def test_getzep_swagger_and_tools():
    # Fetch the GetZep Swagger JSON specification
    response = requests.get(GETZEP_SWAGGER_URL)
    assert response.status_code == 200, f"GET {GETZEP_SWAGGER_URL} failed: {response.text}"
    
    spec = response.json()
    # Validate that the spec is a proper Swagger/OpenAPI 2.0 document
    assert "swagger" in spec, "No 'swagger' key found; invalid swagger specification?"
    # Ensure there are endpoints defined
    assert "paths" in spec and spec["paths"], "No paths found in swagger specification"
    
    print("DEBUG: GetZep swagger spec version:", spec.get("swagger"))
    for path, details in spec["paths"].items():
        print(f"DEBUG: Found endpoint: {path}")
        break

    # Simulate tool creation by setting the environment variable used by FastMCP
    os.environ["OPENAPI_SPEC_URL"] = GETZEP_SWAGGER_URL
    from mcp_openapi_proxy.server_fastmcp import list_functions
    tools_json = list_functions()
    tools = json.loads(tools_json)
    # Confirm that at least one tool was created
    assert isinstance(tools, list) and len(tools) > 0, "No tools were created from GetZep spec"
    print("DEBUG: Tools created from GetZep spec:", tools[0])