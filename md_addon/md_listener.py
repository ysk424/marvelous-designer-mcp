"""Marvelous Designer side MCP listener (blocking, runs on MD's main thread).

MD's embedded Python (3.11) does not give CPU to background daemon threads, so
the old thread-based server never actually bound a socket. This version runs a
plain blocking accept loop on whatever thread the Python Editor uses (the main
GUI thread). While it runs, MD's GUI is unresponsive; it stops when a client
sends {"method": "shutdown"} (the MCP server exposes a `shutdown_listener`
tool for that). To stop it without a client, close Marvelous Designer.

How to start it (paste into MD's Python Editor, or use scripts/md_start_listener.py):

    import sys
    sys.path.insert(0, r"C:\\Users\\azoo\\git\\marvelous-designer-mcp\\md_addon")
    import importlib, md_listener
    importlib.reload(md_listener)          # pick up edits without restarting MD
    md_listener.serve_forever()

Wire protocol: one JSON object per line over TCP 127.0.0.1:7421.
    Request:  {"id": str, "method": str, "params": dict}
    Response: {"id": str, "result": any}  or  {"id": str, "error": str}

Note: MD's API is exposed as importable modules (import_api, export_api,
fabric_api, pattern_api, utility_api, ...), NOT as globals. Code sent via
execute_python must `import` whatever it needs and bind its return value to a
name called `result`.
"""
from __future__ import annotations

import contextlib
import io
import json
import socket
import traceback

HOST = "127.0.0.1"
PORT = 7421

# Persists across execute_python calls within one listener session.
_persistent_globals: dict = {"__name__": "__md_mcp__"}


def _handle_ping(_params: dict) -> dict:
    return {"pong": True}


def _handle_execute_python(params: dict) -> dict:
    code = params.get("code", "")
    out, err = io.StringIO(), io.StringIO()
    result = None
    error = None
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            exec(code, _persistent_globals)
        result = _persistent_globals.get("result")
    except Exception:
        error = traceback.format_exc()
    payload = {"stdout": out.getvalue(), "stderr": err.getvalue(), "result": result, "error": error}
    try:
        json.dumps(payload)
    except TypeError:
        payload["result"] = repr(result)
    return payload


HANDLERS = {
    "ping": _handle_ping,
    "execute_python": _handle_execute_python,
}


def _read_line(conn: socket.socket) -> bytes | None:
    buf = bytearray()
    while b"\n" not in buf:
        chunk = conn.recv(65536)
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf).split(b"\n", 1)[0]


def _serve_conn(conn: socket.socket) -> bool:
    """Handle one request on one connection. Returns False iff shutdown was requested.

    The MCP-side bridge opens a fresh connection per call, so one request per
    connection is all that's needed (and avoids odd Windows socket-reuse issues).
    """
    with conn:
        line = _read_line(conn)
        if line is None:
            return True  # client connected then closed without sending anything
        try:
            req = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as e:
            conn.sendall((json.dumps({"id": None, "error": f"bad json: {e}"}) + "\n").encode())
            return True

        req_id = req.get("id")
        method = req.get("method")
        if method == "shutdown":
            conn.sendall((json.dumps({"id": req_id, "result": {"bye": True}}) + "\n").encode())
            return False

        handler = HANDLERS.get(method)
        if handler is None:
            resp = {"id": req_id, "error": f"unknown method: {method}"}
        else:
            try:
                resp = {"id": req_id, "result": handler(req.get("params") or {})}
            except Exception:
                resp = {"id": req_id, "error": traceback.format_exc()}
        conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
        return True


def serve_forever() -> None:
    """Blocking listener loop. Call this from MD's Python Editor.

    Blocks the MD GUI until a client sends {"method": "shutdown"}.
    """
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(4)
    except OSError as e:
        # Most commonly: port already in use (a previous listener is still running).
        raise RuntimeError(f"[md-mcp] cannot bind {HOST}:{PORT} ({e}) -- is a listener already running?") from e

    print(f"[md-mcp] listening (blocking) on {HOST}:{PORT} -- MD GUI frozen until a client sends 'shutdown'")
    try:
        with srv:
            while True:
                conn, _addr = srv.accept()
                try:
                    keep_going = _serve_conn(conn)
                except Exception:
                    traceback.print_exc()
                    keep_going = True
                if not keep_going:
                    break
    finally:
        print("[md-mcp] stopped")


if __name__ == "__main__":
    serve_forever()
