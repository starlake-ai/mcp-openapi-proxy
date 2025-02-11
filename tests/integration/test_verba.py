import os
import unittest
import subprocess
import json

class VerbaEndpointIntegrationTest(unittest.TestCase):
    def setUp(self):
        # Only run this test when RUN_VERBA_TEST env var is set to a truthy value
        if not os.getenv("RUN_VERBA_TEST"):
            self.skipTest("Skipping verba endpoint integration test - RUN_VERBA_TEST not set")

    def test_verba_endpoint(self):
        # Run curl command to fetch the verba endpoint
        command = ["curl", "-s", "http://localhost:8080/v1/verba"]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode("utf-8").strip()

        # Try parsing the output as JSON
        try:
            data = json.loads(output)
        except Exception as e:
            self.fail(f"Response from /v1/verba is not valid JSON: {e}\\nOutput was: {output}")

        # Assert that the JSON response contains a 'classes' key
        self.assertIn("classes", data, "JSON response does not contain 'classes' key")

        # Check that at least one class name in the response starts with 'VERBA_'
        classes = data["classes"]
        self.assertIsInstance(classes, list, "'classes' key is not a list")
        verba_found = any(isinstance(item, dict) and "class" in item and item["class"].startswith("VERBA_") for item in classes)
        self.assertTrue(verba_found, "No class starting with 'VERBA_' found in the response")

if __name__ == '__main__':
    unittest.main()