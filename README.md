# CV Matcher — AI CV ir darbo skelbimo derinimo įrankis

Įrankis, kuris su **Anthropic Claude** AI palygina jūsų CV su darbo skelbimu ir
pateikia: atitikimo įvertį (%), stipriąsias puses, trūkstamus raktinius
žodžius/įgūdžius ir konkrečius CV pataisymo pasiūlymus.

Sukurta su Python + FastAPI. Paprasta web sąsaja: įkeliate CV (PDF arba tekstą),
įklijuojate skelbimą — ir gaunate analizę.

## Ekrano nuotrauka

![CV Matcher sąsaja](docs/screenshot.png)

## Funkcijos

- CV įkėlimas **PDF** arba teksto formatu (arba tiesiog įklijuotas tekstas).
- Darbo skelbimo tekstas.
- AI analizė grąžina:
  - **Atitikimo įvertį** (0–100 %)
  - **Stipriąsias puses**
  - **Trūkstamus raktinius žodžius / įgūdžius**
  - **Konkrečius CV pataisymo pasiūlymus**
- Atsakymas pateikiamas ta pačia kalba, kuria parašytas CV.

## Technologijos

- Python 3.11+ / FastAPI
- Anthropic Claude API (`anthropic` SDK, struktūrizuotas atsakymas per tool use)
- Jinja2 šablonai, grynas HTML/CSS (be Node.js build'o)
- `pypdf` PDF teksto ištraukimui

## Paleidimas

1. Klonuokite projektą ir sukurkite virtualią aplinką:

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. Įdiekite priklausomybes:

   ```bash
   pip install -r requirements.txt
   ```

3. Nustatykite API raktą:

   ```bash
   cp .env.example .env
   ```

   Faile `.env` įrašykite savo `ANTHROPIC_API_KEY` (gaunamas iš
   [console.anthropic.com](https://console.anthropic.com/)).

4. Paleiskite serverį:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Atidarykite naršyklėje: <http://127.0.0.1:8000>

## Projekto struktūra

```
cv-matcher/
├── app/
│   ├── main.py        # FastAPI maršrutai (forma + analizė)
│   ├── matcher.py     # Claude API iškvietimas, struktūrizuotas rezultatas
│   └── pdf_utils.py   # Teksto ištraukimas iš PDF / teksto failų
├── templates/
│   └── index.html     # Forma ir rezultatų puslapis
├── static/
│   └── style.css
├── requirements.txt
├── .env.example
└── README.md
```

## Modelio pasirinkimas

Numatytasis modelis — `claude-sonnet-5-5` (pigesnis, greitas). Kokybiškesnei
analizei faile `.env` galima nurodyti `ANTHROPIC_MODEL=claude-opus-4-8`.

## Licencija

[MIT](LICENSE)
