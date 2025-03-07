import os
import pytest
from mcp_openapi_proxy.utils import is_tool_whitelisted

@pytest.fixture(autouse=True)
def reset_tool_whitelist_env(monkeypatch):
    # Clear TOOL_WHITELIST environment variable before each test.
    monkeypatch.delenv('TOOL_WHITELIST', raising=False)

def test_no_whitelist_allows_any_endpoint():
    # When TOOL_WHITELIST is not set, any endpoint should be allowed.
    assert is_tool_whitelisted('/anything') is True
    assert is_tool_whitelisted('/tasks/123') is True

def test_simple_prefix_whitelist(monkeypatch):
    monkeypatch.setenv('TOOL_WHITELIST', '/tasks')
    # Endpoints starting with /tasks should be allowed.
    assert is_tool_whitelisted('/tasks') is True
    assert is_tool_whitelisted('/tasks/123') is True
    # Endpoints not starting with /tasks should not be allowed.
    assert is_tool_whitelisted('/projects') is False

def test_multiple_prefixes(monkeypatch):
    monkeypatch.setenv('TOOL_WHITELIST', '/tasks, /projects')
    # Endpoints that match either prefix should be allowed.
    assert is_tool_whitelisted('/tasks/abc') is True
    assert is_tool_whitelisted('/projects/xyz') is True
    # Endpoints that don't match should not.
    assert is_tool_whitelisted('/collections') is False

def test_placeholder_whitelist(monkeypatch):
    # Test a whitelist entry with a placeholder.
    # For example: /collections/{collection_id} should match URIs like /collections/abc123.
    monkeypatch.setenv('TOOL_WHITELIST', '/collections/{collection_id}')
    assert is_tool_whitelisted('/collections/abc123') is True
    assert is_tool_whitelisted('/collections/') is False
    # Also test case where additional path segments exist.
    assert is_tool_whitelisted('/collections/abc123/items') is True

def test_multiple_placeholders(monkeypatch):
    # Test multiple placeholders: /company/{company_id}/project/{project_id}
    monkeypatch.setenv('TOOL_WHITELIST', '/company/{company_id}/project/{project_id}')
    assert is_tool_whitelisted('/company/comp123/project/proj456') is True
    assert is_tool_whitelisted('/company//project/proj456') is False
    # Test extra characters mismatch.
    assert is_tool_whitelisted('/company/comp123/project') is False