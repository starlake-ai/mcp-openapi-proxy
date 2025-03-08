"""
Integration tests for Render.com API via mcp-openapi-proxy, FastMCP mode.
Needs RENDER_API_KEY in .env to run.
"""

import os
import json
import pytest
from dotenv import load_dotenv
from mcp_openapi_proxy.utils import fetch_openapi_spec
from mcp_openapi_proxy.server_fastmcp import mcp, list_functions, call_function

# Load .env file from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

@pytest.mark.integration
def test_render_services_list(reset_env_and_module):
    """Test Render /services endpoint with RENDER_API_KEY."""
    env_key = reset_env_and_module
    render_api_key = os.getenv("RENDER_API_KEY")
    spec_url = os.getenv("RENDER_SPEC_URL", "https://api-docs.render.com/openapi/6140fb3daeae351056086186")
    tool_prefix = os.getenv("TOOL_NAME_PREFIX", "render_")
    print(f"🍺 DEBUG: RENDER_API_KEY: {render_api_key if render_api_key else 'Not set'}")
    if not render_api_key or "your-" in render_api_key:
        print("🍻 DEBUG: Skipping due to missing or placeholder RENDER_API_KEY")
        pytest.skip("RENDER_API_KEY missing or placeholder—set it in .env, ya bloody galah!")

    # Fetch the spec
    print(f"🍆 DEBUG: Fetching spec from {spec_url}")
    spec = fetch_openapi_spec(spec_url)
    assert spec, f"Failed to fetch spec from {spec_url}"
    assert "paths" in spec, "No 'paths' key in spec"
    assert "/services" in spec["paths"], "No /services endpoint in spec"
    assert "servers" in spec or "host" in spec, "No servers or host defined in spec"

    # Set env vars
    os.environ[env_key] = spec_url
    os.environ["API_KEY"] = render_api_key
    os.environ["API_KEY_JMESPATH"] = ""  # Render uses header auth, no JMESPath
    os.environ["API_AUTH_TYPE"] = "Bearer"  # Render expects Bearer token
    os.environ["TOOL_NAME_PREFIX"] = tool_prefix
    os.environ["TOOL_WHITELIST"] = "/services,/deployments"
    os.environ["DEBUG"] = "true"
    print(f"🍍 DEBUG: API_KEY set to: {os.environ['API_KEY'][:5]}...")

    # Verify tools
    print("🍑 DEBUG: Listing available tools")
    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    assert isinstance(tools, list), f"Tools response ain’t a list: {tools_json}"
    assert tools, f"No tools generated: {tools_json}"
    tool_name = f"{tool_prefix}get_services"
    assert any(t["name"] == tool_name for t in tools), f"Tool {tool_name} not found, ya numpty!"

    # Call /services
    print("🍌 DEBUG: Calling get_services")
    response_json = call_function(
        function_name=tool_name,
        parameters={},  # No params needed for basic list
        env_key=env_key
    )
    print(f"🍒 DEBUG: Raw response: {response_json}")
    try:
        response = json.loads(response_json)
        if isinstance(response, dict) and "error" in response:
            print(f"🍷 DEBUG: Error hit: {response['error']}")
            if "401" in response["error"]:
                assert False, "RENDER_API_KEY is invalid—check ya token, mate!"
            assert False, f"Render API shat itself: {response_json}"
        assert isinstance(response, list), f"Response ain’t a list: {response_json}"
        assert len(response) > 0, "No services found—ya sure ya got any deployed, ya lazy sod?"
        print(f"🍉 DEBUG: Found {len(response)} services—bloody ripper!")
    except json.JSONDecodeError:
        assert False, f"Response ain’t valid JSON: {response_json}"

