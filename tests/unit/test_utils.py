"""
Unit tests for utility functions in mcp_openapi_proxy.utils.
"""

import os
from mcp_openapi_proxy.utils import normalize_tool_name, detect_response_type, build_base_url, handle_custom_auth


def test_normalize_tool_name():
    """Test tool name normalization."""
    assert normalize_tool_name("GET /users/{userId}") == "get_users"
    assert normalize_tool_name("POST /pets.create") == "post_pets_create"
    assert normalize_tool_name("") == "unknown_tool"
    assert normalize_tool_name("GET /api/v2/things") == "get_things"


def test_detect_response_type_json():
    """Test detection of JSON response type."""
    json_response = '{"status": "ok"}'
    content, message = detect_response_type(json_response)
    assert content.type == "text"
    assert content.text == '{"text": "{\\"status\\": \\"ok\\"}"}'
    assert "Detected JSON response" in message


def test_detect_response_type_text():
    """Test detection of plain text response type."""
    text_response = "Hello, world!"
    content, message = detect_response_type(text_response)
    assert content.type == "text"
    assert content.text == "Hello, world!"
    assert "Detected non-JSON response" in message


def test_build_base_url_servers():
    """Test base URL construction with OpenAPI 3.0 servers."""
    spec = {"servers": [{"url": "https://api.example.com/v1"}]}
    assert build_base_url(spec) == "https://api.example.com/v1"


def test_build_base_url_host():
    """Test base URL construction with Swagger 2.0 host."""
    spec = {"host": "api.example.com", "schemes": ["https"], "basePath": "/v2"}
    assert build_base_url(spec) == "https://api.example.com/v2"


def test_handle_custom_auth_no_jmespath():
    """Test handle_custom_auth with no API_KEY_JMESPATH set."""
    operation = {"method": "GET"}
    params = {"existing": "value"}
    os.environ.pop("API_KEY_JMESPATH", None)
    os.environ.pop("API_KEY", None)
    result = handle_custom_auth(operation, params)
    assert result == {"existing": "value"}


def test_handle_custom_auth_query():
    """Test handle_custom_auth mapping API_KEY to query parameter."""
    operation = {"method": "GET"}
    params = {"existing": "value"}
    os.environ["API_KEY"] = "test-key"
    os.environ["API_KEY_JMESPATH"] = "query.token"
    result = handle_custom_auth(operation, params)
    assert result == {"existing": "value", "token": "test-key"}


def test_handle_custom_auth_body():
    """Test handle_custom_auth mapping API_KEY to body parameter."""
    operation = {"method": "POST"}
    params = {"existing": "value"}
    os.environ["API_KEY"] = "test-key"
    os.environ["API_KEY_JMESPATH"] = "body.auth.key"
    result = handle_custom_auth(operation, params)
    assert result == {"existing": "value", "auth": {"key": "test-key"}}


def test_handle_custom_auth_none_params():
    """Test handle_custom_auth with no initial parameters."""
    operation = {"method": "GET"}
    os.environ["API_KEY"] = "test-key"
    os.environ["API_KEY_JMESPATH"] = "query.token"
    result = handle_custom_auth(operation, None)
    assert result == {"token": "test-key"}


def test_handle_custom_auth_overwrite():
    """Test handle_custom_auth overwriting existing token with API_KEY."""
    operation = {"method": "GET"}
    params = {"token": "old-token", "exclude_archived": "true"}
    os.environ["API_KEY"] = "new-test-key"
    os.environ["API_KEY_JMESPATH"] = "query.token"
    result = handle_custom_auth(operation, params)
    assert result == {"token": "new-test-key", "exclude_archived": "true"}
