from mcp.server.fastmcp import FastMCP

from . import bridge
from .config import MD_HOST, MD_PORT

mcp = FastMCP("marvelous-designer")


@mcp.tool()
def ping() -> dict:
    """Verify the MD listener is reachable. Returns whatever the listener echoes back."""
    try:
        result = bridge.call("ping")
        return {"ok": True, "host": MD_HOST, "port": MD_PORT, "result": result}
    except bridge.BridgeError as e:
        return {"ok": False, "host": MD_HOST, "port": MD_PORT, "error": str(e)}


@mcp.tool()
def execute_python(code: str) -> dict:
    """Execute arbitrary Python inside Marvelous Designer's interpreter.

    Returns stdout, stderr, and any value bound to a `result` name in the executed scope.
    """
    try:
        return bridge.call("execute_python", {"code": code})
    except bridge.BridgeError as e:
        return {"ok": False, "error": str(e)}
