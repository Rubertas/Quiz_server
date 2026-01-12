Quiz Server Protocol (newline JSON)

Transport
- TCP, one JSON object per line (ends with "\n")
- Server listens on HOST/PORT configured in `server/server.py`

Server behavior overview (from `server/server.py`)
- Max clients: 10 (server rejects new joins with server_full)
- Game has 10 questions per session
- Answer window: 30 seconds
- Delay between questions: 10 seconds
- A player must register with name + gender before playing
- Gender accepted: male/female plus aliases (m/f, vyras/moteris)
- One answer per player per question (first answer counts)
- Round ends early if all active players answered (delay still applies)
- Rate limit: 6 messages per second per client (errors with rate_limited)
- Score: correct answer is 20-100 based on time, wrong is 0, dnf is -10
- Streak bonus: +10 per consecutive correct after the first (max +40)
- joined_late gives 0 points (joined after question start)

Question behavior (from `game/questions.py`)
- Questions are sampled without repeats
- Choices are shuffled every time (correct answer letter updated)
- Answer choices are always A/B/C/D
- Answer messages do not include questionId (server matches current question)

Client -> Server
- name (register)
  {"type":"name","variable":"Vardas","gender":"male|female"}
- start (start game)
  {"type":"start"}
- answer (submit answer)
  {"type":"answer","choice":"A"}
- exit (disconnect)
  {"type":"exit"}

Server -> Client
- join_ok (registration ok)
  {"type":"join_ok"}
- start_ok (game start accepted)
  {"type":"start_ok"}
- players (current player count)
  {"type":"players","count":3}
- scoreboard (current scores)
  {"type":"scoreboard","scoreboard":[{"clientId":1,"name":"Vardas","points":2}]}
- question (new question)
  {
    "type":"question",
    "questionId":123,
    "text":"Klausimas...",
    "choices":["A","B","C","D"],
    "durationMs":30000,
    "deadlineMs":1700000000000,
    "round":1,
    "totalRounds":10
  }
  Notes:
  - Late joiners may receive the current question with reduced durationMs.
- answer_ack (answer accepted or rejected)
  {"type":"answer_ack","ok":true}
  {"type":"answer_ack","ok":false,"reason":"game_not_active|no_question|too_late|not_joined|already_answered"}
- round_end (end of round)
  {
    "type":"round_end",
    "questionId":123,
    "round":1,
    "totalRounds":10,
    "results":[
      {"clientId":1,"name":"Vardas","choice":"A","ok":true,"point":true,"points":85,"timeMs":1700000000123}
    ],
    "scoreboard":[{"clientId":1,"name":"Vardas","points":2}]
  }
results.reason: "wrong" | "dnf" | "joined_late"
  results.point is true when points > 0
  results.timeMs is present only for players who answered
  Points:
  - correct: 20-100 based on time
  - wrong: 0
  - dnf: -10 (no answer in time)
  - joined_late: 0 (joined after question start)
  results.streakBonus is included for correct answers when bonus > 0
- next_in (delay before next question)
  {"type":"next_in","delayMs":10000}
- game_over (game finished)
  {
    "type":"game_over",
    "winnerId":1,"winnerName":"Vardas","winnerPoints":7,
    "secondId":2,"secondName":"Antras","secondPoints":5,
    "thirdId":3,"thirdName":"Trecias","thirdPoints":4,
    "scoreboard":[...]
  }
- error (errors)
  {"type":"error","message":"name_required|gender_required|bad_gender|server_full|game_already_active|no_players|answer_missing|bad_answer_format|rate_limited"}
- bye (disconnect ok)
  {"type":"bye"}
