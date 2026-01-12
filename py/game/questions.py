import random

KLAUSIMAI = [
    {
        "klausimo_id": 1,
        "tekstas": "Kuris vandenynas yra didziausias pasaulyje?",
        "options": ["Atlanto vandenynas", "Ramusis vandenynas", "Indijos vandenynas", "Arkties vandenynas"],
        "teisingas_atsakymas": "B",
    },
    {
        "klausimo_id": 2,
        "tekstas": "Kuri salis garseja Eifelio bokstu?",
        "options": ["Italija", "Ispanija", "Prancuzija", "Belgija"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 3,
        "tekstas": "Kuri spalva gaunama sumaisius melyna ir geltona?",
        "options": ["Raudona", "Violetine", "Ruda", "Zalia"],
        "teisingas_atsakymas": "D",
    },
    {
        "klausimo_id": 4,
        "tekstas": "Kuri upe yra ilgiausia pasaulyje?",
        "options": ["Amazone", "Nilas", "Jangdze", "Misisipe"],
        "teisingas_atsakymas": "B",
    },
    {
        "klausimo_id": 5,
        "tekstas": "Kuris zemynas turi daugiausiai gyventoju?",
        "options": ["Afrika", "Europa", "Azija", "Pietu Amerika"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 6,
        "tekstas": "Kuris Lietuvos miestas buvo laikinoji sostine tarpukariu?",
        "options": ["Vilnius", "Kaunas", "Klaipeda", "Siauliai"],
        "teisingas_atsakymas": "B",
    },
    {
        "klausimo_id": 7,
        "tekstas": "Kuri salis turi daugiausiai gyventoju pasaulyje?",
        "options": ["Kinija", "Indija", "JAV", "Indonezija"],
        "teisingas_atsakymas": "A",
    },
    {
        "klausimo_id": 8,
        "tekstas": "Kokia busena budinga vandeniui 100 C temperaturoje?",
        "options": ["Skysta", "Kieta", "Dujine", "Plazma"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 9,
        "tekstas": "Kokia operacine sistema dazniausiai naudojama Raspberry Pi irenginiuose?",
        "options": ["Windows", "macOS", "Android", "Linux"],
        "teisingas_atsakymas": "D",
    },
    {
        "klausimo_id": 10,
        "tekstas": "Kokia planeta vadinama Raudonaja planeta?",
        "options": ["Jupiteris", "Venera", "Marsas", "Saturnas"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 11,
        "tekstas": "Kiek planetu yra Saules sistemoje?",
        "options": ["7", "8", "9", "10"],
        "teisingas_atsakymas": "B",
    },
    {
        "klausimo_id": 12,
        "tekstas": "Kuri medziaga geriausiai praleidzia elektros srove?",
        "options": ["Plastikas", "Stiklas", "Guma", "Varis"],
        "teisingas_atsakymas": "D",
    },
    {
        "klausimo_id": 13,
        "tekstas": "Kuris gyvunas gali miegoti stovedamas?",
        "options": ["Suo", "Kate", "Arklys", "Meska"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 14,
        "tekstas": "Kuri salis garseja tulpemis?",
        "options": ["Nyderlandai", "Belgija", "Vokietija", "Austrija"],
        "teisingas_atsakymas": "A",
    },
    {
        "klausimo_id": 15,
        "tekstas": "Koks gyvunas laikomas greiciausiu sausumoje?",
        "options": ["Liutas", "Antilope", "Gepardas", "Vilkas"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 16,
        "tekstas": "Kuris is siu isradimu atsirado anksciausiai?",
        "options": ["Popierius", "Spausdinimo masina", "Kompasas", "Parakas"],
        "teisingas_atsakymas": "A",
    },
    {
        "klausimo_id": 17,
        "tekstas": "Kuri valstybe pirmoji paleido dirbtini Zemes palydova?",
        "options": ["JAV", "SSRS", "Kinija", "Vokietija"],
        "teisingas_atsakymas": "B",
    },
    {
        "klausimo_id": 18,
        "tekstas": "Kuri planeta turi daugiausia ziedu?",
        "options": ["Jupiteris", "Uranas", "Saturnas", "Neptunas"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 19,
        "tekstas": "Kokia yra pagrindine fotosintezes funkcija?",
        "options": ["Isskirti deguoni", "Sugerti vandeni", "Gaminti maista naudojant sviesa", "Reguliuoti temperatura"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 20,
        "tekstas": "Kuri zmogaus kuno sistema pernesa deguoni?",
        "options": ["Nervu sistema", "Virskinimo sistema", "Kraujotakos sistema", "Endokrinine sistema"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 21,
        "tekstas": "Kuri kalba naudojama Unity scenarijams?",
        "options": ["Python", "C#", "Java", "Lua"],
        "teisingas_atsakymas": "B",
    },
    {
        "klausimo_id": 22,
        "tekstas": "Kuris is sio nera HTTP metodas?",
        "options": ["GET", "POST", "FETCH", "DELETE"],
        "teisingas_atsakymas": "C",
    },
    {
        "klausimo_id": 23,
        "tekstas": "Kiek bitu yra viename baite?",
        "options": ["4", "8", "16", "32"],
        "teisingas_atsakymas": "B",
    },
    {
        "klausimo_id": 24,
        "tekstas": "Koks TCP tikslas?",
        "options": ["Patikimas duomenu perdavimas", "Failu suspaudimas", "Grafikos renderinimas", "DNS paieska"],
        "teisingas_atsakymas": "A",
    },
    {
        "klausimo_id": 25,
        "tekstas": "Kas yra JSON?",
        "options": ["Duomenu formatas", "Grafikos variklis", "Operacine sistema", "Kompiuterinis zaidimas"],
        "teisingas_atsakymas": "A",
    },
]

def gauti_atsitiktini_klausima() -> dict:
    return _sukeisti_variantus(random.choice(KLAUSIMAI))

def _sukeisti_variantus(k: dict) -> dict:
    options = list(k["options"])
    correct_idx = ord(k["teisingas_atsakymas"].strip().upper()) - ord("A")
    if correct_idx < 0 or correct_idx >= len(options):
        return dict(k)
    correct_text = options[correct_idx]
    random.shuffle(options)
    new_correct_idx = options.index(correct_text)
    return {
        **k,
        "options": options,
        "teisingas_atsakymas": chr(ord("A") + new_correct_idx),
    }

def gauti_klausimus_be_pasikartojimu(kiekis: int) -> list:
    if kiekis != 10:
        raise ValueError("kiekis_privalo_buti_10")
    if len(KLAUSIMAI) < 10:
        raise ValueError("nepakanka_klausimu")
    return [_sukeisti_variantus(k) for k in random.sample(KLAUSIMAI, kiekis)]

def klausimas_i_payload(k: dict, duration_ms: int, deadline_ms: int) -> dict:
    return {
        "type": "question",
        "questionId": k["klausimo_id"],
        "text": k["tekstas"],
        "choices": k["options"],
        "durationMs": duration_ms,
        "deadlineMs": deadline_ms,
    }

def ar_teisingas(k: dict, choice: str) -> bool:
    return choice.strip().upper() == k["teisingas_atsakymas"]
