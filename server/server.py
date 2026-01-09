import json
import os
import re
import socket
import subprocess
import sys
import threading
import time

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from game.questions import gauti_klausimus_be_pasikartojimu, klausimas_i_payload, ar_teisingas

HOST = "192.168.4.1"
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

def log(message, level="INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {message}", flush=True)

def log_block(title, lines):
    log(f"=== {title} ===")
    for line in lines:
        log(line)
    log(f"=== end {title} ===")

def log_blank():
    print("", flush=True)

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

log(f"Prisijunk Per: {get_wifi_name()}")
log(f"Local IP: {local_ip}")
log(f"PORT: {PORT}")

state_lock = threading.Lock()
clients = {}  # conn -> {"id": int, "name": str, "gender": str, "score": int, "streak": int, "joined_at": float}
next_client_id = 1
game_active = False
current_qid = None
current_question = None
current_round = 0
total_rounds = 0
round_deadline = 0.0
answers = {}  # client_id -> (choice, recv_time)
start_event = threading.Event()

def send_json(conn, message):
    data = json.dumps(message).encode() + b"\n"
    conn.sendall(data)

def broadcast(message):
    with state_lock:
        conns = list(clients.keys())
    msg_type = message.get("type") if isinstance(message, dict) else None
    for conn in conns:
        try:
            send_json(conn, message)
        except OSError:
            remove_client(conn)
    if msg_type:
        log(f"Broadcast -> {msg_type} (clients={len(conns)})", level="OUT")

def scoreboard_snapshot():
    with state_lock:
        items = [
            {"clientId": info["id"], "name": info["name"], "points": info["score"]}
            for info in clients.values()
        ]
    items.sort(key=lambda x: (-x["points"], x["name"]))
    return items

def remove_client(conn):
    name = clients.get(conn, {}).get("name", "unknown")
    with state_lock:
        clients.pop(conn, None)
        remaining = len(clients)
    try:
        conn.close()
    except OSError:
        pass
    log(f"Disconnected: {name} (remaining={remaining})", level="NET")
    broadcast({"type": "scoreboard", "scoreboard": scoreboard_snapshot()})
    broadcast({"type": "players", "count": len(clients)})
    if remaining == 0:
        log("No players left, server idle", level="NET")

def start_game():
    global game_active, current_qid, current_question, current_round, total_rounds, round_deadline, answers
    with state_lock:
        for info in clients.values():
            info["score"] = 0
            info["streak"] = 0
        answers = {}
        current_qid = None
        current_question = None
        current_round = 0
        total_rounds = 0
        round_deadline = 0.0
        game_active = True
    broadcast({"type": "scoreboard", "scoreboard": scoreboard_snapshot()})
    log("Game started", level="GAME")
    start_event.set()

def game_loop():
    global game_active, current_qid, current_question, current_round, total_rounds, round_deadline, answers
    while True:
        start_event.wait()

        with state_lock:
            if len(clients) == 0:
                log("Start requested but no players, server idle", level="GAME")
                start_event.clear()
                continue

        try:
            questions = gauti_klausimus_be_pasikartojimu(TOTAL_QUESTIONS)
        except ValueError as exc:
            log(f"Game aborted: {exc}")
            with state_lock:
                game_active = False
                current_qid = None
                round_deadline = 0.0
                answers = {}
            start_event.clear()
            continue
        game_cancelled = False
        total_rounds = len(questions)
        for round_idx, q in enumerate(questions):
            with state_lock:
                if len(clients) == 0:
                    game_cancelled = True
                    game_active = False
                    current_qid = None
                    current_question = None
                    current_round = 0
                    round_deadline = 0.0
                    answers = {}
                    log("No players left during game, cancelling", level="GAME")
                    break
                if not game_active:
                    break

            qid = q["klausimo_id"]
            question_start = time.time()
            deadline = question_start + ANSWER_WINDOW_S

            with state_lock:
                current_qid = qid
                current_question = q
                current_round = round_idx + 1
                round_deadline = deadline
                answers = {}
                expected_ids = {info["id"] for info in clients.values()}

            payload = klausimas_i_payload(
                q,
                duration_ms=ANSWER_WINDOW_S * 1000,
                deadline_ms=int(deadline * 1000),
            )
            payload["round"] = round_idx + 1
            payload["totalRounds"] = total_rounds
            payload["type"] = "question"
            broadcast(payload)
            log(
                f"Question sent: id={qid} round={round_idx + 1}/{len(questions)} "
                f"correct={q['teisingas_atsakymas']}",
                level="ROUND",
            )

            while True:
                now = time.time()
                if now >= deadline:
                    break
                with state_lock:
                    active_expected = {
                        info["id"]
                        for info in clients.values()
                        if info["id"] in expected_ids
                    }
                    if not active_expected:
                        break
                    if active_expected.issubset(answers.keys()):
                        break
                time.sleep(0.05)

            round_end_time = min(deadline, time.time())
            with state_lock:
                round_deadline = round_end_time

            with state_lock:
                answers_snapshot = dict(answers)
                players_snapshot = {info["id"]: info["name"] for info in clients.values()}

            results = []
            with state_lock:
                for client_id, name in players_snapshot.items():
                    if client_id in answers_snapshot:
                        choice, t_recv = answers_snapshot[client_id]
                        ok = ar_teisingas(q, choice)
                        points_awarded = 0
                        streak_bonus = 0
                        if ok:
                            reaction_s = max(
                                0.0,
                                min(ANSWER_WINDOW_S, t_recv - question_start),
                            )
                            time_bonus = int((1.0 - reaction_s / ANSWER_WINDOW_S) * 80)
                            time_bonus = max(0, min(80, time_bonus))
                            points_awarded = 20 + time_bonus
                            for info in clients.values():
                                if info["id"] == client_id:
                                    info["streak"] += 1
                                    streak_bonus = min(40, (info["streak"] - 1) * 10)
                                    points_awarded += streak_bonus
                                    info["score"] += points_awarded
                                    break
                        result = {
                            "clientId": client_id,
                            "name": name,
                            "choice": choice,
                            "ok": ok,
                            "points": points_awarded,
                            "point": points_awarded > 0,
                            "timeMs": int(t_recv * 1000),
                        }
                        if not ok:
                            for info in clients.values():
                                if info["id"] == client_id:
                                    info["streak"] = 0
                                    break
                            result["reason"] = "wrong"
                        if ok and streak_bonus:
                            result["streakBonus"] = streak_bonus
                        results.append(result)
                    else:
                        joined_at = None
                        for info in clients.values():
                            if info["id"] == client_id:
                                joined_at = info.get("joined_at")
                                break
                        if joined_at is not None and joined_at > question_start:
                            results.append(
                                {
                                    "clientId": client_id,
                                    "name": name,
                                    "ok": False,
                                    "reason": "joined_late",
                                    "points": 0,
                                    "point": False,
                                }
                            )
                            for info in clients.values():
                                if info["id"] == client_id:
                                    info["streak"] = 0
                                    break
                        else:
                            results.append(
                                {
                                    "clientId": client_id,
                                    "name": name,
                                    "ok": False,
                                    "reason": "dnf",
                                    "points": -10,
                                    "point": False,
                                }
                            )
                            for info in clients.values():
                                if info["id"] == client_id:
                                    info["score"] -= 10
                                    info["streak"] = 0
                                    break

            broadcast(
                {
                    "type": "round_end",
                    "questionId": qid,
                    "round": round_idx + 1,
                    "totalRounds": len(questions),
                    "results": results,
                    "scoreboard": scoreboard_snapshot(),
                }
            )
            log(f"Round ended: id={qid} round={round_idx + 1}/{len(questions)}", level="ROUND")
            log_block("Scoreboard", [str(scoreboard_snapshot())])
            log_blank()

            if round_idx < len(questions) - 1:
                broadcast({"type": "next_in", "delayMs": NEXT_DELAY_S * 1000})
                time.sleep(NEXT_DELAY_S)

        if not game_cancelled:
            scoreboard = scoreboard_snapshot()
            winner = scoreboard[0] if scoreboard else {"name": "", "points": 0, "clientId": None}
            second = scoreboard[1] if len(scoreboard) > 1 else {"name": "", "points": 0, "clientId": None}
            third = scoreboard[2] if len(scoreboard) > 2 else {"name": "", "points": 0, "clientId": None}
            broadcast(
                {
                    "type": "game_over",
                    "winnerId": winner.get("clientId"),
                    "winnerName": winner.get("name", ""),
                    "winnerPoints": winner.get("points", 0),
                    "secondId": second.get("clientId"),
                    "secondName": second.get("name", ""),
                    "secondPoints": second.get("points", 0),
                    "thirdId": third.get("clientId"),
                    "thirdName": third.get("name", ""),
                    "thirdPoints": third.get("points", 0),
                    "scoreboard": scoreboard,
                }
            )
            log(f"Game over: winner={winner.get('name', '')} points={winner.get('points', 0)}", level="GAME")
            log_blank()

        with state_lock:
            game_active = False
            current_qid = None
            current_question = None
            current_round = 0
            total_rounds = 0
            round_deadline = 0.0
            answers = {}
        start_event.clear()

def handle_client(conn, addr):
    log(f"Client connected: {addr}", level="NET")
    buffer = b""
    rate_window_s = 1.0
    rate_limit = 6
    rate_window_start = time.time()
    rate_count = 0
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
                    log("Invalid JSON from client", level="WARN")
                    continue
                now = time.time()
                if now - rate_window_start >= rate_window_s:
                    rate_window_start = now
                    rate_count = 0
                rate_count += 1
                if rate_count > rate_limit:
                    send_json(conn, {"type": "error", "message": "rate_limited"})
                    log(f"Rate limited client {addr}", level="WARN")
                    continue
                log(f"Received -> {msg_json}", level="IN")

                msg_type = msg_json.get("type")
                var = msg_json.get("variable")

                if msg_type == "name":
                    name = str(var or "").strip()
                    if not name:
                        send_json(conn, {"type": "error", "message": "name_required"})
                        continue
                    gender_raw = msg_json.get("gender") or msg_json.get("sex")
                    gender = str(gender_raw or "").strip().lower()
                    if not gender:
                        send_json(conn, {"type": "error", "message": "gender_required"})
                        continue
                    if gender in ["m", "male", "vyras", "v"]:
                        gender = "male"
                    elif gender in ["f", "female", "moteris"]:
                        gender = "female"
                    else:
                        send_json(conn, {"type": "error", "message": "bad_gender"})
                        continue
                    global next_client_id
                    with state_lock:
                        if len(clients) >= MAX_NUM_OF_CLIENTS:
                            send_json(conn, {"type": "error", "message": "server_full"})
                            log("Join rejected: server_full", level="NET")
                            continue
                        clients[conn] = {
                            "id": next_client_id,
                            "name": name,
                            "gender": gender,
                            "score": 0,
                            "streak": 0,
                            "joined_at": time.time(),
                        }
                        next_client_id += 1
                    send_json(conn, {"type": "join_ok"})
                    log(f"Join ok: {name} (total={len(clients)})", level="NET")
                    broadcast({"type": "players", "count": len(clients)})
                    broadcast({"type": "scoreboard", "scoreboard": scoreboard_snapshot()})
                    with state_lock:
                        if game_active and current_question and time.time() < round_deadline:
                            remaining_ms = max(0, int((round_deadline - time.time()) * 1000))
                            payload = klausimas_i_payload(
                                current_question,
                                duration_ms=remaining_ms,
                                deadline_ms=int(round_deadline * 1000),
                            )
                            payload["round"] = current_round
                            payload["totalRounds"] = total_rounds
                            payload["type"] = "question"
                            send_json(conn, payload)
                            log(f"Sent current question to late joiner: {name}", level="GAME")

                elif msg_type == "start":
                    with state_lock:
                        if game_active:
                            send_json(conn, {"type": "error", "message": "game_already_active"})
                            continue
                        if len(clients) == 0:
                            send_json(conn, {"type": "error", "message": "no_players"})
                            continue
                    start_game()
                    send_json(conn, {"type": "start_ok"})
                    log("Start ok sent", level="GAME")

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
                        if client_id in answers:
                            send_json(conn, {"type": "answer_ack", "ok": False, "reason": "already_answered"})
                            continue
                        answers[client_id] = (choice, now)
                    send_json(conn, {"type": "answer_ack", "ok": True})
                    log(f"Answer ack ok: choice={choice} clientId={client_id}", level="GAME")

                elif msg_type == "exit":
                    send_json(conn, {"type": "bye"})
                    log("Client exit", level="NET")
                    return

        except ConnectionResetError:
            break

    remove_client(conn)

threading.Thread(target=game_loop, daemon=True).start()

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
