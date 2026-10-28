"""FastAPI aplikacija: CV + darbo skelbimo derinimo įrankis."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.matcher import match_cv_to_job
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
            result = match_cv_to_job(cv_content, job_text)
        except Exception as exc:  # Rodome draugišką klaidą naudotojui.
            error = f"Nepavyko atlikti analizės: {exc}"

    return templates.TemplateResponse(
        request,
        "index.html",
        {"result": result, "error": error, "job_text": job_text, "cv_text": cv_text},
    )
