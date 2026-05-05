"""Marvelous Designer side listener.

Run this inside MD's Python console to expose a localhost JSON-line socket
that the MCP server connects to. Thread-safety / main-thread marshaling is
intentionally NOT handled here yet -- this is a skeleton to be revised once
the API/threading probes finish.
"""
from __future__ import annotations

import contextlib
import io
import json
import socket
import threading
import traceback

HOST = "127.0.0.1"
PORT = 7421

_persistent_globals: dict = {"__name__": "__md_mcp__"}
_server_thread: threading.Thread | None = None
_stop = threading.Event()


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
    return {
        "stdout": out.getvalue(),
        "stderr": err.getvalue(),
        "result": result,
        "error": error,
    }


HANDLERS = {
    "ping": _handle_ping,
    "execute_python": _handle_execute_python,
}


def _serve_one(conn: socket.socket) -> None:
    with conn:
        buf = bytearray()
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf.extend(chunk)
        line, _ = bytes(buf).split(b"\n", 1)
        try:
            req = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as e:
            conn.sendall((json.dumps({"id": None, "error": f"bad json: {e}"}) + "\n").encode())
            return

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        handler = HANDLERS.get(method)
        if handler is None:
            resp = {"id": req_id, "error": f"unknown method: {method}"}
        else:
            try:
                resp = {"id": req_id, "result": handler(params)}
            except Exception:
                resp = {"id": req_id, "error": traceback.format_exc()}
        conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))


def _serve_forever() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(4)
        srv.settimeout(0.5)
        while not _stop.is_set():
            try:
                conn, _addr = srv.accept()
            except socket.timeout:
                continue
            try:
                _serve_one(conn)
            except Exception:
                traceback.print_exc()


def start() -> None:
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        print(f"[md-mcp] already running on {HOST}:{PORT}")
        return
    _stop.clear()
    _server_thread = threading.Thread(target=_serve_forever, name="md-mcp-listener", daemon=True)
    _server_thread.start()
    print(f"[md-mcp] listening on {HOST}:{PORT}")


def stop() -> None:
    _stop.set()
    print("[md-mcp] stop requested")


if __name__ == "__main__":
    start()
