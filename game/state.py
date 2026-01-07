from dataclasses import dataclass, field
import threading
from typing import Dict, Tuple, Optional
import socket

from server.framing import send_json

@dataclass
class Client:
    conn: socket.socket
    addr: Tuple[str, int]
    client_id: str = ""
    name: str = ""

@dataclass
class GameState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    clients: Dict[socket.socket, Client] = field(default_factory=dict)  # conn -> Client
    scores: Dict[str, int] = field(default_factory=dict)               # clientId -> points
    game_active: bool = False
    questions_per_game: int = 10
    asked_count: int = 0

    # einamo roundo info
    current_question: Optional[dict] = None
    current_qid: Optional[int] = None
    round_deadline: float = 0.0
    answers: Dict[str, Tuple[str, float]] = field(default_factory=dict)  # clientId -> (choice, recv_time)

    def count_players(self) -> int:
        with self.lock:
            return sum(1 for c in self.clients.values() if c.client_id)

    def snapshot_scoreboard(self) -> list:
        with self.lock:
            players = {
                client.client_id: client.name
                for client in self.clients.values()
                if client.client_id
            }
            scores = dict(self.scores)
        return [
            {"clientId": cid, "name": players.get(cid, ""), "points": scores.get(cid, 0)}
            for cid, _pts in sorted(
                scores.items(),
                key=lambda x: (-x[1], players.get(x[0], "")),
            )
        ]

    def broadcast(self, obj: dict) -> None:
        with self.lock:
            conns = list(self.clients.keys())
        for c in conns:
            try:
                send_json(c, obj)
            except Exception:
                self.remove_client(c)

    def remove_client(self, conn: socket.socket) -> None:
        with self.lock:
            self.clients.pop(conn, None)
        try:
            conn.close()
        except Exception:
            pass
