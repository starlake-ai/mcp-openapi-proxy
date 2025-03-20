"""
Integration tests for GitHub API via mcp-openapi-proxy, FastMCP mode.
Requires GITHUB_API_KEY in .env to run.
"""

import os
import json
import pytest
from dotenv import load_dotenv
from mcp_openapi_proxy.utils import fetch_openapi_spec
from mcp_openapi_proxy.server_fastmcp import list_functions, call_function

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

SPEC_URL = "https://api.apis.guru/v2/specs/github.com/github.ae/1.1.4/openapi.json"
SERVER_URL = "https://api.github.com"
EXTRA_HEADERS = ""
TOOL_PREFIX = "git_"

def setup_github_env(env_key, github_api_key):
    """Set up environment variables for GitHub tests."""
    os.environ[env_key] = SPEC_URL
    os.environ["API_KEY"] = github_api_key
    os.environ["SERVER_URL_OVERRIDE"] = SERVER_URL
    os.environ["EXTRA_HEADERS"] = EXTRA_HEADERS
    os.environ["TOOL_NAME_PREFIX"] = TOOL_PREFIX
    os.environ["TOOL_WHITELIST"] = "/repos/"
    os.environ["DEBUG"] = "true"
    print(f"DEBUG: API_KEY set to: {os.environ['API_KEY'][:5]}...")

def get_tool_name(tools, original_name):
    """Find tool name by original endpoint name."""
    return next((tool["name"] for tool in tools if tool["original_name"] == original_name), None)

@pytest.fixture
def github_ids(reset_env_and_module):
    """Fixture to fetch a repository ID from GitHub."""
    env_key = reset_env_and_module
    github_api_key = os.getenv("GITHUB_API_KEY")
    print(f"DEBUG: GITHUB_API_KEY: {github_api_key if github_api_key else 'Not set'}")
    if not github_api_key or "your_key" in github_api_key or github_api_key=="dummy":
        print("DEBUG: Skipping due to missing or placeholder GITHUB_API_KEY")
        pytest.skip("GITHUB_API_KEY missing or placeholder—set it in .env, please!")

    setup_github_env(env_key, github_api_key)
    os.environ["PRELOAD_USERNAME"] = "matthewhand"
    os.environ["FUNCTION_FILTER"] = "username"

    print(f"DEBUG: Fetching spec from {SPEC_URL}")
    spec = fetch_openapi_spec(SPEC_URL)
    assert spec, f"Failed to fetch spec from {SPEC_URL}"

    print("DEBUG: Listing available functions")
    tools_json = list_functions(env_key=env_key)
    tools = json.loads(tools_json)
    print(f"DEBUG: Tools: {tools_json}")
    assert tools, "No functions generated"

    search_tool = get_tool_name(tools, "GET /repos/{owner}/{repo}")
    assert search_tool, "Search tool not found!"

    print(f"DEBUG: Calling {search_tool} to find IDs")
    response_json = call_function(
        function_name=search_tool,
        parameters={"owner": "octocat", "repo": "Hello-World"},
        env_key=env_key
    )
    print(f"DEBUG: Search response: {response_json}")
    response = json.loads(response_json)
    assert "id" in response, "No id in search response"

    repo_id = response["id"]

    if not repo_id:
        print(f"DEBUG: Repo ID: {repo_id}")
        pytest.skip("No repository found in search—please add some to GitHub!")

    return env_key, tools, repo_id

@pytest.mark.integration
def test_github_users_list(github_ids):
    """Test GitHub /users endpoint with GITHUB_API_KEY."""
    env_key, tools, _ = github_ids
    tool_name = get_tool_name(tools, "GET /users")
    assert tool_name, "Function for GET /users not found!"

    print(f"DEBUG: Calling {tool_name} for user list")
    response_json = call_function(function_name=tool_name, parameters={}, env_key=env_key)
    print(f"DEBUG: Raw response: {response_json}")
    try:
        response = json.loads(response_json)
        if isinstance(response, dict) and "error" in response:
            print(f"DEBUG: Error occurred: {response['error']}")
            if "401" in response["error"] or "invalid_token" in response["error"]:
                assert False, "GITHUB_API_KEY is invalid—please check your token!"
            assert False, f"GitHub API returned an error: {response_json}"
        assert isinstance(response, list), f"Response is not a list: {response_json}"
        print(f"DEBUG: Found {len(response)} users—excellent!")
    except json.JSONDecodeError:
        assert False, f"Response is not valid JSON: {response_json}"

@pytest.mark.integration
def test_github_users_me(github_ids):
    """Test GitHub /user endpoint with GITHUB_API_KEY."""
    env_key, tools, _ = github_ids
    tool_name = get_tool_name(tools, "GET /user")
    assert tool_name, "Function for GET /user not found!"

    print(f"DEBUG: Calling {tool_name} for bot user")
    response_json = call_function(function_name=tool_name, parameters={}, env_key=env_key)
    print(f"DEBUG: Raw response: {response_json}")
    try:
        response = json.loads(response_json)
        if isinstance(response, dict) and "error" in response:
            print(f"DEBUG: Error occurred: {response['error']}")
            if "401" in response["error"] or "invalid_token" in response["error"]:
                assert False, "GITHUB_API_KEY is invalid—please check your token!"
            assert False, f"GitHub API returned an error: {response_json}"
        assert isinstance(response, dict), f"Response is not a dictionary: {response_json}"
        assert "login" in response, "Response does not contain 'login'"
        print(f"DEBUG: Got user: {response.get('login', 'Unnamed')}—excellent!")
    except json.JSONDecodeError:
        assert False, f"Response is not valid JSON: {response_json}"

@pytest.mark.integration
def test_github_search(github_ids):
    """Test GitHub /search/repositories endpoint with GITHUB_API_KEY."""
    env_key, tools, _ = github_ids
    tool_name = get_tool_name(tools, "GET /search/repositories")
    assert tool_name, "Function for GET /search/repositories not found!"

    print(f"DEBUG: Calling {tool_name} for search")
    response_json = call_function(
        function_name=tool_name,
        parameters={"q": "test"},
        env_key=env_key
    )
    print(f"DEBUG: Raw response: {response_json}")
    try:
        response = json.loads(response_json)
        if isinstance(response, dict) and "error" in response:
            print(f"DEBUG: Error occurred: {response['error']}")
            if "401" in response["error"] or "invalid_token" in response["error"]:
                assert False, "GITHUB_API_KEY is invalid—please check your token!"
            assert False, f"GitHub API returned an error: {response_json}"
        assert isinstance(response, dict), f"Response is not a dictionary: {response_json}"
        assert "items" in response, f"No 'items' key in response: {response_json}"
        assert isinstance(response["items"], list), "Items is not a list"
        print(f"DEBUG: Found {len(response['items'])} search results—excellent!")
    except json.JSONDecodeError:
        assert False, f"Response is not valid JSON: {response_json}"

@pytest.mark.integration
def test_github_get_repo(github_ids):
    """Test GitHub /repos/{owner}/{repo} endpoint with GITHUB_API_KEY."""
    env_key, tools, repo_id = github_ids
    tool_name = get_tool_name(tools, "GET /repos/{owner}/{repo}")
    assert tool_name, "Function for GET /repos/{owner}/{repo} not found!"

    print(f"DEBUG: Calling {tool_name} for repo {repo_id}")
    response_json = call_function(
        function_name=tool_name,
        parameters={"owner": "octocat", "repo": "Hello-World"},
        env_key=env_key
    )
    print(f"DEBUG: Raw response: {response_json}")
    try:
        response = json.loads(response_json)
        if isinstance(response, dict) and "error" in response:
            print(f"DEBUG: Error occurred: {response['error']}")
            if "401" in response["error"] or "invalid_token" in response["error"]:
                assert False, "GITHUB_API_KEY is invalid—please check your token!"
            assert False, f"GitHub API returned an error: {response_json}"
        assert isinstance(response, dict), f"Response is not a dictionary: {response_json}"
        assert "id" in response, "Response does not contain 'id'"
        assert response["id"] == repo_id, f"Expected repo ID {repo_id}, got {response['id']}"
        print(f"DEBUG: Got repo: {response.get('html_url', 'No URL')}—excellent!")
    except json.JSONDecodeError:
        assert False, f"Response is not valid JSON: {response_json}"