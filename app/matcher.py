"""CV ir darbo skelbimo derinimo logika per Anthropic Claude API."""
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
            "summary": {
                "type": "string",
                "description": "Trumpa 1–2 sakinių išvada apie kandidato tinkamumą.",
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
            "summary",
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
    summary: str
    strengths: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def _build_prompt(cv_text: str, job_text: str) -> str:
    """Surenka naudotojo žinutę su CV ir skelbimo tekstais."""
    cv_text = cv_text[:MAX_CHARS]
    job_text = job_text[:MAX_CHARS]
    return (
        "Esi patyręs įdarbinimo specialistas. Palygink pateiktą CV su darbo "
        "skelbimu ir objektyviai įvertink atitikimą. Atsakyk ta pačia kalba, "
        "kuria parašytas CV.\n\n"
        f"=== CV ===\n{cv_text}\n\n"
        f"=== DARBO SKELBIMAS ===\n{job_text}\n\n"
        "Pateik rezultatą per įrankį „pateikti_rezultata“."
    )


def match_cv_to_job(cv_text: str, job_text: str) -> MatchResult:
    """Kreipiasi į Claude API ir grąžina struktūrizuotą atitikimo analizę.

    API raktas imamas iš aplinkos kintamojo ANTHROPIC_API_KEY.
    """
    if not cv_text.strip():
        raise ValueError("CV tekstas tuščias.")
    if not job_text.strip():
        raise ValueError("Darbo skelbimo tekstas tuščias.")

    client = Anthropic()  # Raktą pasiima iš ANTHROPIC_API_KEY automatiškai.

    message = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=2000,
        tools=[RESULT_TOOL],
        tool_choice={"type": "tool", "name": "pateikti_rezultata"},
        messages=[{"role": "user", "content": _build_prompt(cv_text, job_text)}],
    )

    # Randame įrankio iškvietimą su struktūrizuotu rezultatu.
    for block in message.content:
        if block.type == "tool_use" and block.name == "pateikti_rezultata":
            data = block.input
            score = int(data.get("match_score", 0))
            score = max(0, min(100, score))  # Apribojame 0–100.
            return MatchResult(
                match_score=score,
                summary=str(data.get("summary", "")),
                strengths=list(data.get("strengths", [])),
                missing_keywords=list(data.get("missing_keywords", [])),
                suggestions=list(data.get("suggestions", [])),
            )

    raise RuntimeError("Modelis negrąžino struktūrizuoto rezultato.")
