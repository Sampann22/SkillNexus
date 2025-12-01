# SkillNexus: Bridging Freelancing Talent with Organizations

Quick instructions to run the Django backend locally for development.

Prerequisites
- Python 3.10+
- Node is not required for the backend, but the frontend uses Node/Vite.

Setup (bash / Git Bash on Windows)

1. Create and activate a virtual environment

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # bash on Windows (Git Bash) or use the equivalent for your shell
python -m pip install --upgrade pip
```

2. Install Python dependencies

```bash
pip install -r requirements.txt
```

3. Create a local `.env` (optional)

```bash
cp .env.example .env
# edit .env and set DJANGO_SECRET_KEY and DJANGO_DEBUG if needed
```

4. Run database migrations and start the development server

```bash
python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

Default behaviour
- If `DATABASE_URL` is not set, Django will use the included `db.sqlite3` database for local development.
- `settings.py` reads `DJANGO_SECRET_KEY` and `DJANGO_DEBUG` from environment variables. If not set, a local unsafe fallback is used for convenience only.

Notes for deployment
- For production, set `DJANGO_DEBUG=False` and provide a secure `DJANGO_SECRET_KEY` and a `DATABASE_URL` pointing to a managed Postgres database.
- Consider adding `whitenoise` and `gunicorn` configuration for static files and process management (packages are included in `requirements.txt`).
