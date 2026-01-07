import random

KLAUSIMAI = [
    {
        "klausimo_id": 1,
        "tekstas": "Kuris vandenynas yra didžiausias pasaulyje?",
        "options": ["Atlanto vandenynas", "Indijos vandenynas", "Ramusis vandenynas", "Arkties vandenynas"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 2,
        "tekstas": "Kuri šalis turi didžiausią gyventojų skaičių pasaulyje?",
        "options": ["JAV", "Rusija", "Indija", "Brazilija"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 3,
        "tekstas": "Kuri planeta turi daugiausia žiedų?",
        "options": ["Jupiteris", "Uranas", "Saturnas", "Neptūnas"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 4,
        "tekstas": "Kokia yra pagrindinė fotosintezės funkcija?",
        "options": ["Išskirti deguonį", "Sugerti vandenį", "Gaminti maistą augalui naudojant šviesą", "Reguliuoti temperatūrą"],
        "teisingas_atsakymas": "C"
    },
    {
        "klausimo_id": 5,
        "tekstas": "Kuri žmogaus kūno sistema perneša deguonį?",
        "options": ["Nervų sistema", "Virškinimo sistema", "Kraujotakos sistema", "Endokrininė sistema"],
        "teisingas_atsakymas": "C"
    }
]

def gauti_atsitiktini_klausima() -> dict:
    return random.choice(KLAUSIMAI)

def klausimas_i_payload(k: dict, duration_ms: int, deadline_ms: int) -> dict:
    # į Unity nesiunčiam teisingo atsakymo
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
