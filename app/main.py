"""FastAPI aplikacija: CV + darbo skelbimo derinimo įrankis."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import matcher
from app.pdf_utils import extract_text

# Užkrauname .env (ANTHROPIC_API_KEY ir kt.).
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="CV Matcher")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Pradinis puslapis su forma."""
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    cv_file: UploadFile | None = None,
    cv_text: str = Form(""),
    job_text: str = Form(""),
):
    """Priima CV (failą arba tekstą) ir skelbimą, grąžina analizės rezultatą."""
    error: str | None = None
    result = None

    # CV tekstas: pirmenybė įkeltam failui, kitaip – įvestam tekstui.
    cv_content = cv_text.strip()
    if cv_file is not None and cv_file.filename:
        data = await cv_file.read()
        if data:
            cv_content = extract_text(cv_file.filename, data)

    if not cv_content:
        error = "Įkelkite CV failą arba įveskite CV tekstą."
    elif not job_text.strip():
        error = "Įveskite darbo skelbimo tekstą."
    else:
        try:
            result = matcher.analyze(cv_content, job_text)
        except Exception as exc:  # Rodome draugišką klaidą naudotojui.
            error = f"Nepavyko atlikti analizės: {exc}"

    # Perduodame CV ir skelbimo tekstą atgal, kad veiktų generavimo mygtukai.
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "result": result,
            "error": error,
            "job_text": job_text,
            "cv_text": cv_text,
            "cv_content": cv_content,
        },
    )


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
