import os
import requests
import pytest
import json
from dotenv import load_dotenv  # Suck it up, ya sneaky prick!

# Load environment variables from .env file, ya paranoid bastard
load_dotenv()

# Local V2 swagger file, ya farkin' legend—adjust path if I got it wrong!
GETZEP_SWAGGER_URL = "file:///home/matthewh/mcp-openapi-proxy/examples/getzep.swagger.json"

def test_getzep_swagger_and_tools():
    # Skip if no API key, ya stingy cunt
    getzep_api_key = os.getenv("GETZEP_API_KEY")
    if not getzep_api_key:
        pytest.skip("GETZEP_API_KEY not set in .env, skipping test like a gutless wonder.")

    # No HTTP fetch for local file, ya twat—just read it directly
    spec_path = GETZEP_SWAGGER_URL.replace("file://", "")
    with open(spec_path, 'r') as f:
        spec = json.load(f)  # Suck it down, ya greedy bastard

    # Validate OpenAPI/Swagger structure, ya nosy prick
    assert "swagger" in spec or "openapi" in spec, "Invalid OpenAPI/Swagger document—where’s the fuckin’ version key?"
    assert "paths" in spec and spec["paths"], "No API paths found—useless as tits on a bull!"

    print(f"🍺 DEBUG: GetZep spec version: {spec.get('swagger') or spec.get('openapi')}")
    print(f"🍺 DEBUG: First endpoint found: {next(iter(spec['paths'] or {}), 'none')}")
    print(f"🍺 DEBUG: Total paths in spec: {len(spec.get('paths', {}))}")
    print(f"🍺 DEBUG: Base path from spec: {spec.get('basePath', 'none')}")

    # Configure server env vars, ya lazy sod
    os.environ["OPENAPI_SPEC_URL"] = GETZEP_SWAGGER_URL
    whitelist = ",".join(spec["paths"].keys())  # All paths for testing, ya greedy cunt
    os.environ["TOOL_WHITELIST"] = whitelist
    os.environ["API_AUTH_BEARER"] = getzep_api_key  # Yer precious key, ya wanker
    os.environ["API_AUTH_TYPE"] = "Api-Key"  # V2 needs Api-Key, ya farkin’ genius!
    os.environ["SERVER_URL_OVERRIDE"] = "https://api.getzep.com"  # V2 base URL, ya bloody ripper!
    print(f"🍺 DEBUG: TOOL_WHITELIST set to: {whitelist}")
    print(f"🍺 DEBUG: API_AUTH_TYPE set to: {os.environ['API_AUTH_TYPE']}")
    print(f"🍺 DEBUG: SERVER_URL_OVERRIDE set to: {os.environ['SERVER_URL_OVERRIDE']}")

    # Test tool generation, ya impatient bastard
    from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

    tools_json = list_functions()
    print(f"🍺 DEBUG: Raw tools_json output: {tools_json}")
    tools = json.loads(tools_json)
    print(f"🍺 DEBUG: Parsed tools list: {tools}")
    print(f"🍺 DEBUG: Number of tools generated: {len(tools)}")

    # Assert tool creation, ya whingin’ prick
    assert isinstance(tools, list), "list_functions shat out non-list data!"
    assert len(tools) > 0, "No tools from GetZep spec—fuckin’ useless!"

    # Basic tool validation, ya nosy cunt
    first_tool = tools[0]
    assert "name" in first_tool, "Tool’s got no ‘name’—what a bloody stitch-up!"
    assert "path" in first_tool, "Tool’s got no ‘path’—fuckin’ hopeless!"

    print(f"🍺 DEBUG: First tool created: {json.dumps(first_tool, indent=2)}")

    # Test a real API call—POST /api/v2/sessions, ya randy bastard
    example_tool = next((t for t in tools if t["name"] == "POST /api/v2/sessions"), tools[0])
    result = call_function(
        function_name=example_tool["name"],
        parameters={"session_id": "test_session_123", "user_id": "test_user_456"}  # Fake shit, ya dodgy prick
    )
    result_data = json.loads(result)
    print(f"🍺 DEBUG: API call result: {result_data}")
    assert "error" not in result_data, f"API call fucked up: {result_data.get('error', 'No error message')}"
