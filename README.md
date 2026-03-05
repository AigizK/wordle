# Wordle Bashkir

Wordle Bashkir is a daily Wordle-style game in the Bashkir language.

Players guess a 5-letter Bashkir word in up to 6 attempts. Tile colors follow classic Wordle logic:
- Green: correct letter in the correct position
- Yellow: correct letter in the wrong position
- Brown/gray: letter is not in the target word

## Tech Stack

- Python 3
- FastAPI
- Jinja2 templates
- SQLAlchemy (SQLite by default)

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8015
```

Open: `http://127.0.0.1:8015`

## Environment Variables

Copy and edit `.env.example` if needed:

- `APP_NAME`
- `DEBUG`
- `DATABASE_URL`
- `TASKS_PATH`
- `DICTIONARY_PATH`
- `START_DATE`
- `UTC_OFFSET_HOURS`

## Tests

```bash
pytest
```

