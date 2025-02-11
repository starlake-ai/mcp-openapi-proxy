import os
import requests
import pytest
import json

QUIVR_OPENAPI_URL = "https://api.quivr.app/openapi.json"

def test_quivr_openapi_and_tools():
    # Fetch the Quivr OpenAPI JSON specification
    response = requests.get(QUIVR_OPENAPI_URL)
    assert response.status_code == 200, f"GET {QUIVR_OPENAPI_URL} failed: {response.text}"
    
    spec = response.json()
    # Validate that the spec is a proper OpenAPI v3 document by checking the "openapi" key
    assert "openapi" in spec, "No 'openapi' key found; invalid OpenAPI v3 document?"
    # Ensure that API paths are defined
    assert "paths" in spec and spec["paths"], "No paths found in OpenAPI specification"
    
    print("DEBUG: Quivr OpenAPI version:", spec.get("openapi"))
    for path in spec["paths"]:
        print(f"DEBUG: Found endpoint: {path}")
        break

    # Simulate tool creation by configuring the server's environment variable
    os.environ["OPENAPI_SPEC_URL"] = QUIVR_OPENAPI_URL
    from mcp_openapi_proxy.server_fastmcp import list_functions
    tools_json = list_functions()
    tools = json.loads(tools_json)
    # Confirm that at least one tool was created by the server from the Quivr spec
    assert isinstance(tools, list) and len(tools) > 0, "No tools were created from Quivr spec"
    print("DEBUG: Tools created from Quivr spec:", tools[0])