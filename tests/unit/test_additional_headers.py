import os
import pytest
from mcp_openapi_proxy.utils import get_additional_headers, setup_logging
from mcp_openapi_proxy.server_lowlevel import dispatcher_handler
from mcp_openapi_proxy.server_fastmcp import call_function
import requests
from types import SimpleNamespace

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.delenv("EXTRA_HEADERS", raising=False)
    monkeypatch.delenv("OPENAPI_SPEC_URL", raising=False)
    monkeypatch.setenv("OPENAPI_SPEC_URL", "http://dummy.com")

@pytest.fixture
def mock_requests(monkeypatch):
    def mock_request(method, url, **kwargs):
        class MockResponse:
            def __init__(self):
                self.text = "Mocked response"
            def raise_for_status(self):
                pass
        return MockResponse()
    monkeypatch.setattr(requests, "request", mock_request)

def test_get_additional_headers_empty(mock_env):
    headers = get_additional_headers()
    assert headers == {}, "Expected empty headers when EXTRA_HEADERS not set"

def test_get_additional_headers_single(mock_env):
    os.environ["EXTRA_HEADERS"] = "X-Test: Value"
    headers = get_additional_headers()
    assert headers == {"X-Test": "Value"}, "Single header not parsed correctly"

def test_get_additional_headers_multiple(mock_env):
    os.environ["EXTRA_HEADERS"] = "X-Test: Value\nX-Another: More"
    headers = get_additional_headers()
    assert headers == {"X-Test": "Value", "X-Another": "More"}, "Multiple headers not parsed correctly"

def test_lowlevel_dispatcher_with_headers(mock_env, mock_requests):
    os.environ["EXTRA_HEADERS"] = "X-Custom: Foo"
    from mcp_openapi_proxy.server_lowlevel import tools, openapi_spec_data
    tools.clear()
    openapi_spec_data = {
        "servers": [{"url": "http://dummy.com"}],
        "paths": {"/test": {"get": {"summary": "Test"}}}
    }
    tools.append(SimpleNamespace(name="get_test", inputSchema={"type": "object", "properties": {}}))
    request = SimpleNamespace(params=SimpleNamespace(name="get_test", arguments={}))
    result = asyncio.run(dispatcher_handler(request))
    assert result.root.content[0].text == "Mocked response", "Dispatcher failed with headers"

def test_fastmcp_call_function_with_headers(mock_env, mock_requests):
    os.environ["EXTRA_HEADERS"] = "X-Custom: Bar"
    result = call_function(function_name="get_test", parameters={}, env_key="OPENAPI_SPEC_URL")
    assert json.loads(result) == "Mocked response", "Call function failed with headers"
