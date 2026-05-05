import os

MD_HOST = os.environ.get("MD_MCP_HOST", "127.0.0.1")
MD_PORT = int(os.environ.get("MD_MCP_PORT", "7421"))
MD_TIMEOUT = float(os.environ.get("MD_MCP_TIMEOUT", "10.0"))
