import json
import os
import re
import socket
import subprocess
import sys
import threading
import time

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from game.questions import gauti_atsitiktini_klausima, klausimas_i_payload, ar_teisingas

HOST = "0.0.0.0"
PORT = 7777
MAX_NUM_OF_CLIENTS = 10
ANSWER_WINDOW_S = 30
NEXT_DELAY_S = 10
TOTAL_QUESTIONS = 10

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

local_ip = socket.gethostbyname(socket.gethostname())

def get_wifi_name():
    try:
        output = subprocess.check_output(
            ["iw", "dev"],
            stderr=subprocess.DEVNULL
        ).decode()
        match = re.search(r"ssid (.+)", output)
        return match.group(1) if match else None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

print(f"Prisijunk Per: {get_wifi_name()}")
print(f"Local IP: {local_ip}")
print(f"PORT: {PORT}")

state_lock = threading.Lock()
clients = {}  # conn -> {"id": int, "name": str, "score": int}
next_client_id = 1
game_active = False
current_qid = None
round_deadline = 0.0
answers = {}  # client_id -> (choice, recv_time)
start_event = threading.Event()

def send_json(conn, message):
    data = json.dumps(message).encode() + b"\n"
    conn.sendall(data)

def broadcast(message):
    for conn in list(clients.keys()):
        try:
            send_json(conn, message)
        except OSError:
            remove_client(conn)

def scoreboard_snapshot():
    with state_lock:
        items = [
            {"clientId": info["id"], "name": info["name"], "points": info["score"]}
            for info in clients.values()
        ]
    items.sort(key=lambda x: (-x["points"], x["name"]))
    return items

def remove_client(conn):
    with state_lock:
        clients.pop(conn, None)
    try:
        conn.close()
    except OSError:
        pass
    broadcast({"type": "scoreboard", "scoreboard": scoreboard_snapshot()})
    broadcast({"type": "players", "count": len(clients)})

def start_game():
    global game_active, current_qid, round_deadline, answers
    with state_lock:
        for info in clients.values():
            info["score"] = 0
        answers = {}
        current_qid = None
        round_deadline = 0.0
        game_active = True
    broadcast({"type": "scoreboard", "scoreboard": scoreboard_snapshot()})
    start_event.set()

def game_loop():
    global game_active, current_qid, round_deadline, answers
    while True:
        start_event.wait()

        for round_idx in range(TOTAL_QUESTIONS):
            with state_lock:
                if not game_active:
                    break

            q = gauti_atsitiktini_klausima()
            qid = q["klausimo_id"]
            deadline = time.time() + ANSWER_WINDOW_S

            with state_lock:
                current_qid = qid
                round_deadline = deadline
                answers = {}

            payload = klausimas_i_payload(
                q,
                duration_ms=ANSWER_WINDOW_S * 1000,
                deadline_ms=int(deadline * 1000),
            )
            payload["round"] = round_idx + 1
            payload["totalRounds"] = TOTAL_QUESTIONS
            payload["type"] = "question"
            broadcast(payload)

            while time.time() < deadline:
                time.sleep(0.05)

            with state_lock:
                answers_snapshot = dict(answers)
                players_snapshot = {info["id"]: info["name"] for info in clients.values()}

            first_correct_id = None
            first_correct_time = None
            for client_id, (choice, t_recv) in answers_snapshot.items():
                if ar_teisingas(q, choice):
                    if first_correct_time is None or t_recv < first_correct_time:
                        first_correct_time = t_recv
                        first_correct_id = client_id

            results = []
            with state_lock:
                for client_id, name in players_snapshot.items():
                    if client_id in answers_snapshot:
                        choice, t_recv = answers_snapshot[client_id]
                        ok = ar_teisingas(q, choice)
                        got_point = ok and client_id == first_correct_id
                        if got_point:
                            for info in clients.values():
                                if info["id"] == client_id:
                                    info["score"] += 1
                                    break
                        result = {
                            "clientId": client_id,
                            "name": name,
                            "choice": choice,
                            "ok": ok,
                            "point": got_point,
                            "timeMs": int(t_recv * 1000),
                        }
                        if not ok:
                            result["reason"] = "wrong"
                        results.append(result)
                    else:
                        results.append(
                            {
                                "clientId": client_id,
                                "name": name,
                                "ok": False,
                                "reason": "dnf",
                            }
                        )

            broadcast(
                {
                    "type": "round_end",
                    "questionId": qid,
                    "round": round_idx + 1,
                    "totalRounds": TOTAL_QUESTIONS,
                    "results": results,
                    "scoreboard": scoreboard_snapshot(),
                }
            )

            if round_idx < TOTAL_QUESTIONS - 1:
                broadcast({"type": "next_in", "delayMs": NEXT_DELAY_S * 1000})
                time.sleep(NEXT_DELAY_S)

        scoreboard = scoreboard_snapshot()
        winner = scoreboard[0] if scoreboard else {"name": "", "points": 0, "clientId": None}
        broadcast(
            {
                "type": "game_over",
                "winnerId": winner.get("clientId"),
                "winnerName": winner.get("name", ""),
                "winnerPoints": winner.get("points", 0),
                "scoreboard": scoreboard,
            }
        )

        with state_lock:
            game_active = False
            current_qid = None
            round_deadline = 0.0
            answers = {}
        start_event.clear()

def handle_client(conn, addr):
    buffer = b""
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    msg_json = json.loads(line.decode())
                except json.JSONDecodeError:
                    continue

                msg_type = msg_json.get("type")
                var = msg_json.get("variable")

                if msg_type == "name":
                    name = str(var or "").strip()
                    if not name:
                        send_json(conn, {"type": "error", "message": "name_required"})
                        continue
                    global next_client_id
                    with state_lock:
                        clients[conn] = {"id": next_client_id, "name": name, "score": 0}
                        next_client_id += 1
                    send_json(conn, {"type": "join_ok"})
                    broadcast({"type": "players", "count": len(clients)})
                    broadcast({"type": "scoreboard", "scoreboard": scoreboard_snapshot()})

                elif msg_type == "start":
                    with state_lock:
                        if game_active:
                            send_json(conn, {"type": "error", "message": "game_already_active"})
                            continue
                    start_game()
                    send_json(conn, {"type": "start_ok"})

                elif msg_type == "answer":
                    choice = msg_json.get("choice") or var
                    if choice is None:
                        send_json(conn, {"type": "error", "message": "answer_missing"})
                        continue
                    choice = str(choice).strip().upper()
                    if choice not in ["A", "B", "C", "D"]:
                        send_json(conn, {"type": "error", "message": "bad_answer_format"})
                        continue
                    now = time.time()
                    with state_lock:
                        if not game_active:
                            send_json(conn, {"type": "answer_ack", "ok": False, "reason": "game_not_active"})
                            continue
                        if current_qid is None:
                            send_json(conn, {"type": "answer_ack", "ok": False, "reason": "no_question"})
                            continue
                        if now > round_deadline:
                            send_json(conn, {"type": "answer_ack", "ok": False, "reason": "too_late"})
                            continue
                        client_id = clients.get(conn, {}).get("id")
                        if client_id is None:
                            send_json(conn, {"type": "answer_ack", "ok": False, "reason": "not_joined"})
                            continue
                        if client_id not in answers:
                            answers[client_id] = (choice, now)
                    send_json(conn, {"type": "answer_ack", "ok": True})

                elif msg_type == "exit":
                    send_json(conn, {"type": "bye"})
                    return

        except ConnectionResetError:
            break

    remove_client(conn)

threading.Thread(target=game_loop, daemon=True).start()

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
