import os
import unittest
import subprocess
import json

class SchemaIntegrationTest(unittest.TestCase):
    def setUp(self):
        # Only run this test when RUN_SCHEMA_TEST env var is set to a truthy value
        if not os.getenv("RUN_SCHEMA_TEST"):
            self.skipTest("Skipping schema integration test - RUN_SCHEMA_TEST not set")

    def test_schema_endpoint(self):
        # Run the curl command to fetch the schema from the server
        command = ["curl", "-s", "http://localhost:8080/v1/schema"]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode("utf-8")
        try:
            schema = json.loads(output)
        except Exception as e:
            self.fail("Schema response is not valid JSON: " + str(e))
        # Check that the schema contains the expected 'openapi' key
        self.assertIn("openapi", schema, "Schema JSON does not contain 'openapi' key")

if __name__ == '__main__':
    unittest.main()