import argparse
import json
import random
import socket
import threading
import time

NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hugo", "Ivy", "Jack",
    "Kara", "Liam", "Mia", "Noah", "Olivia", "Paul", "Quinn", "Ruby", "Sam", "Tina",
    "Uma", "Victor", "Wendy", "Xander", "Yara", "Zane", "Aaron", "Bella", "Caleb", "Daisy",
    "Ethan", "Fiona", "Gavin", "Hannah", "Isaac", "Jade", "Kyle", "Luna", "Mason", "Nora",
    "Owen", "Piper", "Quentin", "Riley", "Sophia", "Tyler", "Ulysses", "Violet", "Wyatt", "Zoe"
]

def random_name():
    return random.choice(NAMES)

def random_gender():
    return random.choice(["male", "female"])

class Client:
    def __init__(self, host, port, name, label, gender=None):
        self.host = host
        self.port = port
        self.name = name
        self.label = label
        self.gender = gender or random_gender()
        self.sock = None
        self.buffer = b""
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.inbox = []
        self.current_qid = None

    def log(self, msg):
        print(f"[{self.label}] {msg}", flush=True)

    def connect(self, send_name=True):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.running = True
        self.thread = threading.Thread(target=self.recv_loop, daemon=True)
        self.thread.start()
        if send_name:
            self.send({"type": "name", "variable": self.name, "gender": self.gender})
            self.log(f"connected as {self.name} ({self.gender})")
            time.sleep(0.05)
        else:
            self.log("connected without name")

    def close(self):
        self.running = False
        try:
            self.send({"type": "exit"})
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def send(self, obj):
        data = json.dumps(obj).encode() + b"\n"
        self.sock.sendall(data)

    def recv_loop(self):
        while self.running:
            try:
                data = self.sock.recv(1024)
            except OSError:
                break
            if not data:
                break
            self.buffer += data
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode())
                except json.JSONDecodeError:
                    self.log("bad json from server")
                    continue
                if msg.get("type") == "question":
                    self.current_qid = msg.get("questionId")
                with self.lock:
                    self.inbox.append(msg)
                self.log(f"recv {msg}")

    def wait_for(self, mtype, timeout_s=5):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            with self.lock:
                for i, msg in enumerate(self.inbox):
                    if msg.get("type") == mtype:
                        return self.inbox.pop(i)
            time.sleep(0.05)
        return None

def assert_true(label, cond, details=""):
    if cond:
        print(f"[PASS] {label}", flush=True)
    else:
        print(f"[FAIL] {label} {details}", flush=True)

def safe_error(client, timeout_s=5):
    err = client.wait_for("error", timeout_s=timeout_s)
    return err.get("message") if err else None

def pregame_tests(host, port, max_clients):
    print("[TEST] no_players")
    ctrl = Client(host, port, "CONTROL", "CTRL")
    ctrl.connect(send_name=False)
    ctrl.send({"type": "start"})
    err_msg = safe_error(ctrl, timeout_s=5)
    assert_true("no_players", err_msg == "no_players")

    print("[TEST] join_ok + players + scoreboard")
    ctrl.send({"type": "name", "variable": ctrl.name, "gender": ctrl.gender})
    assert_true("join_ok", ctrl.wait_for("join_ok") is not None)
    assert_true("players_received", ctrl.wait_for("players") is not None)
    assert_true("scoreboard_received", ctrl.wait_for("scoreboard") is not None)
    time.sleep(0.1)

    print("[TEST] answer_missing / bad_answer_format (no game)")
    ctrl.send({"type": "answer"})
    assert_true("answer_missing", safe_error(ctrl) == "answer_missing")
    time.sleep(0.05)
    ctrl.send({"type": "answer", "choice": "Z"})
    assert_true("bad_answer_format", safe_error(ctrl) == "bad_answer_format")
    time.sleep(0.05)

    print("[TEST] not_joined (no game)")
    ghost = Client(host, port, "GHOST", "GHOST")
    ghost.connect(send_name=False)
    ghost.send({"type": "answer", "choice": "A"})
    ack = ghost.wait_for("answer_ack")
    assert_true("not_joined", ack and ack.get("reason") == "not_joined")
    ghost.close()

    print("[TEST] server_full")
    extras = []
    for i in range(max_clients + 1):
        c = Client(host, port, random_name(), f"E{i}")
        c.connect()
        extras.append(c)
        time.sleep(0.1)
    server_full = False
    for c in extras:
        if safe_error(c, timeout_s=2) == "server_full":
            server_full = True
            break
    assert_true("server_full", server_full)
    for c in extras:
        c.close()

    return ctrl

def manual_session(ctrl, host, port):
    print("[MANUAL] start the game yourself")
    print("Commands: start | A/B/C/D | exit")
    late_bot_done = False
    answered_rounds = 0
    try:
        while True:
            msg = ctrl.wait_for("question", timeout_s=0.1)
            if msg:
                answered_rounds += 1
                if answered_rounds == 3 and not late_bot_done:
                    late = Client(host, port, "LATE_JOIN", "LATE_JOIN")
                    late.connect()
                    time.sleep(0.2)
                    late.send({"type": "answer", "choice": random.choice(["A", "B", "C", "D"])})
                    late.close()
                    late_bot_done = True

            cmd = input("> ").strip().upper()
            if cmd == "START":
                ctrl.send({"type": "start"})
            elif cmd in ["A", "B", "C", "D"]:
                ctrl.send({"type": "answer", "choice": cmd})
            elif cmd == "EXIT":
                break
            elif cmd == "":
                continue
            else:
                print("Unknown command")
    except KeyboardInterrupt:
        pass

def main():
    parser = argparse.ArgumentParser(description="Quiz server pregame test + manual play")
    parser.add_argument("host", nargs="?", default="192.168.4.1", help="Server IP")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--max-clients", type=int, default=10)
    args = parser.parse_args()

    ctrl = pregame_tests(args.host, args.port, args.max_clients)
    manual_session(ctrl, args.host, args.port)
    ctrl.close()

if __name__ == "__main__":
    main()
