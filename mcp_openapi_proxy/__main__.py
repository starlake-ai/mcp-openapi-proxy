"""
Entry point for the mcp_openapi_proxy package.

This script determines which server to run based on the presence of
the OPENAPI_SIMPLE_MODE environment variable:
- Low-Level Server: For dynamic tool creation from OpenAPI spec.
- FastMCP Server: For static tool configurations defined in code.
"""
 
import os
import sys
from dotenv import load_dotenv
from mcp_openapi_proxy.utils import setup_logging
 
# Load environment variables from .env if present
load_dotenv()

def main():
    """
    Main entry point for the mcp_openapi_proxy package.

    Depending on the OPENAPI_SIMPLE_MODE environment variable, this function
    launches either:
    - Low-Level Server (dynamic tools from OpenAPI spec)
    - FastMCP Server (static tools defined in server_fastmcp.py)
    """
    # Configure logging
    DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
    logger = setup_logging(debug=DEBUG)

    logger.debug("Starting mcp_openapi_proxy package entry point.")

    # Default to Low-Level Mode unless SIMPLE_MODE is explicitly enabled
    OPENAPI_SIMPLE_MODE = os.getenv("OPENAPI_SIMPLE_MODE", "false").lower() in ("true", "1", "yes") # Default to false, enable with "true" etc.
    if OPENAPI_SIMPLE_MODE:
        logger.debug("OPENAPI_SIMPLE_MODE is enabled. Launching FastMCP Server.")
        from mcp_openapi_proxy.server_fastmcp import run_simple_server
        selected_server = run_simple_server
    else:
        logger.debug("OPENAPI_SIMPLE_MODE is disabled. Launching Low-Level Server.")
        from mcp_openapi_proxy.server_lowlevel import run_server
        selected_server = run_server

    # Run the selected server
    try:
        selected_server()
    except Exception as e:
        logger.critical("Unhandled exception occurred while running the server.", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
