"""
Integration tests for Render.com API via mcp-openapi-proxy, LowLevel mode.
Needs RENDER_API_KEY in .env to run.
"""

import os
import json
import asyncio
import pytest
from dotenv import load_dotenv
from mcp import types
from mcp_openapi_proxy.utils import fetch_openapi_spec, setup_logging
from mcp_openapi_proxy.server_lowlevel import mcp, tools, openapi_spec_data, register_functions

# Load .env file from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

@pytest.mark.asyncio
async def test_render_services_list_lowlevel(reset_env_and_module):
    """Test Render /services endpoint in LowLevel mode with RENDER_API_KEY."""
    env_key = reset_env_and_module
    render_api_key = os.getenv("RENDER_API_KEY")
    spec_url = os.getenv("RENDER_SPEC_URL", "https://api-docs.render.com/openapi/6140fb3daeae351056086186")
    tool_prefix = os.getenv("TOOL_NAME_PREFIX", "render_")
    print(f"🍺 DEBUG: RENDER_API_KEY: {render_api_key if render_api_key else 'Not set'}")
    if not render_api_key or "your-" in render_api_key:
        print("🍻 DEBUG: Skipping due to missing or placeholder RENDER_API_KEY")
        pytest.skip("RENDER_API_KEY missing or placeholder—set it in .env!")

    # Set up environment
    os.environ[env_key] = spec_url
    os.environ["API_KEY"] = render_api_key
    os.environ["API_AUTH_TYPE"] = "Bearer"
    os.environ["TOOL_NAME_PREFIX"] = tool_prefix
    os.environ["TOOL_WHITELIST"] = "/services,/deployments"
    os.environ["DEBUG"] = "true"
    print(f"🍍 DEBUG: API_KEY set to: {os.environ['API_KEY'][:5]}...")

    # Fetch and register spec
    global openapi_spec_data
    logger = setup_logging(debug=True)
    print(f"🍆 DEBUG: Fetching spec from {spec_url}")
    openapi_spec_data = fetch_openapi_spec(spec_url)
    assert openapi_spec_data, f"Failed to fetch spec from {spec_url}"
    assert "paths" in openapi_spec_data, "No 'paths' key in spec"
    assert "/services" in openapi_spec_data["paths"], "No /services endpoint in spec"
    assert "servers" in openapi_spec_data or "host" in openapi_spec_data, "No servers or host defined in spec"

    register_functions(openapi_spec_data)
    assert tools, "No tools registered from spec!"
    tool_name = f"{tool_prefix}get_services"
    assert any(t.name == tool_name for t in tools), f"Tool {tool_name} not found in registered tools!"

    # Simulate CallToolRequest with timeout
    request = types.CallToolRequest(
        params=types.CallToolParams(
            name=tool_name,
            arguments={}
        )
    )
    print("🍌 DEBUG: Dispatching get_services request")
    try:
        result = await asyncio.wait_for(
            mcp.request_handlers[types.CallToolRequest](request),
            timeout=10.0  # 10 seconds max
        )
    except asyncio.TimeoutError:
        logger.error("Request to dispatcher timed out after 10 seconds")
        pytest.fail("Dispatcher request hung—timeout after 10 seconds!")

    assert isinstance(result, types.ServerResult), "Result is not a ServerResult!"
    assert hasattr(result.root, 'content'), "Result root has no content!"

    response_content = result.root.content[0].text
    print(f"🍒 DEBUG: Raw response content: {response_content}")
    try:
        response = json.loads(response_content)
        if isinstance(response, dict) and "error" in response:
            print(f"🍷 DEBUG: Error hit: {response['error']}")
            if "401" in response["error"]:
                pytest.fail("RENDER_API_KEY is invalid—check your token!")
            pytest.fail(f"Render API failed: {response_content}")
        assert isinstance(response, list), f"Response is not a list: {response_content}"
        assert len(response) > 0, "No services found—ensure you have services deployed!"
        print(f"🍉 DEBUG: Found {len(response)} services—success!")
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {response_content}")
