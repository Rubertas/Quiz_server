import time
from questions import gauti_atsitiktini_klausima, klausimas_i_payload, ar_teisingas
from game.state import GameState
from game import protocol as P

def start_game_loop(
    state: GameState,
    answer_window_s: int = 30,
    next_delay_s: int = 10,
    total_questions: int = 10,
):
    while True:
        # laukiam starto ir bent 1 zaidejo
        while True:
            with state.lock:
                active = state.game_active
                players = sum(1 for c in state.clients.values() if c.client_id)
            if active and players > 0:
                break
            time.sleep(0.2)

        for idx in range(total_questions):
            with state.lock:
                if not state.game_active:
                    break
                state.asked_count = idx + 1

            q = gauti_atsitiktini_klausima()
            qid = q["klausimo_id"]

            with state.lock:
                state.current_question = q
                state.current_qid = qid
                state.answers = {}
                state.round_deadline = time.time() + answer_window_s
                deadline_ms = int(state.round_deadline * 1000)

            payload = klausimas_i_payload(
                q,
                duration_ms=answer_window_s * 1000,
                deadline_ms=deadline_ms,
            )
            payload["round"] = idx + 1
            payload["totalRounds"] = total_questions
            state.broadcast(payload)

            # laukiam iki deadline
            while time.time() < state.round_deadline:
                time.sleep(0.05)

            # snapshot + score update
            with state.lock:
                answers_snapshot = dict(state.answers)
                scores_snapshot = dict(state.scores)
                players_snapshot = {
                    client.client_id: client.name
                    for client in state.clients.values()
                    if client.client_id
                }

            first_correct_id = None
            first_correct_time = None
            for client_id, (choice, t_recv) in answers_snapshot.items():
                if ar_teisingas(q, choice):
                    if first_correct_time is None or t_recv < first_correct_time:
                        first_correct_time = t_recv
                        first_correct_id = client_id

            results = []
            for client_id, name in players_snapshot.items():
                if client_id in answers_snapshot:
                    choice, t_recv = answers_snapshot[client_id]
                    ok = ar_teisingas(q, choice)
                    got_point = ok and client_id == first_correct_id
                    if got_point:
                        scores_snapshot[client_id] = scores_snapshot.get(client_id, 0) + 1
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

            with state.lock:
                state.scores = scores_snapshot

            scoreboard = [
                {"clientId": cid, "name": players_snapshot.get(cid, ""), "points": pts}
                for cid, pts in sorted(
                    scores_snapshot.items(),
                    key=lambda x: (-x[1], players_snapshot.get(x[0], "")),
                )
            ]

            state.broadcast(
                {
                    "type": P.TYPE_ROUND_END,
                    "questionId": qid,
                    "round": idx + 1,
                    "totalRounds": total_questions,
                    "results": results,
                    "scoreboard": scoreboard,
                }
            )

            if idx < total_questions - 1:
                state.broadcast({"type": P.TYPE_NEXT_IN, "delayMs": next_delay_s * 1000})
                time.sleep(next_delay_s)

        with state.lock:
            final_scores = dict(state.scores)
            players_snapshot = {
                client.client_id: client.name
                for client in state.clients.values()
                if client.client_id
            }
            state.game_active = False
            state.current_question = None
            state.current_qid = None
            state.round_deadline = 0.0
            state.answers = {}

        winner_id = None
        winner_points = None
        for cid, pts in sorted(
            final_scores.items(),
            key=lambda x: (-x[1], players_snapshot.get(x[0], "")),
        ):
            winner_id = cid
            winner_points = pts
            break

        final_scoreboard = [
            {"clientId": cid, "name": players_snapshot.get(cid, ""), "points": pts}
            for cid, pts in sorted(
                final_scores.items(),
                key=lambda x: (-x[1], players_snapshot.get(x[0], "")),
            )
        ]

        state.broadcast(
            {
                "type": P.TYPE_GAME_OVER,
                "winnerId": winner_id,
                "winnerName": players_snapshot.get(winner_id, "") if winner_id else "",
                "winnerPoints": winner_points if winner_points is not None else 0,
                "scoreboard": final_scoreboard,
            }
        )
