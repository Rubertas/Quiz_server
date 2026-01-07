import json
import struct
import socket
from typing import Optional

def _recvall(conn: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            return b""
        data += chunk
    return data

def recv_json(conn: socket.socket) -> Optional[dict]:
    header = _recvall(conn, 4)
    if not header:
        return None
    (length,) = struct.unpack(">I", header)
    body = _recvall(conn, length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))

def send_json(conn: socket.socket, obj: dict) -> None:
    body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    conn.sendall(struct.pack(">I", len(body)) + body)
