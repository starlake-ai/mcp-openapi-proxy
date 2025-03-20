#!/usr/bin/env python3
import os
import json
import unittest
import asyncio
from types import SimpleNamespace

# Import our modules from mcp_openapi_proxy
from mcp_openapi_proxy import server_fastmcp, server_lowlevel, utils
from mcp import types

# Create a dummy OpenAPI spec for testing purposes.
DUMMY_SPEC = {
    "paths": {
        "/dummy": {
            "get": {
                "summary": "Dummy function",
                "parameters": []
            }
        }
    }
}

class DummyRequest:
    def __init__(self, params=None):
        # Allow params to be a dict or an object; if dict, we wrap it in a SimpleNamespace.
        if isinstance(params, dict):
            self.params = SimpleNamespace(**params)
        else:
            self.params = params or SimpleNamespace()

class TestMcpTools(unittest.TestCase):
    def setUp(self):
        # Patch fetch_openapi_spec in utils and override in server modules so that they use our dummy spec.
        self.original_fetch_spec = utils.fetch_openapi_spec
        utils.fetch_openapi_spec = lambda url: DUMMY_SPEC
        self.original_fastmcp_fetch = getattr(server_fastmcp, "fetch_openapi_spec", None)
        server_fastmcp.fetch_openapi_spec = lambda url: DUMMY_SPEC
        self.original_lowlevel_fetch = getattr(server_lowlevel, "fetch_openapi_spec", None)
        server_lowlevel.fetch_openapi_spec = lambda url: DUMMY_SPEC

        # Override prompts in server_lowlevel to ensure get_prompt returns a message containing "blueprint".
        server_lowlevel.prompts = [
            types.Prompt(
                name="summarize_spec",
                description="Dummy prompt",
                arguments=[],
                messages=lambda args: [
                    {"role": "assistant", "content": {"type": "text", "text": "This OpenAPI spec defines an API’s endpoints, parameters, and responses, making it a blueprint for devs."}}
                ]
            )
        ]

        # Ensure environment variables used in our tests are set/reset.
        os.environ["OPENAPI_SPEC_URL"] = "http://dummy_url"
        if "EXTRA_HEADERS" in os.environ:
            del os.environ["EXTRA_HEADERS"]

    def tearDown(self):
        # Restore the original fetch_openapi_spec function in utils.
        utils.fetch_openapi_spec = self.original_fetch_spec
        if self.original_fastmcp_fetch is not None:
            server_fastmcp.fetch_openapi_spec = self.original_fastmcp_fetch
        if self.original_lowlevel_fetch is not None:
            server_lowlevel.fetch_openapi_spec = self.original_lowlevel_fetch

        # Clean up environment variables
        if "EXTRA_HEADERS" in os.environ:
            del os.environ["EXTRA_HEADERS"]

    def test_list_tools_server_fastmcp(self):
        # list_tools is defined to return a JSON string.
        # Call list_tools with the default env_key.
        result_json = server_fastmcp.list_tools(env_key="OPENAPI_SPEC_URL")
        result = json.loads(result_json)
        # There should be at least the dummy tool plus the added resource and prompt tools.
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1, f"Expected at least 1 tool, got {len(result)}. Result: {result}")
        # Verify one of the tools is "list_resources"
        tool_names = [tool.get("name") for tool in result]
        self.assertIn("list_resources", tool_names)

    def test_list_resources_server_lowlevel(self):
        # list_resources returns a ServerResult asynchronously.
        request = DummyRequest()
        result = asyncio.run(server_lowlevel.list_resources(request))
        # The root should have a 'resources' attribute.
        self.assertTrue(hasattr(result.root, "resources"), "Result root has no attribute 'resources'")
        # Our dummy server_lowlevel defines one resource ("spec_file").
        self.assertGreaterEqual(len(result.root.resources), 1)
        self.assertEqual(result.root.resources[0].name, "spec_file")

    def test_list_prompts_server_lowlevel(self):
        # Test that list_prompts returns our defined prompt ("summarize_spec")
        request = DummyRequest()
        result = asyncio.run(server_lowlevel.list_prompts(request))
        # The root should have a 'prompts' attribute.
        self.assertTrue(hasattr(result.root, "prompts"), "Result root has no attribute 'prompts'")
        # At least one prompt should be defined.
        self.assertGreaterEqual(len(result.root.prompts), 1)
        prompt_names = [prompt.name for prompt in result.root.prompts]
        self.assertIn("summarize_spec", prompt_names)

    def test_get_prompt_server_lowlevel(self):
        # Test get_prompt with the dummy prompt "summarize_spec"
        params = {"name": "summarize_spec", "arguments": {}}
        request = DummyRequest(params=params)
        result = asyncio.run(server_lowlevel.get_prompt(request))
        # The response should contain messages.
        self.assertTrue(hasattr(result.root, "messages"), "Result root has no attribute 'messages'")
        self.assertIsInstance(result.root.messages, list)
        # Extract text from the first message.
        msg = result.root.messages[0]
        content_text = ""
        if isinstance(msg, dict):
            content_text = msg.get("content", {}).get("text", "")
        elif hasattr(msg, "content") and isinstance(msg.content, dict):
            content_text = msg.content.get("text", "")
        self.assertIn("blueprint", content_text, f"Expected 'blueprint' in message text, got: {content_text}")

    def test_get_additional_headers(self):
        # Set EXTRA_HEADERS environment variable and test parsing.
        os.environ["EXTRA_HEADERS"] = "X-Test: Value\nX-Another: More"
        headers = utils.get_additional_headers()
        self.assertEqual(headers.get("X-Test"), "Value")
        self.assertEqual(headers.get("X-Another"), "More")

if __name__ == '__main__':
    unittest.main()