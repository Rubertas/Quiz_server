import random

KLAUSIMAI = [
    {
        "klausimo_id": 1,
        "tekstas": "Kuris vandenynas yra didziausias pasaulyje?",
        "options": ["Atlanto vandenynas", "Indijos vandenynas", "Ramusis vandenynas", "Arkties vandenynas"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 2,
        "tekstas": "Kuri salis turi didziausia gyventoju skaiciu pasaulyje?",
        "options": ["JAV", "Rusija", "Indija", "Brazilija"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 3,
        "tekstas": "Kuri planeta turi daugiausia ziedu?",
        "options": ["Jupiteris", "Uranas", "Saturnas", "Neptunas"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 4,
        "tekstas": "Kokia yra pagrindine fotosintezes funkcija?",
        "options": ["Isskirti deguoni", "Sugerti vandeni", "Gaminti maista naudojant sviesa", "Reguliuoti temperatura"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 5,
        "tekstas": "Kuri zmogaus kuno sistema pernesa deguoni?",
        "options": ["Nervu sistema", "Virskinimo sistema", "Kraujotakos sistema", "Endokrinine sistema"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 6,
        "tekstas": "Kuri kalba naudojama Unity scenarijams?",
        "options": ["Python", "C#", "Java", "Lua"],
        "teisingas_atsakymas": "B"
    },
    {
        "klausimo_id": 7,
        "tekstas": "Kuris is sio nera HTTP metodas?",
        "options": ["GET", "POST", "FETCH", "DELETE"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 8,
        "tekstas": "Kiek bitu yra viename baite?",
        "options": ["4", "8", "16", "32"],
        "teisingas_atsakymas": "B"
    },
    {
        "klausimo_id": 9,
        "tekstas": "Koks TCP tikslas?",
        "options": ["Patikimas duomenu perdavimas", "Failu suspaudimas", "Grafikos renderinimas", "DNS paieska"],
        "teisingas_atsakymas": "A"
    },
    {
        "klausimo_id": 10,
        "tekstas": "Kas yra JSON?",
        "options": ["Duomenu formatas", "Grafikos variklis", "Operacine sistema", "Kompiuterinis zaidimas"],
        "teisingas_atsakymas": "A"
    }
]

def gauti_atsitiktini_klausima() -> dict:
    return random.choice(KLAUSIMAI)

def gauti_klausimus_be_pasikartojimu(kiekis: int) -> list:
    if kiekis != 10:
        raise ValueError("kiekis_privalo_buti_10")
    if len(KLAUSIMAI) < 10:
        raise ValueError("nepakanka_klausimu")
    return random.sample(KLAUSIMAI, kiekis)

def klausimas_i_payload(k: dict, duration_ms: int, deadline_ms: int) -> dict:
    return {
        "type": "question",
        "questionId": k["klausimo_id"],
        "text": k["tekstas"],
        "choices": k["options"],
        "durationMs": duration_ms,
        "deadlineMs": deadline_ms
    }

def ar_teisingas(k: dict, choice: str) -> bool:
    return choice.strip().upper() == k["teisingas_atsakymas"]
