"""
Unit tests for utility functions in mcp-openapi-proxy.
"""

import os
import pytest
from mcp_openapi_proxy.utils import normalize_tool_name, detect_response_type, build_base_url, handle_auth, strip_parameters

def test_normalize_tool_name():
    assert normalize_tool_name("GET /api/v2/users") == "get_users"
    assert normalize_tool_name("POST /users/{id}") == "post_users_id"
    assert normalize_tool_name("INVALID") == "unknown_tool"

def test_detect_response_type_json():
    content, msg = detect_response_type('{"key": "value"}')
    assert content.type == "text"
    assert content.text == '{"text": "{\\"key\\": \\"value\\"}"}'
    assert "JSON" in msg

def test_detect_response_type_text():
    content, msg = detect_response_type("plain text")
    assert content.type == "text"
    assert content.text == "plain text"
    assert "non-JSON" in msg

def test_build_base_url_servers():
    spec = {"servers": [{"url": "https://api.example.com/v1"}]}
    assert build_base_url(spec) == "https://api.example.com/v1"

def test_build_base_url_host():
    spec = {"host": "api.example.com", "schemes": ["https"], "basePath": "/v1"}
    assert build_base_url(spec) == "https://api.example.com/v1"

def test_handle_auth_with_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "testkey")
    headers = handle_auth({"method": "GET"})
    assert headers == {"Authorization": "Bearer testkey"}

def test_handle_auth_no_api_key():
    headers = handle_auth({"method": "GET"})
    assert headers == {}

def test_strip_parameters_with_param(monkeypatch):
    monkeypatch.setenv("STRIP_PARAM", "token")
    params = {"token": "abc123", "channel": "test"}
    result = strip_parameters(params)
    assert result == {"channel": "test"}

def test_strip_parameters_no_param():
    params = {"channel": "test"}
    result = strip_parameters(params)
    assert result == {"channel": "test"}
