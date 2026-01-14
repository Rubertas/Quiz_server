using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;

public class ClientInfo
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string Gender { get; set; } = "";
    public int Score { get; set; }
    public int Streak { get; set; }
    public double JoinedAt { get; set; }
}

public static class Program
{
    private const string HOST = "0.0.0.0";
    private const int PORT = 7777;
    private const int MAX_NUM_OF_CLIENTS = 10;
    private const int ANSWER_WINDOW_S = 30;
    private const int NEXT_DELAY_S = 10;
    private const int TOTAL_QUESTIONS = 10;

    private static readonly object StateLock = new object();
    private static readonly Dictionary<TcpClient, ClientInfo> Clients = new Dictionary<TcpClient, ClientInfo>();
    private static int NextClientId = 1;
    private static bool GameActive = false;
    private static int? CurrentQid = null;
    private static Question CurrentQuestion = null;
    private static int CurrentRound = 0;
    private static int TotalRounds = 0;
    private static double RoundDeadline = 0.0;
    private static Dictionary<int, (string Choice, double RecvTime)> Answers =
        new Dictionary<int, (string Choice, double RecvTime)>();
    private static readonly ManualResetEventSlim StartEvent = new ManualResetEventSlim(false);

    public static void Main()
    {
        TcpListener server = new TcpListener(IPAddress.Parse(HOST), PORT);
        server.Server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        server.Start();

        string localIp = GetLocalIp();
        Log(string.Format("Prisijunk Per: {0}", GetWifiName()));
        Log(string.Format("Local IP: {0}", localIp));
        Log(string.Format("PORT: {0}", PORT));

        Thread gameThread = new Thread(GameLoop)
        {
            IsBackground = true
        };
        gameThread.Start();

        while (true)
        {
            TcpClient conn = server.AcceptTcpClient();
            Thread clientThread = new Thread(() => HandleClient(conn))
            {
                IsBackground = true
            };
            clientThread.Start();
        }
    }

    private static void Log(string message, string level = "INFO")
    {
        string ts = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
        Console.WriteLine(string.Format("[{0}] [{1}] {2}", ts, level, message));
    }

    private static void LogBlock(string title, IEnumerable<string> lines)
    {
        Log(string.Format("=== {0} ===", title));
        foreach (string line in lines)
        {
            Log(line);
        }
        Log(string.Format("=== end {0} ===", title));
    }

    private static void LogBlank()
    {
        Console.WriteLine("");
    }

    private static string GetWifiName()
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = "iw",
                Arguments = "dev",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using (Process proc = Process.Start(psi))
            {
                if (proc == null)
                {
                    return "None";
                }
                string output = proc.StandardOutput.ReadToEnd();
                proc.WaitForExit();
                Match match = Regex.Match(output, "ssid (.+)");
                return match.Success ? match.Groups[1].Value : "None";
            }
        }
        catch
        {
            return "None";
        }
    }

    private static string GetLocalIp()
    {
        try
        {
            IPAddress ip = Dns.GetHostEntry(Dns.GetHostName())
                .AddressList
                .FirstOrDefault(a => a.AddressFamily == AddressFamily.InterNetwork);
            return ip != null ? ip.ToString() : "0.0.0.0";
        }
        catch
        {
            return "0.0.0.0";
        }
    }

    private static void SendJson(TcpClient conn, object message)
    {
        string json = JsonSerializer.Serialize(message);
        byte[] data = Encoding.UTF8.GetBytes(json + "\n");
        NetworkStream stream = conn.GetStream();
        stream.Write(data, 0, data.Length);
    }

    private static void Broadcast(object message)
    {
        List<TcpClient> conns;
        lock (StateLock)
        {
            conns = Clients.Keys.ToList();
        }

        string msgType = null;
        if (message is Dictionary<string, object> dict && dict.ContainsKey("type"))
        {
            msgType = dict["type"] as string;
        }

        foreach (TcpClient conn in conns)
        {
            try
            {
                SendJson(conn, message);
            }
            catch
            {
                RemoveClient(conn);
            }
        }

        if (!string.IsNullOrEmpty(msgType))
        {
            Log(string.Format("Broadcast -> {0} (clients={1})", msgType, conns.Count), "OUT");
        }
    }

    private static List<Dictionary<string, object>> ScoreboardSnapshot()
    {
        List<Dictionary<string, object>> items = new List<Dictionary<string, object>>();
        lock (StateLock)
        {
            foreach (ClientInfo info in Clients.Values)
            {
                items.Add(new Dictionary<string, object>
                {
                    ["clientId"] = info.Id,
                    ["name"] = info.Name,
                    ["points"] = info.Score
                });
            }
        }

        items = items
            .OrderByDescending(x => (int)x["points"])
            .ThenBy(x => (string)x["name"])
            .ToList();

        return items;
    }

    private static void RemoveClient(TcpClient conn)
    {
        string name = "unknown";
        lock (StateLock)
        {
            if (Clients.ContainsKey(conn))
            {
                name = Clients[conn].Name;
                Clients.Remove(conn);
            }
        }

        try
        {
            conn.Close();
        }
        catch
        {
        }

        int remaining;
        lock (StateLock)
        {
            remaining = Clients.Count;
        }

        Log(string.Format("Disconnected: {0} (remaining={1})", name, remaining), "NET");
        Broadcast(new Dictionary<string, object> { ["type"] = "scoreboard", ["scoreboard"] = ScoreboardSnapshot() });
        Broadcast(new Dictionary<string, object> { ["type"] = "players", ["count"] = remaining });
        if (remaining == 0)
        {
            Log("No players left, server idle", "NET");
        }
    }

    private static void StartGame()
    {
        lock (StateLock)
        {
            foreach (ClientInfo info in Clients.Values)
            {
                info.Score = 0;
                info.Streak = 0;
            }
            Answers = new Dictionary<int, (string Choice, double RecvTime)>();
            CurrentQid = null;
            CurrentQuestion = null;
            CurrentRound = 0;
            TotalRounds = 0;
            RoundDeadline = 0.0;
            GameActive = true;
        }
        Broadcast(new Dictionary<string, object> { ["type"] = "scoreboard", ["scoreboard"] = ScoreboardSnapshot() });
        Log("Game started", "GAME");
        StartEvent.Set();
    }

    private static void GameLoop()
    {
        while (true)
        {
            StartEvent.Wait();

            lock (StateLock)
            {
                if (Clients.Count == 0)
                {
                    Log("Start requested but no players, server idle", "GAME");
                    StartEvent.Reset();
                    continue;
                }
            }

            List<Question> questions;
            try
            {
                questions = Questions.GautiKlausimusBePasikartojimu(TOTAL_QUESTIONS);
            }
            catch (Exception exc)
            {
                Log(string.Format("Game aborted: {0}", exc.Message));
                lock (StateLock)
                {
                    GameActive = false;
                    CurrentQid = null;
                    RoundDeadline = 0.0;
                    Answers = new Dictionary<int, (string Choice, double RecvTime)>();
                }
                StartEvent.Reset();
                continue;
            }

            bool gameCancelled = false;
            TotalRounds = questions.Count;

            for (int roundIdx = 0; roundIdx < questions.Count; roundIdx++)
            {
                Question q = questions[roundIdx];
                lock (StateLock)
                {
                    if (Clients.Count == 0)
                    {
                        gameCancelled = true;
                        GameActive = false;
                        CurrentQid = null;
                        CurrentQuestion = null;
                        CurrentRound = 0;
                        RoundDeadline = 0.0;
                        Answers = new Dictionary<int, (string Choice, double RecvTime)>();
                        Log("No players left during game, cancelling", "GAME");
                        break;
                    }
                    if (!GameActive)
                    {
                        break;
                    }
                }

                int qid = q.KlausimoId;
                double questionStart = NowSeconds();
                double deadline = questionStart + ANSWER_WINDOW_S;

                HashSet<int> expectedIds;
                lock (StateLock)
                {
                    CurrentQid = qid;
                    CurrentQuestion = q;
                    CurrentRound = roundIdx + 1;
                    RoundDeadline = deadline;
                    Answers = new Dictionary<int, (string Choice, double RecvTime)>();
                    expectedIds = new HashSet<int>(Clients.Values.Select(info => info.Id));
                }

                Dictionary<string, object> payload = Questions.KlausimasIPayload(
                    q,
                    durationMs: ANSWER_WINDOW_S * 1000,
                    deadlineMs: (int)(deadline * 1000)
                );
                payload["round"] = roundIdx + 1;
                payload["totalRounds"] = TotalRounds;
                payload["type"] = "question";
                Broadcast(payload);
                Log(string.Format(
                    "Question sent: id={0} round={1}/{2} correct={3}",
                    qid,
                    roundIdx + 1,
                    questions.Count,
                    q.TeisingasAtsakymas
                ), "ROUND");

                while (true)
                {
                    double now = NowSeconds();
                    if (now >= deadline)
                    {
                        break;
                    }
                    lock (StateLock)
                    {
                        HashSet<int> activeExpected = new HashSet<int>(
                            Clients.Values
                                .Where(info => expectedIds.Contains(info.Id))
                                .Select(info => info.Id)
                        );
                        if (activeExpected.Count == 0)
                        {
                            break;
                        }
                        if (activeExpected.IsSubsetOf(Answers.Keys))
                        {
                            break;
                        }
                    }
                    Thread.Sleep(50);
                }

                double roundEndTime = Math.Min(deadline, NowSeconds());
                lock (StateLock)
                {
                    RoundDeadline = roundEndTime;
                }

                Dictionary<int, (string Choice, double RecvTime)> answersSnapshot;
                Dictionary<int, string> playersSnapshot;
                lock (StateLock)
                {
                    answersSnapshot = new Dictionary<int, (string Choice, double RecvTime)>(Answers);
                    playersSnapshot = Clients.Values.ToDictionary(info => info.Id, info => info.Name);
                }

                List<Dictionary<string, object>> results = new List<Dictionary<string, object>>();
                lock (StateLock)
                {
                    foreach (KeyValuePair<int, string> entry in playersSnapshot)
                    {
                        int clientId = entry.Key;
                        string name = entry.Value;
                        if (answersSnapshot.ContainsKey(clientId))
                        {
                            (string choice, double tRecv) = answersSnapshot[clientId];
                            bool ok = Questions.ArTeisingas(q, choice);
                            int pointsAwarded = 0;
                            int streakBonus = 0;
                            if (ok)
                            {
                                double reactionS = Math.Max(0.0, Math.Min(ANSWER_WINDOW_S, tRecv - questionStart));
                                int timeBonus = (int)((1.0 - reactionS / ANSWER_WINDOW_S) * 80);
                                timeBonus = Math.Max(0, Math.Min(80, timeBonus));
                                pointsAwarded = 20 + timeBonus;

                                foreach (ClientInfo info in Clients.Values)
                                {
                                    if (info.Id == clientId)
                                    {
                                        info.Streak += 1;
                                        streakBonus = Math.Min(40, (info.Streak - 1) * 10);
                                        pointsAwarded += streakBonus;
                                        info.Score += pointsAwarded;
                                        break;
                                    }
                                }
                            }

                            Dictionary<string, object> result = new Dictionary<string, object>
                            {
                                ["clientId"] = clientId,
                                ["name"] = name,
                                ["choice"] = choice,
                                ["ok"] = ok,
                                ["points"] = pointsAwarded,
                                ["point"] = pointsAwarded > 0,
                                ["timeMs"] = (int)(tRecv * 1000)
                            };

                            if (!ok)
                            {
                                foreach (ClientInfo info in Clients.Values)
                                {
                                    if (info.Id == clientId)
                                    {
                                        info.Streak = 0;
                                        break;
                                    }
                                }
                                result["reason"] = "wrong";
                            }
                            if (ok && streakBonus > 0)
                            {
                                result["streakBonus"] = streakBonus;
                            }
                            results.Add(result);
                        }
                        else
                        {
                            double? joinedAt = null;
                            foreach (ClientInfo info in Clients.Values)
                            {
                                if (info.Id == clientId)
                                {
                                    joinedAt = info.JoinedAt;
                                    break;
                                }
                            }

                            if (joinedAt.HasValue && joinedAt.Value > questionStart)
                            {
                                results.Add(new Dictionary<string, object>
                                {
                                    ["clientId"] = clientId,
                                    ["name"] = name,
                                    ["ok"] = false,
                                    ["reason"] = "joined_late",
                                    ["points"] = 0,
                                    ["point"] = false
                                });
                                foreach (ClientInfo info in Clients.Values)
                                {
                                    if (info.Id == clientId)
                                    {
                                        info.Streak = 0;
                                        break;
                                    }
                                }
                            }
                            else
                            {
                                results.Add(new Dictionary<string, object>
                                {
                                    ["clientId"] = clientId,
                                    ["name"] = name,
                                    ["ok"] = false,
                                    ["reason"] = "dnf",
                                    ["points"] = -10,
                                    ["point"] = false
                                });
                                foreach (ClientInfo info in Clients.Values)
                                {
                                    if (info.Id == clientId)
                                    {
                                        info.Score -= 10;
                                        info.Streak = 0;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }

                Broadcast(new Dictionary<string, object>
                {
                    ["type"] = "round_end",
                    ["questionId"] = qid,
                    ["round"] = roundIdx + 1,
                    ["totalRounds"] = questions.Count,
                    ["results"] = results,
                    ["scoreboard"] = ScoreboardSnapshot()
                });
                Log(string.Format("Round ended: id={0} round={1}/{2}", qid, roundIdx + 1, questions.Count), "ROUND");
                LogBlock("Scoreboard", new List<string> { JsonSerializer.Serialize(ScoreboardSnapshot()) });
                LogBlank();

                if (roundIdx < questions.Count - 1)
                {
                    Broadcast(new Dictionary<string, object> { ["type"] = "next_in", ["delayMs"] = NEXT_DELAY_S * 1000 });
                    Thread.Sleep(NEXT_DELAY_S * 1000);
                }
            }

            if (!gameCancelled)
            {
                List<Dictionary<string, object>> scoreboard = ScoreboardSnapshot();
                Dictionary<string, object> winner = scoreboard.Count > 0 ? scoreboard[0] :
                    new Dictionary<string, object> { ["name"] = "", ["points"] = 0, ["clientId"] = null };
                Dictionary<string, object> second = scoreboard.Count > 1 ? scoreboard[1] :
                    new Dictionary<string, object> { ["name"] = "", ["points"] = 0, ["clientId"] = null };
                Dictionary<string, object> third = scoreboard.Count > 2 ? scoreboard[2] :
                    new Dictionary<string, object> { ["name"] = "", ["points"] = 0, ["clientId"] = null };
                Broadcast(new Dictionary<string, object>
                {
                    ["type"] = "game_over",
                    ["winnerId"] = winner.ContainsKey("clientId") ? winner["clientId"] : null,
                    ["winnerName"] = winner.ContainsKey("name") ? winner["name"] : "",
                    ["winnerPoints"] = winner.ContainsKey("points") ? winner["points"] : 0,
                    ["secondId"] = second.ContainsKey("clientId") ? second["clientId"] : null,
                    ["secondName"] = second.ContainsKey("name") ? second["name"] : "",
                    ["secondPoints"] = second.ContainsKey("points") ? second["points"] : 0,
                    ["thirdId"] = third.ContainsKey("clientId") ? third["clientId"] : null,
                    ["thirdName"] = third.ContainsKey("name") ? third["name"] : "",
                    ["thirdPoints"] = third.ContainsKey("points") ? third["points"] : 0,
                    ["scoreboard"] = scoreboard
                });
                Log(string.Format("Game over: winner={0} points={1}", winner["name"], winner["points"]), "GAME");
                LogBlank();
            }

            lock (StateLock)
            {
                GameActive = false;
                CurrentQid = null;
                CurrentQuestion = null;
                CurrentRound = 0;
                TotalRounds = 0;
                RoundDeadline = 0.0;
                Answers = new Dictionary<int, (string Choice, double RecvTime)>();
            }
            StartEvent.Reset();
        }
    }
    private static void HandleClient(TcpClient conn)
    {
        IPEndPoint endPoint = conn.Client.RemoteEndPoint as IPEndPoint;
        Log(string.Format("Client connected: {0}", endPoint), "NET");

        StringBuilder buffer = new StringBuilder();
        double rateWindowS = 1.0;
        int rateLimit = 6;
        double rateWindowStart = NowSeconds();
        int rateCount = 0;

        try
        {
            byte[] recvBuffer = new byte[1024];
            NetworkStream stream = conn.GetStream();
            while (true)
            {
                int read = stream.Read(recvBuffer, 0, recvBuffer.Length);
                if (read <= 0)
                {
                    break;
                }
                buffer.Append(Encoding.UTF8.GetString(recvBuffer, 0, read));
                while (true)
                {
                    string current = buffer.ToString();
                    int idx = current.IndexOf('\n');
                    if (idx < 0)
                    {
                        break;
                    }
                    string line = current.Substring(0, idx);
                    buffer.Remove(0, idx + 1);
                    if (line.Length == 0)
                    {
                        continue;
                    }

                    Dictionary<string, JsonElement> msgJson;
                    try
                    {
                        msgJson = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(line);
                    }
                    catch
                    {
                        Log("Invalid JSON from client", "WARN");
                        continue;
                    }

                    double now = NowSeconds();
                    if (now - rateWindowStart >= rateWindowS)
                    {
                        rateWindowStart = now;
                        rateCount = 0;
                    }
                    rateCount += 1;
                    if (rateCount > rateLimit)
                    {
                        SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "rate_limited" });
                        Log(string.Format("Rate limited client {0}", endPoint), "WARN");
                        continue;
                    }

                    Log(string.Format("Received -> {0}", line), "IN");

                    string msgType = GetString(msgJson, "type");
                    string var = GetString(msgJson, "variable");

                    if (msgType == "name")
                    {
                        string name = (var ?? GetString(msgJson, "name") ?? GetString(msgJson, "playerName") ?? "").Trim();
                        if (string.IsNullOrEmpty(name))
                        {
                            SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "name_required" });
                            continue;
                        }
                        string genderRaw = GetString(msgJson, "gender") ?? GetString(msgJson, "sex") ?? GetString(msgJson, "playerGender");
                        string gender = (genderRaw ?? "").Trim().ToLowerInvariant();
                        if (string.IsNullOrEmpty(gender))
                        {
                            SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "gender_required" });
                            continue;
                        }
                        if (gender == "m" || gender == "male" || gender == "vyras" || gender == "v")
                        {
                            gender = "male";
                        }
                        else if (gender == "f" || gender == "female" || gender == "moteris")
                        {
                            gender = "female";
                        }
                        else
                        {
                            SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "bad_gender" });
                            continue;
                        }

                        lock (StateLock)
                        {
                            if (Clients.Count >= MAX_NUM_OF_CLIENTS)
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "server_full" });
                                Log("Join rejected: server_full", "NET");
                                continue;
                            }
                            Clients[conn] = new ClientInfo
                            {
                                Id = NextClientId,
                                Name = name,
                                Gender = gender,
                                Score = 0,
                                Streak = 0,
                                JoinedAt = NowSeconds()
                            };
                            NextClientId += 1;
                        }

                        SendJson(conn, new Dictionary<string, object> { ["type"] = "join_ok" });
                        Log(string.Format("Join ok: {0} (total={1})", name, Clients.Count), "NET");
                        Broadcast(new Dictionary<string, object> { ["type"] = "players", ["count"] = Clients.Count });
                        Broadcast(new Dictionary<string, object> { ["type"] = "scoreboard", ["scoreboard"] = ScoreboardSnapshot() });

                        lock (StateLock)
                        {
                            if (GameActive && CurrentQuestion != null && NowSeconds() < RoundDeadline)
                            {
                                int remainingMs = Math.Max(0, (int)((RoundDeadline - NowSeconds()) * 1000));
                                Dictionary<string, object> payload = Questions.KlausimasIPayload(
                                    CurrentQuestion,
                                    durationMs: remainingMs,
                                    deadlineMs: (int)(RoundDeadline * 1000)
                                );
                                payload["round"] = CurrentRound;
                                payload["totalRounds"] = TotalRounds;
                                payload["type"] = "question";
                                SendJson(conn, payload);
                                Log(string.Format("Sent current question to late joiner: {0}", name), "GAME");
                            }
                        }
                    }
                    else if (msgType == "start")
                    {
                        lock (StateLock)
                        {
                            if (GameActive)
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "game_already_active" });
                                continue;
                            }
                            if (Clients.Count == 0)
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "no_players" });
                                continue;
                            }
                        }
                        StartGame();
                        SendJson(conn, new Dictionary<string, object> { ["type"] = "start_ok" });
                        Log("Start ok sent", "GAME");
                    }
                    else if (msgType == "answer")
                    {
                        string choice = GetString(msgJson, "choice") ?? GetString(msgJson, "answer") ?? var;
                        if (choice == null)
                        {
                            SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "answer_missing" });
                            continue;
                        }
                        choice = choice.Trim().ToUpperInvariant();
                        if (!(choice == "A" || choice == "B" || choice == "C" || choice == "D"))
                        {
                            SendJson(conn, new Dictionary<string, object> { ["type"] = "error", ["message"] = "bad_answer_format" });
                            continue;
                        }
                        double nowAnswer = NowSeconds();
                        int clientId;
                        lock (StateLock)
                        {
                            if (!GameActive)
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "answer_ack", ["ok"] = false, ["reason"] = "game_not_active" });
                                continue;
                            }
                            if (CurrentQid == null)
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "answer_ack", ["ok"] = false, ["reason"] = "no_question" });
                                continue;
                            }
                            if (nowAnswer > RoundDeadline)
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "answer_ack", ["ok"] = false, ["reason"] = "too_late" });
                                continue;
                            }
                            if (!Clients.ContainsKey(conn))
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "answer_ack", ["ok"] = false, ["reason"] = "not_joined" });
                                continue;
                            }
                            clientId = Clients[conn].Id;
                            if (Answers.ContainsKey(clientId))
                            {
                                SendJson(conn, new Dictionary<string, object> { ["type"] = "answer_ack", ["ok"] = false, ["reason"] = "already_answered" });
                                continue;
                            }
                            Answers[clientId] = (choice, nowAnswer);
                        }
                        SendJson(conn, new Dictionary<string, object> { ["type"] = "answer_ack", ["ok"] = true });
                        Log(string.Format("Answer ack ok: choice={0} clientId={1}", choice, clientId), "GAME");
                    }
                    else if (msgType == "exit")
                    {
                        SendJson(conn, new Dictionary<string, object> { ["type"] = "bye" });
                        Log("Client exit", "NET");
                        return;
                    }
                }
            }
        }
        catch (Exception)
        {
        }

        RemoveClient(conn);
    }
    private static string GetString(Dictionary<string, JsonElement> obj, string key)
    {
        if (!obj.ContainsKey(key))
        {
            return null;
        }
        JsonElement el = obj[key];
        if (el.ValueKind == JsonValueKind.String)
        {
            return el.GetString();
        }
        if (el.ValueKind == JsonValueKind.Number || el.ValueKind == JsonValueKind.True || el.ValueKind == JsonValueKind.False)
        {
            return el.GetRawText();
        }
        return null;
    }

    private static double NowSeconds()
    {
        return DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;
    }
}
