import os
import glob
import json
import re
import requests
import yaml
import pytest
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

def load_config(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def fetch_spec(spec_url):
    try:
        r = requests.get(spec_url, timeout=10)
        if r.status_code in [401, 403]:
            pytest.skip(f"Spec {spec_url} requires authentication (status code {r.status_code}).")
        r.raise_for_status()
        content = r.text
    except Exception as e:
        pytest.fail(f"Failed to fetch spec from {spec_url}: {e}")
    # Attempt to parse JSON first
    try:
        spec = json.loads(content)
    except json.JSONDecodeError:
        try:
            spec = yaml.safe_load(content)
        except Exception as e:
            pytest.fail(f"Content from {spec_url} is not valid JSON or YAML: {e}")
    return spec

def has_valid_spec(spec):
    return isinstance(spec, dict) and ("openapi" in spec or "swagger" in spec)

def check_env_placeholders(env_config):
    # For each value, if a placeholder like ${VAR_NAME} exists, verify os.environ has that key.
    missing_vars = []
    for key, value in env_config.items():
        placeholders = re.findall(r'\$\{([^}]+)\}', value)
        for var in placeholders:
            if os.environ.get(var) is None:
                missing_vars.append(var)
    return missing_vars

@pytest.mark.parametrize("config_file", [
    f for f in glob.glob("examples/claude_desktop_config.json*")
    if ".bak" not in f
])
def test_working_example(config_file):
    # Load the configuration
    config = load_config(config_file)
    mcp_servers = config.get("mcpServers", {})
    assert mcp_servers, f"No mcpServers found in {config_file}"
    
    for server_name, server_config in mcp_servers.items():
        env_config = server_config.get("env", {})
        spec_url = env_config.get("OPENAPI_SPEC_URL", None)
        assert spec_url, f"OPENAPI_SPEC_URL not specified in {config_file} for server {server_name}"
        # Skip examples with placeholder domains (e.g., 'your-confluence-instance.com', 'your-ghost-instance.com')
        if re.search(r'your-', spec_url, re.IGNORECASE):
            pytest.skip(f"Skipping test for {config_file} for server {server_name} because spec URL {spec_url} contains a placeholder domain.")
        # Fetch spec from the URL
        spec = fetch_spec(spec_url)
        assert has_valid_spec(spec), f"Spec fetched from {spec_url} in {config_file} is invalid (missing 'openapi' or 'swagger')"
        
        # Check environment variable placeholders if any
        missing_vars = check_env_placeholders(env_config)
        assert not missing_vars, f"Missing environment variables {missing_vars} in config {config_file} for server {server_name}"