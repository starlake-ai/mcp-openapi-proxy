import pytest
from mcp_openapi_proxy.utils import normalize_tool_name, get_auth_headers, detect_response_type, build_base_url

def test_normalize_tool_name_basic():
    assert normalize_tool_name("GET /pets") == "get_pets", "Basic method and path should normalize correctly"
    assert normalize_tool_name("POST /users.create") == "post_users_create", "Dots should become underscores"

def test_normalize_tool_name_with_params():
    assert normalize_tool_name("GET /sessions/{sessionId}") == "get_sessions", "Path params should be stripped"
    assert normalize_tool_name("PUT /users/{userId}/profile") == "put_users_profile", "Multiple params should be skipped"

def test_normalize_tool_name_edge_cases():
    assert normalize_tool_name("") == "unknown_tool", "Empty string should default to unknown_tool"
    assert normalize_tool_name("/slash/only") == "unknown_tool", "Malformed input should default"

def test_get_auth_headers_no_key(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    headers = get_auth_headers({"securityDefinitions": {}})
    assert headers == {}, "No API_KEY should return empty headers"

def test_get_auth_headers_bearer_override(monkeypatch):
    monkeypatch.setenv("API_KEY", "abc123")
    monkeypatch.setenv("API_AUTH_TYPE", "Bearer")
    headers = get_auth_headers({})
    assert headers["Authorization"] == "Bearer abc123", "API_AUTH_TYPE override should set Bearer token"

def test_detect_response_type_json():
    content, _ = detect_response_type('{"key": "value"}')
    assert content.type == "text"
    assert content.text == '{"text": "{\\"key\\": \\"value\\"}"}', "JSON should be wrapped in text field"

def test_detect_response_type_text():
    content, _ = detect_response_type("Hello, world!")
    assert content.type == "text"
    assert content.text == "Hello, world!", "Plain text should stay as-is"

def test_build_base_url_no_placeholder():
    spec = {"servers": [{"url": "https://api.example.com"}]}
    url = build_base_url(spec)
    assert url == "https://api.example.com", "No placeholder should return clean URL"
