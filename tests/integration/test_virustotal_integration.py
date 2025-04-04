import os
import json
import pytest
import logging

logger = logging.getLogger(__name__)

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
VIRUSTOTAL_OPENAPI_URL = f"file://{os.path.join(os.path.dirname(TEST_DIR), '..', 'examples', 'virustotal.openapi.json')}"

def test_virustotal_openapi_and_tools(reset_env_and_module):
    env_key = reset_env_and_module
    # Skip the test if the VIRUSTOTAL_API_KEY is not provided
    virustotal_api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not virustotal_api_key:
        pytest.skip("VIRUSTOTAL_API_KEY not set in .env, skipping test.")

    # Read the local OpenAPI file for VirusTotal
    spec_path = VIRUSTOTAL_OPENAPI_URL.replace("file://", "")
    logger.debug(f"TEST_DIR resolved to: {TEST_DIR}")
    logger.debug(f"Attempting to open spec file at: {spec_path}")
    with open(spec_path, 'r') as f:
        try:
            spec = json.load(f)
        except json.JSONDecodeError:
            import yaml
            spec = yaml.safe_load(f)
    if spec is None:
        import pytest
        pytest.skip("VirusTotal OpenAPI spec is empty or invalid")

    # Validate the OpenAPI structure
    assert "swagger" in spec or "openapi" in spec, "Invalid OpenAPI document: missing version key."
    assert "paths" in spec and spec["paths"], "No API paths found in the specification."
    print(f"DEBUG: Virustotal spec version: {spec.get('swagger') or spec.get('openapi')}")
    print(f"DEBUG: First endpoint found: {next(iter(spec['paths'] or {}), 'none')}")
    print(f"DEBUG: Total paths in spec: {len(spec.get('paths', {}))}")
    print(f"DEBUG: Base path from spec: {spec.get('basePath', 'none')}")

    # Configure server environment variables with unique key
    os.environ[env_key] = VIRUSTOTAL_OPENAPI_URL
    whitelist = ",".join(spec["paths"].keys())
    os.environ["TOOL_WHITELIST"] = whitelist
    os.environ["API_AUTH_BEARER"] = virustotal_api_key
    os.environ["API_AUTH_TYPE_OVERRIDE"] = "Api-Key"
    print(f"DEBUG: Using env key: {env_key}")
    print(f"DEBUG: TOOL_WHITELIST set to: {whitelist}")
    print(f"DEBUG: API_AUTH_TYPE_OVERRIDE set to: {os.environ['API_AUTH_TYPE_OVERRIDE']}")

    # Import after environment setup
    from mcp_openapi_proxy.server_fastmcp import list_functions, call_function
    logger.debug(f"Env before list_functions: {env_key}={os.environ.get(env_key)}, TOOL_WHITELIST={os.environ.get('TOOL_WHITELIST')}")
    logger.debug("Calling list_functions for Virustotal integration")
    tools_json = list_functions(env_key=env_key)
    logger.debug(f"list_functions returned: {tools_json}")
    tools = json.loads(tools_json)
    print(f"DEBUG: Raw tools_json output: {tools_json}")
    print(f"DEBUG: Parsed tools list: {tools}")
    print(f"DEBUG: Number of tools generated: {len(tools)}")

    # Verify tool creation with enhanced debug info on failure
    assert isinstance(tools, list), "list_functions returned invalid data (not a list)."
    assert len(tools) > 0, (
        f"No tools were generated from the VirusTotal specification. "
        f"VIRUSTOTAL_OPENAPI_URL: {VIRUSTOTAL_OPENAPI_URL}, "
        f"Spec keys: {list(spec.keys())}, "
        f"Paths: {list(spec.get('paths', {}).keys())}"
    )