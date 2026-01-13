using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;

public class Client
{
    private static readonly Random Rng = new Random();

    public string Host { get; private set; }
    public int Port { get; private set; }
    public string Name { get; private set; }
    public string Label { get; private set; }
    public string Gender { get; private set; }
    public TcpClient Sock { get; private set; }
    private readonly List<Dictionary<string, string>> _inbox = new List<Dictionary<string, string>>();
    private readonly object _lock = new object();
    private StringBuilder _buffer = new StringBuilder();
    private bool _running = false;
    private Thread _thread;

    public int? CurrentQid { get; private set; }

    public Client(string host, int port, string name, string label, string gender = null)
    {
        Host = host;
        Port = port;
        Name = name;
        Label = label;
        Gender = gender ?? RandomGender();
    }

    public void Log(string msg)
    {
        Console.WriteLine(string.Format("[{0}] {1}", Label, msg));
    }

    public void Connect(bool sendName = true)
    {
        Sock = new TcpClient();
        Sock.Connect(Host, Port);
        _running = true;
        _thread = new Thread(RecvLoop) { IsBackground = true };
        _thread.Start();
        if (sendName)
        {
            Send(new Dictionary<string, object> { ["type"] = "name", ["variable"] = Name, ["gender"] = Gender });
            Log(string.Format("connected as {0} ({1})", Name, Gender));
            Thread.Sleep(50);
        }
        else
        {
            Log("connected without name");
        }
    }

    public void Close()
    {
        _running = false;
        try
        {
            Send(new Dictionary<string, object> { ["type"] = "exit" });
        }
        catch
        {
        }
        try
        {
            Sock.Close();
        }
        catch
        {
        }
    }

    public void Send(Dictionary<string, object> obj)
    {
        string json = JsonSerializer.Serialize(obj);
        byte[] data = Encoding.UTF8.GetBytes(json + "\n");
        NetworkStream stream = Sock.GetStream();
        stream.Write(data, 0, data.Length);
    }

    private void RecvLoop()
    {
        byte[] recvBuffer = new byte[1024];
        while (_running)
        {
            int read;
            try
            {
                read = Sock.GetStream().Read(recvBuffer, 0, recvBuffer.Length);
            }
            catch
            {
                break;
            }
            if (read <= 0)
            {
                break;
            }
            _buffer.Append(Encoding.UTF8.GetString(recvBuffer, 0, read));
            while (true)
            {
                string current = _buffer.ToString();
                int idx = current.IndexOf('\n');
                if (idx < 0)
                {
                    break;
                }
                string line = current.Substring(0, idx);
                _buffer.Remove(0, idx + 1);
                if (line.Length == 0)
                {
                    continue;
                }

                Dictionary<string, string> msg;
                try
                {
                    msg = ParseMessage(line);
                }
                catch
                {
                    Log("bad json from server");
                    continue;
                }

                if (msg.ContainsKey("type") && msg["type"] == "question")
                {
                    if (msg.ContainsKey("questionId") && int.TryParse(msg["questionId"], out int qid))
                    {
                        CurrentQid = qid;
                    }
                }

                lock (_lock)
                {
                    _inbox.Add(msg);
                }
                Log(string.Format("recv {0}", line));
            }
        }
    }

    public Dictionary<string, string> WaitFor(string mtype, double timeoutS = 5.0)
    {
        double deadline = NowSeconds() + timeoutS;
        while (NowSeconds() < deadline)
        {
            lock (_lock)
            {
                for (int i = 0; i < _inbox.Count; i++)
                {
                    if (_inbox[i].ContainsKey("type") && _inbox[i]["type"] == mtype)
                    {
                        Dictionary<string, string> msg = _inbox[i];
                        _inbox.RemoveAt(i);
                        return msg;
                    }
                }
            }
            Thread.Sleep(50);
        }
        return null;
    }

    private static Dictionary<string, string> ParseMessage(string line)
    {
        Dictionary<string, string> dict = new Dictionary<string, string>();
        using (JsonDocument doc = JsonDocument.Parse(line))
        {
            foreach (JsonProperty prop in doc.RootElement.EnumerateObject())
            {
                if (prop.Value.ValueKind == JsonValueKind.String)
                {
                    dict[prop.Name] = prop.Value.GetString() ?? "";
                }
                else
                {
                    dict[prop.Name] = prop.Value.GetRawText();
                }
            }
        }
        return dict;
    }

    private static string RandomGender()
    {
        return Rng.Next(0, 2) == 0 ? "male" : "female";
    }

    private static double NowSeconds()
    {
        return DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;
    }
}

public static class TestClientProgram
{
    private static readonly List<string> NAMES = new List<string>
    {
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hugo", "Ivy", "Jack",
        "Kara", "Liam", "Mia", "Noah", "Olivia", "Paul", "Quinn", "Ruby", "Sam", "Tina",
        "Uma", "Victor", "Wendy", "Xander", "Yara", "Zane", "Aaron", "Bella", "Caleb", "Daisy",
        "Ethan", "Fiona", "Gavin", "Hannah", "Isaac", "Jade", "Kyle", "Luna", "Mason", "Nora",
        "Owen", "Piper", "Quentin", "Riley", "Sophia", "Tyler", "Ulysses", "Violet", "Wyatt", "Zoe"
    };

    private static readonly Random Rng = new Random();

    private static string RandomName()
    {
        return NAMES[Rng.Next(NAMES.Count)];
    }

    private static void AssertTrue(string label, bool cond, string details = "")
    {
        if (cond)
        {
            Console.WriteLine(string.Format("[PASS] {0}", label));
        }
        else
        {
            Console.WriteLine(string.Format("[FAIL] {0} {1}", label, details));
        }
    }

    private static string SafeError(Client client, double timeoutS = 5.0)
    {
        Dictionary<string, string> err = client.WaitFor("error", timeoutS);
        if (err == null)
        {
            return null;
        }
        return err.ContainsKey("message") ? err["message"] : null;
    }

    private static Client PregameTests(string host, int port, int maxClients)
    {
        Console.WriteLine("[TEST] no_players");
        Client ctrl = new Client(host, port, "CONTROL", "CTRL");
        ctrl.Connect(sendName: false);
        ctrl.Send(new Dictionary<string, object> { ["type"] = "start" });
        string errMsg = SafeError(ctrl, 5.0);
        AssertTrue("no_players", errMsg == "no_players");

        Console.WriteLine("[TEST] join_ok + players + scoreboard");
        ctrl.Send(new Dictionary<string, object> { ["type"] = "name", ["variable"] = ctrl.Name, ["gender"] = ctrl.Gender });
        AssertTrue("join_ok", ctrl.WaitFor("join_ok") != null);
        AssertTrue("players_received", ctrl.WaitFor("players") != null);
        AssertTrue("scoreboard_received", ctrl.WaitFor("scoreboard") != null);
        Thread.Sleep(100);

        Console.WriteLine("[TEST] answer_missing / bad_answer_format (no game)");
        ctrl.Send(new Dictionary<string, object> { ["type"] = "answer" });
        AssertTrue("answer_missing", SafeError(ctrl) == "answer_missing");
        Thread.Sleep(50);
        ctrl.Send(new Dictionary<string, object> { ["type"] = "answer", ["choice"] = "Z" });
        AssertTrue("bad_answer_format", SafeError(ctrl) == "bad_answer_format");
        Thread.Sleep(50);

        Console.WriteLine("[TEST] not_joined (no game)");
        Client ghost = new Client(host, port, "GHOST", "GHOST");
        ghost.Connect(sendName: false);
        ghost.Send(new Dictionary<string, object> { ["type"] = "answer", ["choice"] = "A" });
        Dictionary<string, string> ack = ghost.WaitFor("answer_ack");
        AssertTrue("not_joined", ack != null && ack.ContainsKey("reason") && ack["reason"] == "not_joined");
        ghost.Close();

        Console.WriteLine("[TEST] server_full");
        List<Client> extras = new List<Client>();
        for (int i = 0; i < maxClients + 1; i++)
        {
            Client c = new Client(host, port, RandomName(), string.Format("E{0}", i));
            c.Connect();
            extras.Add(c);
            Thread.Sleep(100);
        }
        bool serverFull = false;
        foreach (Client c in extras)
        {
            if (SafeError(c, 2.0) == "server_full")
            {
                serverFull = true;
                break;
            }
        }
        AssertTrue("server_full", serverFull);
        foreach (Client c in extras)
        {
            c.Close();
        }

        return ctrl;
    }
    private static void ManualSession(Client ctrl, string host, int port)
    {
        Console.WriteLine("[MANUAL] start the game yourself");
        Console.WriteLine("Commands: start | A/B/C/D | exit");
        bool lateBotDone = false;
        int answeredRounds = 0;
        try
        {
            while (true)
            {
                Dictionary<string, string> msg = ctrl.WaitFor("question", 0.1);
                if (msg != null)
                {
                    answeredRounds += 1;
                    if (answeredRounds == 3 && !lateBotDone)
                    {
                        Client late = new Client(host, port, "LATE_JOIN", "LATE_JOIN");
                        late.Connect();
                        Thread.Sleep(200);
                        string[] choices = new[] { "A", "B", "C", "D" };
                        late.Send(new Dictionary<string, object> { ["type"] = "answer", ["choice"] = choices[Rng.Next(choices.Length)] });
                        late.Close();
                        lateBotDone = true;
                    }
                }

                string cmd = Console.ReadLine();
                if (cmd == null)
                {
                    continue;
                }
                cmd = cmd.Trim().ToUpperInvariant();
                if (cmd == "START")
                {
                    ctrl.Send(new Dictionary<string, object> { ["type"] = "start" });
                }
                else if (cmd == "A" || cmd == "B" || cmd == "C" || cmd == "D")
                {
                    ctrl.Send(new Dictionary<string, object> { ["type"] = "answer", ["choice"] = cmd });
                }
                else if (cmd == "EXIT")
                {
                    break;
                }
                else if (cmd == "")
                {
                    continue;
                }
                else
                {
                    Console.WriteLine("Unknown command");
                }
            }
        }
        catch (ThreadInterruptedException)
        {
        }
    }

    private static int GetArgInt(string[] args, string name, int fallback)
    {
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == name && i + 1 < args.Length && int.TryParse(args[i + 1], out int val))
            {
                return val;
            }
        }
        return fallback;
    }

    public static void Main(string[] args)
    {
        string host = "192.168.4.1";
        if (args.Length > 0 && !args[0].StartsWith("--"))
        {
            host = args[0];
        }
        int port = GetArgInt(args, "--port", 7777);
        int maxClients = GetArgInt(args, "--max-clients", 10);

        Client ctrl = PregameTests(host, port, maxClients);
        ManualSession(ctrl, host, port);
        ctrl.Close();
    }
}
