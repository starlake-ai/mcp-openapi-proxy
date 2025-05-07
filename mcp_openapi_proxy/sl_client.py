import requests


class APIClient:
    def __init__(self, base_url, api_key):
        """
        Initialize the API client.

        :param base_url: The base URL of the API.
        :param api_key: The API key for authentication.
        """
        self.base_url = base_url
        self.api_key = api_key

    def post_and_get_session_cookie(self, endpoint, payload, session_cookie=None):
        """
        Post to the API and retrieve the '_sessiondata' cookie.

        :param endpoint: The API endpoint to post to.
        :param payload: The JSON payload to send in the request body.
        :param session_cookie: Optional '_sessiondata' cookie to include in the request.
        :return: The value of the '_sessiondata' cookie, or None if not found.
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "apiKey": self.api_key
        }

        # Include the '_sessiondata' cookie if provided
        cookies = {}
        if session_cookie:
            cookies['_sessiondata'] = session_cookie

        response = requests.post(url, json=payload, headers=headers, cookies=cookies)

        # Raise an exception for HTTP errors
        response.raise_for_status()

        # Retrieve the '_sessiondata' cookie
        new_session_cookie = response.cookies.get('_sessiondata')
        return new_session_cookie

    def select_project(self, project_id, session_cookie):
        """
        Select a project using the provided project ID.

        :param project_id: The ID of the project to select.
        :param session_cookie: The '_sessiondata' cookie for authentication.
        :return: The response from the project selection API.
        """
        endpoint = f"api/v1/projects/{project_id}"
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json"
        }
        cookies = {
            "_sessiondata": session_cookie
        }

        response = requests.get(url, headers=headers, cookies=cookies)

        # Raise an exception for HTTP errors
        response.raise_for_status()

        # Retrieve the '_sessiondata' cookie
        new_session_cookie = response.cookies.get('_sessiondata')

        return response.json(), new_session_cookie

    def auth(self, base_url, api_key, existing_cookie=None):
        """
        Authenticate using the API key and optional existing cookie.

        :param base_url: The base URL of the API.
        :param api_key: The API key for authentication.
        :param existing_cookie: Optional '_sessiondata' cookie to include in the request.
        :return: The retrieved '_sessiondata' cookie, or None if not found.
        """
        endpoint = "api/v1/auth/basic/api-key-signin"
        payload = {}

        session_cookie = self.post_and_get_session_cookie(endpoint, payload, session_cookie=existing_cookie)

        if session_cookie:
            print(f"Session cookie retrieved: {session_cookie}")
        else:
            print("Session cookie '_sessiondata' not found.")

        return session_cookie


# Example usage
if __name__ == "__main__":
    base_url = "http://localhost:9000"
    api_key = "25a3c0a890e008d2532c9aabbf88772b45a895dd096488ec4b4deae858b410b1"
    existing_cookie = None  # Replace with an existing '_sessiondata' cookie if available

    # Authenticate and retrieve session cookie
    client = APIClient(base_url, api_key)
    session_cookie = client.auth(base_url, api_key, existing_cookie)

    if session_cookie:
        # Select a project
        project_id = 101
        project_response = client.select_project(project_id, session_cookie)
        print(f"Project selected: {project_response}")

