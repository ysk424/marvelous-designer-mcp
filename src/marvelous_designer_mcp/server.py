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

    MD's API is exposed as importable modules (import_api, export_api, fabric_api,
    pattern_api, utility_api, ...), NOT as globals — so `import` what you need.
    Bind the value you want back to a name called `result`.

    Returns: {"stdout": str, "stderr": str, "result": any, "error": str|None}.
    """
    try:
        return bridge.call("execute_python", {"code": code})
    except bridge.BridgeError as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def shutdown_listener() -> dict:
    """Stop the MD-side listener's blocking loop and release the Marvelous Designer GUI."""
    try:
        return {"ok": True, "result": bridge.call("shutdown")}
    except bridge.BridgeError as e:
        return {"ok": False, "error": str(e)}
