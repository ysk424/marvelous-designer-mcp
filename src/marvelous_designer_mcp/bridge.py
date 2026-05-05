import json
import socket
import uuid
from typing import Any

from .config import MD_HOST, MD_PORT, MD_TIMEOUT


class BridgeError(RuntimeError):
    pass


def _recv_line(sock: socket.socket) -> bytes:
    buf = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise BridgeError("connection closed before response")
        buf.extend(chunk)
        if b"\n" in chunk:
            break
    return bytes(buf).split(b"\n", 1)[0]


def call(method: str, params: dict[str, Any] | None = None, *, timeout: float | None = None) -> Any:
    """Send a JSON request to the MD listener and return the result.

    Wire format: one JSON object per line.
    Request:  {"id": str, "method": str, "params": dict}
    Response: {"id": str, "result": any} or {"id": str, "error": str}
    """
    payload = {
        "id": uuid.uuid4().hex,
        "method": method,
        "params": params or {},
    }
    data = (json.dumps(payload) + "\n").encode("utf-8")

    with socket.create_connection((MD_HOST, MD_PORT), timeout=timeout or MD_TIMEOUT) as sock:
        sock.sendall(data)
        line = _recv_line(sock)

    try:
        resp = json.loads(line.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise BridgeError(f"invalid JSON from listener: {e}") from e

    if "error" in resp:
        raise BridgeError(str(resp["error"]))
    return resp.get("result")
