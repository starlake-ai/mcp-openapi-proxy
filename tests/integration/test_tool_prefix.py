import os
import unittest
import json
from mcp_openapi_proxy.utils import map_verba_schema_to_tools

class ToolPrefixIntegrationTest(unittest.TestCase):
    def setUp(self):
        # Set the environment variable for testing the tool name prefix.
        os.environ["TOOL_NAME_PREFIX"] = "api"
    
    def tearDown(self):
        # Clean up the environment variable after the test.
        if "TOOL_NAME_PREFIX" in os.environ:
            del os.environ["TOOL_NAME_PREFIX"]

    def test_tool_name_prefix_mapping(self):
        # Sample schema resembling the /v1/verba endpoint schema
        sample_schema = {
            "classes": [
                {"class": "VERBA_Example_Class", "attribute": "value1"},
                {"class": "VERBA_Sample", "attribute": "value2"}
            ]
        }
        tools = map_verba_schema_to_tools(sample_schema)
        # Expect 2 tools mapped from the sample schema
        self.assertEqual(len(tools), 2, "Expected 2 tools from schema mapping")
        for tool in tools:
            # Each tool name should start with the prefix 'api_' as set in the environment variable
            self.assertTrue(tool.name.startswith("api_"), f"Tool name {tool.name} does not start with 'api_'")
            # Also ensure the normalized name part is in lowercase
            self.assertTrue(tool.name.islower(), f"Tool name {tool.name} is not in lowercase")

if __name__ == '__main__':
    unittest.main()