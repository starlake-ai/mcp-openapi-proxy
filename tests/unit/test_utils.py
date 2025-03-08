from mcp_openapi_proxy.utils import normalize_tool_name, detect_response_type, build_base_url

def test_normalize_tool_name_basic():
    assert normalize_tool_name("GET /pets") == "get_pets", "Basic method and path should normalize correctly"

def test_normalize_tool_name_with_params():
    assert normalize_tool_name("GET /sessions/{sessionId}") == "get_sessions", "Path params should be stripped"

def test_normalize_tool_name_edge_cases():
    assert normalize_tool_name("") == "unknown_tool", "Empty string should default to unknown_tool"
    assert normalize_tool_name("POST /users//{id}/") == "post_users", "Multiple slashes should collapse"

def test_get_auth_headers_no_key(monkeypatch):
    from mcp_openapi_proxy.utils import get_auth_headers
    monkeypatch.delenv("API_KEY", raising=False)
    headers = get_auth_headers({})
    assert headers == {}, "No API_KEY should return empty headers"

def test_get_auth_headers_bearer_override(monkeypatch):
    from mcp_openapi_proxy.utils import get_auth_headers
    monkeypatch.setenv("API_KEY", "testkey")
    monkeypatch.setenv("API_AUTH_TYPE", "Bearer")
    headers = get_auth_headers({})
    assert headers == {"Authorization": "Bearer testkey"}, "Bearer auth should set Authorization header"

def test_detect_response_type_json():
    content, msg = detect_response_type('{"key": "value"}')
    assert content.type == "text", "JSON should return text type"
    assert '"text": "{\\"key\\": \\"value\\"}"' in content.text, "JSON should be wrapped in structured text"
    assert "JSON" in msg, "Log message should indicate JSON"

def test_detect_response_type_text():
    content, msg = detect_response_type("Hello, world!")
    assert content.type == "text", "Text should return text type"
    assert content.text == "Hello, world!", "Text should match input"
    assert "non-JSON" in msg, "Log message should indicate non-JSON"

def test_build_base_url_no_placeholder():
    spec = {"servers": [{"url": "https://example.com"}]}
    assert build_base_url(spec) == "https://example.com", "Should use spec URL when no override"

def test_build_base_url_with_server_override():
    import os
    spec = {"servers": [{"url": "https://default.example.com"}]}
    os.environ["SERVER_URL_OVERRIDE"] = "https://api.machines.dev"
    assert build_base_url(spec) == "https://api.machines.dev", "Should use single override URL"
    os.environ["SERVER_URL_OVERRIDE"] = "https://api.machines.dev http://_api.internal:4280"
    assert build_base_url(spec) == "https://api.machines.dev", "Should pick first valid URL"
    os.environ["SERVER_URL_OVERRIDE"] = "not-a-url https://api.machines.dev"
    assert build_base_url(spec) == "https://api.machines.dev", "Should skip invalid URL"
    os.environ["SERVER_URL_OVERRIDE"] = "not-a-url nope"
    assert build_base_url(spec) == "https://default.example.com", "Should fall back to spec URL"
    os.environ["SERVER_URL_OVERRIDE"] = ""
    assert build_base_url(spec) == "https://default.example.com", "Should use spec URL when override empty"
    del os.environ["SERVER_URL_OVERRIDE"]
