import unittest
from types import SimpleNamespace
import requests
import mcp_openapi_proxy.server_lowlevel as server
import pytest

class TestParameterSubstitution(unittest.TestCase):
    def setUp(self):
        server.tools.clear()
        self.dummy_spec = {
            "openapi": "3.0.0",
            "servers": [{"url": "https://dummy-base-url.com"}],
            "paths": {
                "/repos/{owner}/{repo}/contents/": {
                    "get": {
                        "summary": "Get repo contents",
                        "parameters": [
                            {"name": "owner", "in": "path", "required": True, "schema": {"type": "string"}},
                            {"name": "repo", "in": "path", "required": True, "schema": {"type": "string"}}
                        ],
                        "responses": {
                            "200": {
                                "description": "OK"
                            }
                        }
                    }
                }
            }
        }
        server.openapi_spec_data = self.dummy_spec
        server.register_functions(self.dummy_spec)

    @pytest.mark.asyncio
    async def test_path_parameter_substitution(self):
        # Use the registered tool's name to ensure consistency
        tool_name = server.tools[0].name
        dummy_request = SimpleNamespace(
            params=SimpleNamespace(
                name=tool_name,
                arguments={"owner": "foo", "repo": "bar"}
            )
        )
        original_request = requests.request

        def dummy_request_fn(method, url, **kwargs):
            dummy_request_fn.called_url = url
            class DummyResponse:
                def __init__(self, url):
                    self.url = url
                    self.text = "Success"
                def raise_for_status(self):
                    pass
            return DummyResponse(url)

        requests.request = dummy_request_fn
        try:
            await server.dispatcher_handler(dummy_request)
        finally:
            requests.request = original_request

        expected_url = "https://dummy-base-url.com/repos/foo/bar/contents/"
        self.assertEqual(dummy_request_fn.called_url, expected_url,
                         f"Expected URL: {expected_url}, got {dummy_request_fn.called_url}")

if __name__ == "__main__":
    unittest.main()
