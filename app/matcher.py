"""CV ir darbo skelbimo derinimo logika per Anthropic Claude API.

Funkcijos:
- analyze():           atitikimas, alga, stipriosios pusės, spragos, pasiūlymai.
- rewrite_cv():        pritaikyto CV teksto generavimas.
- cover_letter():      motyvacinio laiško generavimas.
- company_insights():  įmonės žvalgyba su interneto paieška.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from anthropic import Anthropic

# Numatytasis modelis – pigesnis Sonnet. Galima keisti per .env (ANTHROPIC_MODEL),
# pvz. į „claude-opus-4-8“ kokybiškesnei analizei.
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

# Riba, kad per didelis tekstas neišpūstų užklausos (apytiksliai simbolių).
MAX_CHARS = 20000

# „Tool“ schema – priverčia modelį grąžinti struktūrizuotą JSON rezultatą.
RESULT_TOOL = {
    "name": "pateikti_rezultata",
    "description": "Pateikia CV ir darbo skelbimo atitikimo analizės rezultatą.",
    "input_schema": {
        "type": "object",
        "properties": {
            "match_score": {
                "type": "integer",
                "description": "Atitikimo įvertis nuo 0 iki 100.",
            },
            "verdict": {
                "type": "string",
                "description": "Trumpa 1–2 sakinių išvada: verta ar neverta kandidatuoti ir kodėl.",
            },
            "salary_range": {
                "type": "string",
                "description": "Orientacinis atlyginimo rėžis panašioje pozicijoje regione, pvz. „42–52 k€ / metus“.",
            },
            "salary_note": {
                "type": "string",
                "description": "Trumpas paaiškinimas, kuo remiasi algos vertinimas.",
            },
            "company_name": {
                "type": "string",
                "description": "Įmonės pavadinimas iš skelbimo (jei nurodytas, kitaip tuščia).",
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Kandidato stipriosios pusės, atitinkančios skelbimą.",
            },
            "missing_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Skelbime minimi, bet CV trūkstami raktiniai žodžiai/įgūdžiai.",
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Konkretūs CV pataisymo pasiūlymai šiam skelbimui.",
            },
        },
        "required": [
            "match_score",
            "verdict",
            "salary_range",
            "strengths",
            "missing_keywords",
            "suggestions",
        ],
    },
}


@dataclass
class MatchResult:
    """Derinimo rezultatas, paruoštas rodymui šablone."""

    match_score: int
    verdict: str
    salary_range: str = ""
    salary_note: str = ""
    company_name: str = ""
    strengths: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def _client() -> Anthropic:
    """Sukuria Anthropic klientą (raktą pasiima iš ANTHROPIC_API_KEY)."""
    return Anthropic()


def _clip(text: str) -> str:
    """Apriboja teksto ilgį, kad neišpūstų užklausos."""
    return text[:MAX_CHARS]


def _text_from(message) -> str:
    """Surenka visą tekstinį turinį iš atsakymo blokų."""
    parts = [b.text for b in message.content if getattr(b, "type", "") == "text"]
    return "\n".join(parts).strip()


def analyze(cv_text: str, job_text: str) -> MatchResult:
    """Kreipiasi į Claude API ir grąžina struktūrizuotą atitikimo analizę."""
    if not cv_text.strip():
        raise ValueError("CV tekstas tuščias.")
    if not job_text.strip():
        raise ValueError("Darbo skelbimo tekstas tuščias.")

    prompt = (
        "Esi patyręs įdarbinimo specialistas. Palygink pateiktą CV su darbo "
        "skelbimu ir objektyviai įvertink atitikimą. Algą vertink pagal poziciją "
        "ir regioną (jei nurodytas). Atsakyk ta pačia kalba, kuria parašytas CV.\n\n"
        f"=== CV ===\n{_clip(cv_text)}\n\n"
        f"=== DARBO SKELBIMAS ===\n{_clip(job_text)}\n\n"
        "Pateik rezultatą per įrankį „pateikti_rezultata“."
    )

    message = _client().messages.create(
        model=DEFAULT_MODEL,
        max_tokens=2000,
        tools=[RESULT_TOOL],
        tool_choice={"type": "tool", "name": "pateikti_rezultata"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "pateikti_rezultata":
            data = block.input
            score = max(0, min(100, int(data.get("match_score", 0))))
            return MatchResult(
                match_score=score,
                verdict=str(data.get("verdict", "")),
                salary_range=str(data.get("salary_range", "")),
                salary_note=str(data.get("salary_note", "")),
                company_name=str(data.get("company_name", "")),
                strengths=list(data.get("strengths", [])),
                missing_keywords=list(data.get("missing_keywords", [])),
                suggestions=list(data.get("suggestions", [])),
            )

    raise RuntimeError("Modelis negrąžino struktūrizuoto rezultato.")


def rewrite_cv(cv_text: str, job_text: str) -> str:
    """Perrašo CV, pritaikant jį konkrečiam darbo skelbimui. Grąžina Markdown tekstą."""
    prompt = (
        "Perrašyk pateiktą CV taip, kad jis geriau atitiktų šį darbo skelbimą: "
        "pabrėžk svarbiausius įgūdžius ir patirtį, naudok skelbimo raktinius žodžius, "
        "bet NIEKO neišgalvok ir nepridėk melagingos patirties. Išlaikyk tą pačią kalbą, "
        "kuria parašytas CV. Pateik tvarkingą CV Markdown formatu (be papildomų komentarų).\n\n"
        f"=== ESAMAS CV ===\n{_clip(cv_text)}\n\n"
        f"=== DARBO SKELBIMAS ===\n{_clip(job_text)}"
    )
    message = _client().messages.create(
        model=DEFAULT_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    return _text_from(message)


def cover_letter(cv_text: str, job_text: str, company_name: str = "") -> str:
    """Parašo motyvacinį laišką konkrečiai įmonei pagal CV ir skelbimą."""
    company = company_name.strip() or "įmonei iš skelbimo"
    prompt = (
        f"Parašyk profesionalų, nuoširdų motyvacinį laišką {company}, pritaikytą "
        "šiam darbo skelbimui ir remiantis pateiktu CV. Laiškas turi būti konkretus "
        "(ne bendrinis), pabrėžti atitinkančius įgūdžius ir motyvaciją, apie 250–350 "
        "žodžių. Rašyk ta pačia kalba, kuria parašytas skelbimas. Pateik tik laiško "
        "tekstą be papildomų komentarų.\n\n"
        f"=== CV ===\n{_clip(cv_text)}\n\n"
        f"=== DARBO SKELBIMAS ===\n{_clip(job_text)}"
    )
    message = _client().messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return _text_from(message)


def company_insights(company_name: str, job_text: str = "") -> str:
    """Įmonės žvalgyba su interneto paieška. Grąžina Markdown santrauką.

    Naudoja Anthropic „web_search“ įrankį – duomenys orientaciniai, gali būti nepilni.
    """
    company = company_name.strip()
    if not company:
        raise ValueError("Nenurodytas įmonės pavadinimas.")

    prompt = (
        f"Surask viešą informaciją apie įmonę „{company}“ ir pateik trumpą santrauką "
        "lietuvių kalba šiomis temomis:\n"
        "- Ką įmonė veikia (sritis, dydis, vieta)\n"
        "- Darbuotojų skaičius (apytiksliai)\n"
        "- Ar aktyviai samdo, augimo / plėtros ženklai\n"
        "- Atmosfera ir kultūra pagal viešus atsiliepimus (jei randama)\n"
        "- Į ką atkreipti dėmesį kandidatuojant (raudoni/žali signalai)\n\n"
        "Pateik tvarkingą Markdown santrauką. Aiškiai pažymėk, jei informacijos "
        "nepavyko rasti – neišgalvok duomenų."
    )
    if job_text.strip():
        prompt += f"\n\nKonteksto skelbimas:\n{_clip(job_text)[:3000]}"

    message = _client().messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
        messages=[{"role": "user", "content": prompt}],
    )
    return _text_from(message)
