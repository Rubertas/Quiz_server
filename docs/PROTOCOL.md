Quiz Server Protocol (newline JSON)

Transport
- TCP, one JSON object per line (ends with "\n")
- Server listens on HOST/PORT configured in `server/server.py`

Client -> Server
- name
  {"type":"name","variable":"Vardas"}
- start
  {"type":"start"}
- answer
  {"type":"answer","choice":"A","questionId":123}
- exit
  {"type":"exit"}

Server -> Client
- join_ok
  {"type":"join_ok"}
- players
  {"type":"players","count":3}
- scoreboard
  {"type":"scoreboard","scoreboard":[{"clientId":1,"name":"Vardas","points":2}]}
- question
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
- answer_ack
  {"type":"answer_ack","ok":true}
  {"type":"answer_ack","ok":false,"reason":"game_not_active|no_question|not_current_question|too_late|not_joined"}
- round_end
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
- next_in
  {"type":"next_in","delayMs":10000}
- game_over
  {
    "type":"game_over",
    "winnerId":1,"winnerName":"Vardas","winnerPoints":7,
    "secondId":2,"secondName":"Antras","secondPoints":5,
    "thirdId":3,"thirdName":"Trecias","thirdPoints":4,
    "scoreboard":[...]
  }
- error
  {"type":"error","message":"name_required|server_full|game_already_active|no_players|answer_missing|bad_answer_format|questionId_required|bad_questionId"}
- bye
  {"type":"bye"}
