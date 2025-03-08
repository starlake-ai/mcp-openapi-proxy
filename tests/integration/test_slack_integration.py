"""
Integration test for Slack API using mcp-openapi-proxy with online spec.
"""

import os
import json
import pytest
import requests
from dotenv import load_dotenv

# Explicitly load .env from project root
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
print(f"DEBUG: Looking for .env at: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

SLACK_OPENAPI_URL = "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json"

@pytest.mark.integration
def test_slack_chat_postmessage(reset_env_and_module):
    """Test Slack integration by posting a message if SLACK_API_KEY is set."""
    env_key = reset_env_and_module
    slack_api_key = os.getenv("SLACK_API_KEY")
    print(f"DEBUG: SLACK_API_KEY from os.getenv: {slack_api_key if slack_api_key else 'Not set'}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    if not slack_api_key:
        pytest.skip("SLACK_API_KEY not set in .env, skipping Slack integration test")

    # Verify spec is fetchable
    try:
        response = requests.get(SLACK_OPENAPI_URL, timeout=10)
        response.raise_for_status()
        spec = response.json()
        assert "paths" in spec, "Invalid Slack spec: no 'paths' key"
        assert "/chat.postMessage" in spec["paths"], "Slack spec missing /chat.postMessage"
    except requests.RequestException as e:
        pytest.skip(f"Failed to fetch Slack spec from {SLACK_OPENAPI_URL}: {e}")

    # Configure environment
    os.environ[env_key] = SLACK_OPENAPI_URL
    os.environ["SERVER_URL_OVERRIDE"] = "https://slack.com/api"
    os.environ["API_KEY"] = slack_api_key
    os.environ["API_KEY_JMESPATH"] = "query.token"
    os.environ["TOOL_WHITELIST"] = "/chat.postMessage,/users.info"
    os.environ["TOOL_NAME_PREFIX"] = "slack_"
    os.environ["DEBUG"] = "true"

    # Import after env setup
    from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

    # Verify tools
    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    print(f"DEBUG: Slack tools: {tools_json}")
    assert isinstance(tools, list) and len(tools) > 0, "No tools generated from Slack spec"
    assert any(t["name"] == "slack_post_chat_postmessage" for t in tools), "Missing slack_post_chat_postmessage tool"

    # Test posting a message
    channel_id = os.getenv("SLACK_TEST_CHANNEL", "C12345678")  # Set SLACK_TEST_CHANNEL in .env
    print(f"DEBUG: SLACK_TEST_CHANNEL: {channel_id}")
    response_json = call_function(
        function_name="slack_post_chat_postmessage",
        parameters={"channel": channel_id, "text": "Test message from mcp-openapi-proxy"},
        env_key=env_key
    )
    print(f"DEBUG: Slack response: {response_json}")
    try:
        result = json.loads(response_json)
        if "error" in result:
            if result["error"] == "channel_not_found":
                pytest.skip(f"Channel {channel_id} not found - set SLACK_TEST_CHANNEL correctly")
            assert False, f"Slack API error: {result['error']}"
        assert result.get("ok", False), f"Chat post failed: {response_json}"
        assert "message" in result, "No message in response"
        assert result["message"]["text"] == "Test message from mcp-openapi-proxy", "Message text mismatch"
    except json.JSONDecodeError:
        pytest.fail(f"Invalid JSON response: {response_json}")
