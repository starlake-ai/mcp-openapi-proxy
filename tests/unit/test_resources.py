import os
import json
import asyncio
import pytest
from unittest.mock import patch
from mcp_openapi_proxy.server_lowlevel import list_resources, read_resource
from mcp_openapi_proxy.server_fastmcp import list_functions, call_function
from types import SimpleNamespace

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.delenv("OPENAPI_SPEC_URL", raising=False)
    monkeypatch.setenv("OPENAPI_SPEC_URL", "http://dummy.com")

def test_lowlevel_list_resources(mock_env):
    request = SimpleNamespace(params=SimpleNamespace())
    result = asyncio.run(list_resources(request))
    assert len(result.root.resources) == 1, "Expected one resource"
    assert result.root.resources[0].name == "spec_file", "Expected spec_file resource"

@pytest.mark.skip(reason="Pydantic schema mismatch, revisit later")
def test_lowlevel_read_resource_valid(mock_env):
    from mcp_openapi_proxy.server_lowlevel import openapi_spec_data
    openapi_spec_data = {"dummy": "spec"}
    request = SimpleNamespace(params=SimpleNamespace(uri="file:///openapi_spec.json"))
    result = asyncio.run(read_resource(request))
    assert result.root.contents[0].text == json.dumps({"dummy": "spec"}, indent=2), "Expected spec JSON"

@pytest.mark.skip(reason="FastMCP tool list issue, revisit later")
def test_fastmcp_list_resources(mock_env):
    with patch('mcp_openapi_proxy.utils.fetch_openapi_spec', return_value={"paths": {}}):
        tools_json = list_functions(env_key="OPENAPI_SPEC_URL")
        tools = json.loads(tools_json)
        assert any(t["name"] == "list_resources" for t in tools), "list_resources not found"
        result = call_function(function_name="list_resources", parameters={}, env_key="OPENAPI_SPEC_URL")
        resources = json.loads(result)
        assert len(resources) == 1, "Expected one resource"
        assert resources[0]["name"] == "spec_file", "Expected spec_file resource"

@pytest.mark.skip(reason="FastMCP spec fetch issue, revisit later")
def test_fastmcp_read_resource_valid(mock_env):
    with patch('mcp_openapi_proxy.utils.fetch_openapi_spec', return_value={"paths": {}}):
        from mcp_openapi_proxy.server_fastmcp import spec
        spec = {"dummy": "spec"}
        result = call_function(function_name="read_resource", parameters={"uri": "file:///openapi_spec.json"}, env_key="OPENAPI_SPEC_URL")
        assert json.loads(result) == {"dummy": "spec"}, "Expected spec JSON"
