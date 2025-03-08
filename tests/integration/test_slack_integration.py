"""
Integration tests for Slack API via mcp-openapi-proxy, low-level mode.
Needs SLACK_SPEC_URL and SLACK_API_KEY in .env for testing.
TEST_SLACK_CHANNEL optional for posting messages.
"""

import os
import json
import pytest
from dotenv import load_dotenv
from mcp_openapi_proxy.utils import fetch_openapi_spec
from mcp_openapi_proxy.server_fastmcp import mcp, list_functions, call_function

# Load .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

@pytest.mark.integration
def test_slack_users_info(reset_env_and_module):
    """Test users.info with SLACK_API_KEY."""
    env_key = reset_env_and_module
    slack_api_key = os.getenv("SLACK_API_KEY")
    spec_url = os.getenv("SLACK_SPEC_URL", "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json")
    tool_prefix = os.getenv("TOOL_NAME_PREFIX", "slack_")
    print(f"🍺 DEBUG: SLACK_API_KEY from env: {slack_api_key if slack_api_key else 'Not set'}")
    if not slack_api_key or "your-token" in slack_api_key:
        print("🍻 DEBUG: Skipping due to missing or invalid SLACK_API_KEY")
        pytest.skip("SLACK_API_KEY missing or placeholder—please configure it!")

    # Fetch the specification
    print(f"🍆 DEBUG: Fetching spec from {spec_url}")
    spec = fetch_openapi_spec(spec_url)
    assert spec, f"Failed to fetch spec from {spec_url}"
    assert "paths" in spec, "No 'paths' key found in spec"
    assert "/users.info" in spec["paths"], "No /users.info endpoint in spec"
    assert "servers" in spec or "host" in spec, "No servers or host defined in spec"

    # Set environment variables—use SLACK_API_KEY for testing
    os.environ[env_key] = spec_url
    os.environ["SLACK_API_KEY"] = slack_api_key
    os.environ["API_KEY"] = slack_api_key  # Set it anyway for prod consistency
    os.environ["API_KEY_JMESPATH"] = "token"
    os.environ["TOOL_NAME_PREFIX"] = tool_prefix
    os.environ["TOOL_WHITELIST"] = "/chat,/bots,/conversations,/reminders,/files,/users"
    os.environ["DEBUG"] = "true"
    print(f"🍍 DEBUG: API_KEY set to: {os.environ['API_KEY']}")

    # Verify tools
    print("🍑 DEBUG: Listing available tools")
    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    assert isinstance(tools, list), f"Tools response is not a list: {tools_json}"
    assert tools, f"No tools generated: {tools_json}"
    tool_name = f"{tool_prefix}get_users_info"
    assert any(t["name"] == tool_name for t in tools), f"Tool {tool_name} not found"

    # Send request
    print("🍌 DEBUG: Calling users.info for Slackbot")
    response_json = call_function(
        function_name=tool_name,
        parameters={"user": "USLACKBOT"},
        env_key=env_key
    )
    print(f"🍒 DEBUG: Raw response: {response_json}")
    try:
        response = json.loads(response_json)
        if isinstance(response, dict) and "error" in response:
            print(f"🍷 DEBUG: Error occurred: {response['error']}")
            if "401" in response["error"]:
                assert False, "SLACK_API_KEY is invalid—please check it!"
            assert False, f"Slack API returned an error: {response_json}"
        assert isinstance(response, dict), f"Response is not a dictionary: {response_json}"
        assert response["ok"], f"Slack API request failed: {response_json}"
        assert "user" in response, f"No 'user' key in response: {response_json}"
        assert response["user"]["id"] == "USLACKBOT", "Unexpected user ID in response"
    except json.JSONDecodeError:
        assert False, f"Response is not valid JSON: {response_json}"

@pytest.mark.integration
def test_slack_conversations_list(reset_env_and_module):
    """Test conversations.list endpoint."""
    env_key = reset_env_and_module
    slack_api_key = os.getenv("SLACK_API_KEY")
    spec_url = os.getenv("SLACK_SPEC_URL", "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json")
    tool_prefix = os.getenv("TOOL_NAME_PREFIX", "slack_")
    print(f"🍺 DEBUG: SLACK_API_KEY from env: {slack_api_key if slack_api_key else 'Not set'}")
    if not slack_api_key:
        pytest.skip("SLACK_API_KEY not provided—skipping test")

    spec = fetch_openapi_spec(spec_url)
    assert spec, "Failed to fetch specification"
    assert "/conversations.list" in spec["paths"], "No conversations.list endpoint in spec"
    assert "servers" in spec or "host" in spec, "No servers or host in specification"

    os.environ[env_key] = spec_url
    os.environ["SLACK_API_KEY"] = slack_api_key
    os.environ["API_KEY"] = slack_api_key  # Set for prod, but test uses SLACK_API_KEY
    os.environ["API_KEY_JMESPATH"] = "token"
    os.environ["TOOL_NAME_PREFIX"] = tool_prefix
    os.environ["DEBUG"] = "true"
    print(f"🍍 DEBUG: API_KEY set to: {os.environ['API_KEY']}")

    tool_name = f"{tool_prefix}get_conversations_list"
    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    assert any(t["name"] == tool_name for t in tools), f"Tool {tool_name} not found"

    response_json = call_function(
        function_name=tool_name,
        parameters={"exclude_archived": "true", "types": "public_channel,private_channel", "limit": "100"},
        env_key=env_key
    )
    print(f"🍒 DEBUG: Raw response: {response_json}")
    response = json.loads(response_json)
    assert response["ok"], f"Slack API request failed: {response_json}"
    assert "channels" in response, f"No 'channels' key in response: {response_json}"
    channels = response["channels"]
    assert channels, "No channels returned in response"
    channel_ids = [ch["id"] for ch in channels]
    assert channel_ids, "Failed to extract channel IDs from response"
    return channel_ids  # Needed for post_message test

@pytest.mark.integration
def test_slack_post_message(reset_env_and_module):
    """Test posting a message to a Slack channel."""
    env_key = reset_env_and_module
    slack_api_key = os.getenv("SLACK_API_KEY")
    test_channel = os.getenv("TEST_SLACK_CHANNEL")
    spec_url = os.getenv("SLACK_SPEC_URL", "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json")
    tool_prefix = os.getenv("TOOL_NAME_PREFIX", "slack_")
    print(f"🍺 DEBUG: SLACK_API_KEY from env: {slack_api_key if slack_api_key else 'Not set'}")
    if not slack_api_key:
        pytest.skip("SLACK_API_KEY not provided—skipping test")
    if not test_channel:
        pytest.skip("TEST_SLACK_CHANNEL not provided—skipping test")

    spec = fetch_openapi_spec(spec_url)
    assert "servers" in spec or "host" in spec, "No servers or host in specification"

    os.environ[env_key] = spec_url
    os.environ["SLACK_API_KEY"] = slack_api_key
    os.environ["API_KEY"] = slack_api_key  # Set for prod, but test uses SLACK_API_KEY
    os.environ["API_KEY_JMESPATH"] = "token"
    os.environ["TOOL_NAME_PREFIX"] = tool_prefix
    os.environ["DEBUG"] = "true"
    print(f"🍍 DEBUG: API_KEY set to: {os.environ['API_KEY']}")

    channels = test_slack_conversations_list(reset_env_and_module)
    if test_channel not in channels:
        pytest.skip(f"TEST_SLACK_CHANNEL {test_channel} not found in {channels}—check workspace")

    tool_name = f"{tool_prefix}post_chat_postmessage"
    response_json = call_function(
        function_name=tool_name,
        parameters={"channel": test_channel, "text": "Integration test message from mcp-openapi-proxy"},
        env_key=env_key
    )
    print(f"🍒 DEBUG: Raw response: {response_json}")
    response = json.loads(response_json)
    assert response["ok"], f"Message posting failed: {response_json}"
    assert response["channel"] == test_channel, f"Message posted to incorrect channel: {response_json}"
