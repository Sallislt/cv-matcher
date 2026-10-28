"""FastAPI aplikacija: CV + darbo skelbimo derinimo įrankis.

Maršrutai:
- GET  /            – pradinis puslapis su forma (daugiakalbis).
- POST /analyze     – CV + skelbimo analizė, grąžina HTML su rezultatu.
- POST /rewrite-cv  – pritaikyto CV generavimas (JSON).
- POST /cover-letter– motyvacinio laiško generavimas (JSON).
- POST /company     – įmonės žvalgyba su interneto paieška (JSON).
- POST /ats         – ATS peržiūra: kaip CV mato atrankos sistema (JSON).

Sąsaja verčiama per app.i18n; AI atsakymai generuojami CV/skelbimo kalba.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import i18n, matcher
from app.pdf_utils import extract_text

# Užkrauname .env (ANTHROPIC_API_KEY ir kt.).
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="CV Matcher")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Slapuko pavadinimas pasirinktai kalbai įsiminti.
LANG_COOKIE = "lang"


def pick_lang(request: Request, query_lang: str | None = None) -> str:
    """Parenka sąsajos kalbą: ?lang= → slapukas → naršyklės Accept-Language."""
    candidate = query_lang or request.cookies.get(LANG_COOKIE)
    return i18n.resolve_lang(candidate, request.headers.get("accept-language"))


def base_context(request: Request, lang: str) -> dict:
    """Bendras šablono kontekstas su vertimais ir kalbų sąrašu."""
    return {
        "t": i18n.get(lang),
        "lang": lang,
        "dir": "rtl" if lang in i18n.RTL else "ltr",
        "languages": i18n.LANGUAGES,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, lang: str | None = None):
    """Pradinis puslapis su forma."""
    chosen = pick_lang(request, lang)
    response = templates.TemplateResponse(request, "index.html", base_context(request, chosen))
    # Jei kalba nurodyta per ?lang=, įsimename ją slapuke.
    if lang and lang in i18n.TRANSLATIONS:
        response.set_cookie(LANG_COOKIE, chosen, max_age=60 * 60 * 24 * 365)
    return response


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    cv_file: UploadFile | None = None,
    cv_text: str = Form(""),
    job_text: str = Form(""),
):
    """Priima CV (failą arba tekstą) ir skelbimą, grąžina analizės rezultatą."""
    lang = pick_lang(request)
    t = i18n.get(lang)
    error: str | None = None
    result = None

    # CV tekstas: pirmenybė įkeltam failui, kitaip – įvestam tekstui.
    cv_content = cv_text.strip()
    if cv_file is not None and cv_file.filename:
        data = await cv_file.read()
        if data:
            cv_content = extract_text(cv_file.filename, data)

    if not cv_content:
        error = t["err_no_cv"]
    elif not job_text.strip():
        error = t["err_no_job"]
    else:
        try:
            result = matcher.analyze(cv_content, job_text)
        except Exception as exc:  # Rodome draugišką klaidą naudotojui.
            error = f"{t['err_analyze']} {exc}"

    context = base_context(request, lang)
    context.update(
        {
            "result": result,
            "error": error,
            "job_text": job_text,
            "cv_text": cv_text,
            "cv_content": cv_content,
        }
    )
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/rewrite-cv")
async def rewrite_cv(cv_text: str = Form(""), job_text: str = Form("")):
    """Grąžina pritaikytą CV (JSON)."""
    try:
        text = matcher.rewrite_cv(cv_text, job_text)
        return JSONResponse({"ok": True, "text": text})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=200)


@app.post("/cover-letter")
async def cover_letter(
    cv_text: str = Form(""), job_text: str = Form(""), company_name: str = Form("")
):
    """Grąžina motyvacinį laišką (JSON)."""
    try:
        text = matcher.cover_letter(cv_text, job_text, company_name)
        return JSONResponse({"ok": True, "text": text})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=200)


@app.post("/company")
async def company(company_name: str = Form(""), job_text: str = Form("")):
    """Grąžina įmonės žvalgybos santrauką su interneto paieška (JSON)."""
    try:
        text = matcher.company_insights(company_name, job_text)
        return JSONResponse({"ok": True, "text": text})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=200)


@app.post("/ats")
async def ats(cv_text: str = Form(""), job_text: str = Form("")):
    """Grąžina ATS peržiūrą: kaip CV perskaitytų atrankos sistema (JSON)."""
    try:
        data = matcher.ats_view(cv_text, job_text)
        return JSONResponse({"ok": True, "data": data})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=200)
