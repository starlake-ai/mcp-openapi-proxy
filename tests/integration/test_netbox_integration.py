import os
import pytest
import requests

@pytest.mark.integration
class TestNetboxIntegration:
    @classmethod
    def setup_class(cls):
        # Set up environment to use the NetBox config
        cls.base_url = os.environ.get("SERVER_URL_OVERRIDE", "http://localhost:8000/api")
        cls.token = os.environ["NETBOX_API_KEY"]
        cls.headers = {"Authorization": f"Token {cls.token}"}

    def test_devices_list(self):
        """Test the /dcim/devices/ endpoint (list devices)"""
        resp = requests.get(f"{self.base_url}/dcim/devices/", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_ip_addresses_list(self):
        """Test the /ipam/ip-addresses/ endpoint (list IP addresses)"""
        resp = requests.get(f"{self.base_url}/ipam/ip-addresses/", headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "results" in data
        assert isinstance(data["results"], list)
