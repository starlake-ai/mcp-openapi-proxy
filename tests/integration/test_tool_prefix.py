"""
Integration test for tool name generation from OpenAPI spec.
"""

import os
import json
import pytest
from mcp_openapi_proxy.server_fastmcp import list_functions

@pytest.mark.integration
def test_tool_name_mapping(reset_env_and_module):
    """Test that tool names are correctly generated from OpenAPI spec."""
    env_key = reset_env_and_module
    spec_url = "https://petstore.swagger.io/v2/swagger.json"
    os.environ[env_key] = spec_url
    os.environ["DEBUG"] = "true"

    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    assert isinstance(tools, list), "Tools should be a list"
    assert len(tools) > 0, "No tools generated from spec"
    for tool in tools:
        name = tool["name"]
        assert name.startswith(("get_", "post_", "put_", "delete_")), \
            f"Tool name {name} should start with HTTP method prefix"
        assert name.islower(), f"Tool name {name} should be lowercase"
        assert " " not in name, f"Tool name {name} should have no spaces"
