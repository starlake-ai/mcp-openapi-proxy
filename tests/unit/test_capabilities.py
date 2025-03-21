import os
import asyncio
import pytest
from mcp_openapi_proxy.server_lowlevel import start_server
from unittest.mock import patch, AsyncMock

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.delenv("OPENAPI_SPEC_URL", raising=False)
    monkeypatch.setenv("OPENAPI_SPEC_URL", "http://dummy.com")

def dummy_stdio_server():
    class DummyAsyncCM:
        async def __aenter__(self):
            return (AsyncMock(), AsyncMock())
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    return DummyAsyncCM()

def test_capabilities_in_start_server(mock_env):
    with patch('mcp_openapi_proxy.server_lowlevel.stdio_server', new=dummy_stdio_server):
        with patch('mcp_openapi_proxy.server_lowlevel.mcp.run', new_callable=AsyncMock) as mock_run:
            asyncio.run(start_server())
            init_options = mock_run.call_args[1]["initialization_options"]
            assert init_options.capabilities.tools.listChanged, "Tools capability not set"
            assert init_options.capabilities.prompts.listChanged, "Prompts capability not set"
            assert init_options.capabilities.resources.listChanged, "Resources capability not set"
