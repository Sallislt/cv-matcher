"""CV teksto ištraukimas iš PDF arba paprasto teksto failo."""
from __future__ import annotations

import io

from pypdf import PdfReader


def extract_text_from_pdf(data: bytes) -> str:
    """Ištraukia tekstą iš PDF baitų. Grąžina sujungtą visų puslapių tekstą."""
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts).strip()


def extract_text(filename: str, data: bytes) -> str:
    """Pagal failo plėtinį parenka ištraukimo būdą (PDF arba tekstas)."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    # Tekstiniai failai (.txt, .md ir kt.) – bandome dekoduoti kaip UTF-8.
    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="ignore").strip()
