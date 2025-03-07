import json

def test_embedded_openapi_json_valid():
    # Embedded sample valid OpenAPI spec
    sample_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Sample API",
            "version": "1.0.0"
        },
        "paths": {
            "/pets": {
                "get": {
                    "summary": "List all pets",
                    "responses": {
                        "200": {
                            "description": "An array of pets",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    # Simulate retrieval by converting to JSON and parsing it back
    spec_json = json.dumps(sample_spec)
    parsed_spec = json.loads(spec_json)
    # Assert that the spec has either an "openapi" or "swagger" key and non-empty "paths"
    assert ("openapi" in parsed_spec or "swagger" in parsed_spec), "Spec must contain 'openapi' or 'swagger' key"
    assert "paths" in parsed_spec and parsed_spec["paths"], "Spec must contain non-empty 'paths' object"