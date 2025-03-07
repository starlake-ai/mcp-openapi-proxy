import os
import json
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

ASANA_OPENAPI_URL = "https://raw.githubusercontent.com/Asana/openapi/refs/heads/master/defs/asana_oas.yaml"

def test_asana_api_functionality():
    os.environ["OPENAPI_SPEC_URL"] = ASANA_OPENAPI_URL
    os.environ["SERVER_URL_OVERRIDE"] = "https://app.asana.com/api/1.0"
    os.environ["TOOL_WHITELIST"] = "/tasks"
    os.environ["TOOL_NAME_PREFIX"] = "asana_"
    os.environ["API_AUTH_BEARER"] = os.getenv("ASANA_API_KEY", "")

    asana_api_key = os.getenv("ASANA_API_KEY")
    if not asana_api_key:
        pytest.skip("ASANA_API_KEY not set")

    headers = {"Authorization": f"Bearer {asana_api_key}"}

    # Get workspaces
    response = requests.get("https://app.asana.com/api/1.0/workspaces", headers=headers, timeout=10)
    response.raise_for_status()
    workspaces = response.json()["data"]
    assert len(workspaces) > 0, "No workspaces found"

    workspace_gid = workspaces[0]["gid"]

    # Get initial tasks
    tasks_url = f"https://app.asana.com/api/1.0/tasks?workspace={workspace_gid}&assignee=me"
    response = requests.get(tasks_url, headers=headers, timeout=10)
    response.raise_for_status()
    initial_tasks = response.json()["data"]

    # Create task if none exist
    if not initial_tasks:
        payload = {
            "data": {
                "workspace": workspace_gid,
                "name": "Integration Test Task",
                "notes": "Automated test task"
            }
        }
        create_response = requests.post(
            "https://app.asana.com/api/1.0/tasks",
            headers=headers,
            json=payload,
            timeout=10
        )
        create_response.raise_for_status()

        # Re-fetch tasks
        response = requests.get(tasks_url, headers=headers, timeout=10)
        response.raise_for_status()
        final_tasks = response.json()["data"]
    else:
        final_tasks = initial_tasks

    assert len(final_tasks) > 0, "No tasks found after potential creation"

    # Cleanup (optional)
    if not initial_tasks and final_tasks:
        test_task = next((t for t in final_tasks if t["name"] == "Integration Test Task"), None)
        if test_task:
            delete_response = requests.delete(
                f"https://app.asana.com/api/1.0/tasks/{test_task['gid']}",
                headers=headers,
                timeout=10
            )
            delete_response.raise_for_status()

if __name__ == "__main__":
    pytest.main(["-v", __file__])
