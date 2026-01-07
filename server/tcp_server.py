import socket
import threading

from framing import recv_json, send_json
from Quiz_server.game.state import GameState, Client
from game import protocol as P

def start_tcp_server(state: GameState, host: str, port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(50)
    print(f"Server listening on {host}:{port}")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=_handle_client, args=(state, conn, addr), daemon=True).start()

def _handle_client(state: GameState, conn: socket.socket, addr):
    client = Client(conn=conn, addr=addr)
    with state.lock:
        state.clients[conn] = client

    try:
        while True:
            msg = recv_json(conn)
            if msg is None:
                break

            mtype = msg.get("type")

            if mtype == P.TYPE_JOIN:
                client_id = str(msg.get("clientId", "")).strip()
                name = str(msg.get("name", "")).strip()

                if not client_id or not name:
                    send_json(conn, {"type": P.TYPE_ERROR, "message": "join_requires_clientId_and_name"})
                    continue

                with state.lock:
                    client.client_id = client_id
                    client.name = name
                    state.scores.setdefault(client_id, 0)

                send_json(conn, {"type": P.TYPE_JOIN_OK, "clientId": client_id})
                state.broadcast({"type": P.TYPE_PLAYERS, "count": state.count_players()})
                send_json(conn, {"type": P.TYPE_SCOREBOARD, "scoreboard": state.snapshot_scoreboard()})
                state.broadcast({"type": P.TYPE_SCOREBOARD, "scoreboard": state.snapshot_scoreboard()})

            elif mtype == P.TYPE_START:
                with state.lock:
                    if state.game_active:
                        send_json(conn, {"type": P.TYPE_ERROR, "message": "game_already_active"})
                        continue
                    state.game_active = True
                    state.asked_count = 0
                    state.current_question = None
                    state.current_qid = None
                    state.round_deadline = 0.0
                    state.answers = {}
                    # reset scores for a new game
                    for client in state.clients.values():
                        if client.client_id:
                            state.scores[client.client_id] = 0

                send_json(conn, {"type": P.TYPE_START_OK})
                state.broadcast({"type": P.TYPE_PLAYERS, "count": state.count_players()})
                state.broadcast({"type": P.TYPE_SCOREBOARD, "scoreboard": state.snapshot_scoreboard()})

            elif mtype == P.TYPE_ANSWER:
                client_id = str(msg.get("clientId", "")).strip()
                qid = msg.get("questionId")
                choice = str(msg.get("choice", "")).strip().upper()

                if not client_id or qid is None or choice not in ["A", "B", "C", "D"]:
                    send_json(conn, {"type": P.TYPE_ERROR, "message": "bad_answer_format"})
                    continue

                import time
                now = time.time()

                with state.lock:
                    if not state.game_active:
                        send_json(conn, {"type": P.TYPE_ANSWER_ACK, "ok": False, "reason": "game_not_active"})
                        continue
                    if state.current_qid != int(qid):
                        send_json(conn, {"type": P.TYPE_ANSWER_ACK, "ok": False, "reason": "not_current_question"})
                        continue
                    if now > state.round_deadline:
                        send_json(conn, {"type": P.TYPE_ANSWER_ACK, "ok": False, "reason": "too_late"})
                        continue
                    if client_id not in state.answers:
                        state.answers[client_id] = (choice, now)

                send_json(conn, {"type": P.TYPE_ANSWER_ACK, "ok": True, "questionId": int(qid)})

            elif mtype == P.TYPE_EXIT:
                send_json(conn, {"type": P.TYPE_BYE})
                break

            else:
                send_json(conn, {"type": P.TYPE_ERROR, "message": "unknown_type"})

    finally:
        state.remove_client(conn)
        state.broadcast({"type": P.TYPE_PLAYERS, "count": state.count_players()})
        state.broadcast({"type": P.TYPE_SCOREBOARD, "scoreboard": state.snapshot_scoreboard()})
