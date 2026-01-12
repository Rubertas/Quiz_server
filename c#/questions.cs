using System;
using System.Collections.Generic;
using System.Linq;

public class Question
{
    public int KlausimoId { get; set; }
    public string Tekstas { get; set; } = "";
    public List<string> Options { get; set; } = new List<string>();
    public string TeisingasAtsakymas { get; set; } = "";
}

public static class Questions
{
    private static readonly Random Rng = new Random();

    public static readonly List<Question> KLAUSIMAI = new List<Question>
    {
        new Question
        {
            KlausimoId = 1,
            Tekstas = "Kuris vandenynas yra didziausias pasaulyje?",
            Options = new List<string> { "Atlanto vandenynas", "Ramusis vandenynas", "Indijos vandenynas", "Arkties vandenynas" },
            TeisingasAtsakymas = "B",
        },
        new Question
        {
            KlausimoId = 2,
            Tekstas = "Kuri salis garseja Eifelio bokstu?",
            Options = new List<string> { "Italija", "Ispanija", "Prancuzija", "Belgija" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 3,
            Tekstas = "Kuri spalva gaunama sumaisius melyna ir geltona?",
            Options = new List<string> { "Raudona", "Violetine", "Ruda", "Zalia" },
            TeisingasAtsakymas = "D",
        },
        new Question
        {
            KlausimoId = 4,
            Tekstas = "Kuri upe yra ilgiausia pasaulyje?",
            Options = new List<string> { "Amazone", "Nilas", "Jangdze", "Misisipe" },
            TeisingasAtsakymas = "B",
        },
        new Question
        {
            KlausimoId = 5,
            Tekstas = "Kuris zemynas turi daugiausiai gyventoju?",
            Options = new List<string> { "Afrika", "Europa", "Azija", "Pietu Amerika" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 6,
            Tekstas = "Kuris Lietuvos miestas buvo laikinoji sostine tarpukariu?",
            Options = new List<string> { "Vilnius", "Kaunas", "Klaipeda", "Siauliai" },
            TeisingasAtsakymas = "B",
        },
        new Question
        {
            KlausimoId = 7,
            Tekstas = "Kuri salis turi daugiausiai gyventoju pasaulyje?",
            Options = new List<string> { "Kinija", "Indija", "JAV", "Indonezija" },
            TeisingasAtsakymas = "A",
        },
        new Question
        {
            KlausimoId = 8,
            Tekstas = "Kokia busena budinga vandeniui 100 C temperaturoje?",
            Options = new List<string> { "Skysta", "Kieta", "Dujine", "Plazma" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 9,
            Tekstas = "Kokia operacine sistema dazniausiai naudojama Raspberry Pi irenginiuose?",
            Options = new List<string> { "Windows", "macOS", "Android", "Linux" },
            TeisingasAtsakymas = "D",
        },
        new Question
        {
            KlausimoId = 10,
            Tekstas = "Kokia planeta vadinama Raudonaja planeta?",
            Options = new List<string> { "Jupiteris", "Venera", "Marsas", "Saturnas" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 11,
            Tekstas = "Kiek planetu yra Saules sistemoje?",
            Options = new List<string> { "7", "8", "9", "10" },
            TeisingasAtsakymas = "B",
        },
        new Question
        {
            KlausimoId = 12,
            Tekstas = "Kuri medziaga geriausiai praleidzia elektros srove?",
            Options = new List<string> { "Plastikas", "Stiklas", "Guma", "Varis" },
            TeisingasAtsakymas = "D",
        },
        new Question
        {
            KlausimoId = 13,
            Tekstas = "Kuris gyvunas gali miegoti stovedamas?",
            Options = new List<string> { "Suo", "Kate", "Arklys", "Meska" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 14,
            Tekstas = "Kuri salis garseja tulpemis?",
            Options = new List<string> { "Nyderlandai", "Belgija", "Vokietija", "Austrija" },
            TeisingasAtsakymas = "A",
        },
        new Question
        {
            KlausimoId = 15,
            Tekstas = "Koks gyvunas laikomas greiciausiu sausumoje?",
            Options = new List<string> { "Liutas", "Antilope", "Gepardas", "Vilkas" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 16,
            Tekstas = "Kuris is siu isradimu atsirado anksciausiai?",
            Options = new List<string> { "Popierius", "Spausdinimo masina", "Kompasas", "Parakas" },
            TeisingasAtsakymas = "A",
        },
        new Question
        {
            KlausimoId = 17,
            Tekstas = "Kuri valstybe pirmoji paleido dirbtini Zemes palydova?",
            Options = new List<string> { "JAV", "SSRS", "Kinija", "Vokietija" },
            TeisingasAtsakymas = "B",
        },
        new Question
        {
            KlausimoId = 18,
            Tekstas = "Kuri planeta turi daugiausia ziedu?",
            Options = new List<string> { "Jupiteris", "Uranas", "Saturnas", "Neptunas" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 19,
            Tekstas = "Kokia yra pagrindine fotosintezes funkcija?",
            Options = new List<string> { "Isskirti deguoni", "Sugerti vandeni", "Gaminti maista naudojant sviesa", "Reguliuoti temperatura" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 20,
            Tekstas = "Kuri zmogaus kuno sistema pernesa deguoni?",
            Options = new List<string> { "Nervu sistema", "Virskinimo sistema", "Kraujotakos sistema", "Endokrinine sistema" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 21,
            Tekstas = "Kuri kalba naudojama Unity scenarijams?",
            Options = new List<string> { "Python", "C#", "Java", "Lua" },
            TeisingasAtsakymas = "B",
        },
        new Question
        {
            KlausimoId = 22,
            Tekstas = "Kuris is sio nera HTTP metodas?",
            Options = new List<string> { "GET", "POST", "FETCH", "DELETE" },
            TeisingasAtsakymas = "C",
        },
        new Question
        {
            KlausimoId = 23,
            Tekstas = "Kiek bitu yra viename baite?",
            Options = new List<string> { "4", "8", "16", "32" },
            TeisingasAtsakymas = "B",
        },
        new Question
        {
            KlausimoId = 24,
            Tekstas = "Koks TCP tikslas?",
            Options = new List<string> { "Patikimas duomenu perdavimas", "Failu suspaudimas", "Grafikos renderinimas", "DNS paieska" },
            TeisingasAtsakymas = "A",
        },
        new Question
        {
            KlausimoId = 25,
            Tekstas = "Kas yra JSON?",
            Options = new List<string> { "Duomenu formatas", "Grafikos variklis", "Operacine sistema", "Kompiuterinis zaidimas" },
            TeisingasAtsakymas = "A",
        },
    };

    public static Question GautiAtsitiktiniKlausima()
    {
        var q = KLAUSIMAI[Rng.Next(KLAUSIMAI.Count)];
        return SukeistiVariantus(q);
    }

    public static List<Question> GautiKlausimusBePasikartojimu(int kiekis)
    {
        if (kiekis != 10)
        {
            throw new ArgumentException("kiekis_privalo_buti_10");
        }
        if (KLAUSIMAI.Count < 10)
        {
            throw new InvalidOperationException("nepakanka_klausimu");
        }

        return KLAUSIMAI
            .OrderBy(_ => Rng.Next())
            .Take(kiekis)
            .Select(SukeistiVariantus)
            .ToList();
    }

    public static Dictionary<string, object> KlausimasIPayload(Question k, int durationMs, int deadlineMs)
    {
        return new Dictionary<string, object>
        {
            ["type"] = "question",
            ["questionId"] = k.KlausimoId,
            ["text"] = k.Tekstas,
            ["choices"] = k.Options,
            ["durationMs"] = durationMs,
            ["deadlineMs"] = deadlineMs,
        };
    }

    public static bool ArTeisingas(Question k, string choice)
    {
        return (choice ?? "").Trim().ToUpperInvariant() == k.TeisingasAtsakymas;
    }

    private static Question SukeistiVariantus(Question k)
    {
        var options = new List<string>(k.Options);
        var letter = k.TeisingasAtsakymas.Trim().ToUpperInvariant();
        if (string.IsNullOrEmpty(letter))
        {
            return CloneQuestion(k);
        }
        var correctIdx = letter[0] - 'A';
        if (correctIdx < 0 || correctIdx >= options.Count)
        {
            return CloneQuestion(k);
        }
        var correctText = options[correctIdx];
        Shuffle(options);
        var newCorrectIdx = options.IndexOf(correctText);
        return new Question
        {
            KlausimoId = k.KlausimoId,
            Tekstas = k.Tekstas,
            Options = options,
            TeisingasAtsakymas = ((char)('A' + newCorrectIdx)).ToString(),
        };
    }

    private static void Shuffle<T>(IList<T> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Rng.Next(i + 1);
            T tmp = list[i];
            list[i] = list[j];
            list[j] = tmp;
        }
    }

    private static Question CloneQuestion(Question k)
    {
        return new Question
        {
            KlausimoId = k.KlausimoId,
            Tekstas = k.Tekstas,
            Options = new List<string>(k.Options),
            TeisingasAtsakymas = k.TeisingasAtsakymas,
        };
    }
}
