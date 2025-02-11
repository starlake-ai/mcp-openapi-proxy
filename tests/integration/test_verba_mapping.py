import os
import unittest
import json
from mcp_openapi_proxy.utils import map_verba_schema_to_tools

class VerbaMappingIntegrationTest(unittest.TestCase):
    def setUp(self):
        # Only run this test if RUN_VERBA_MAPPING_TEST environment variable is set
        if not os.getenv("RUN_VERBA_MAPPING_TEST"):
            self.skipTest("Skipping verba mapping test - RUN_VERBA_MAPPING_TEST not set")

    def test_map_verba_schema_to_tools(self):
        # Sample schema resembling the /v1/verba endpoint schema
        sample_schema = {
            "classes": [
                {"class": "VERBA_Example_Class", "attribute": "value1"},
                {"class": "VERBA_Sample", "attribute": "value2"},
                {"class": "", "attribute": "ignored"},
                {"attribute": "missing_class"}
            ]
        }
        tools = map_verba_schema_to_tools(sample_schema)
        # Expect 2 tools (only valid class entries are mapped)
        self.assertEqual(len(tools), 2, "Expected 2 tools from schema")

        for tool in tools:
            # Each tool name should be normalized and start with 'verba_'
            self.assertTrue(tool.name.startswith("verba_"), f"Tool name {tool.name} does not start with 'verba_'")
            # Check that the description is a non-empty string
            self.assertTrue(isinstance(tool.description, str) and len(tool.description) > 0, "Tool description should be a non-empty string")

if __name__ == '__main__':
    unittest.main()