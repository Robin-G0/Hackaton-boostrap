# Hackathon Repo Scaffold Generator (FastAPI + Postgres + Next.js)

This repository contains a single Python script that generates a ready-to-run starter repository for hackathons:

- **Backend**: FastAPI (Uvicorn, hot reload)
- **Database**: PostgreSQL 16
- **Frontend**: Next.js (App Router)
- **Orchestration**: Docker Compose
- Includes `.env.example` with default variables injected into backend/frontend.

The scaffold also pre-configures Next.js TypeScript settings to avoid Next modifying `tsconfig.json` on first startup, and disables Next telemetry by default.

---

## Requirements

- Python **3.10+**
- Docker + Docker Compose

---

## Files in this repo

- `scaffold.py` (the generator script)

---

## Usage

### 1) Create a new project in the current folder

```bash
python scaffold.py
```

This writes the scaffold into the current directory.

### 2) Create a new project in a target folder

```bash
python scaffold.py --root ./my-hackathon-project
```

### 3) Overwrite existing files

```bash
python scaffold.py --root ./my-hackathon-project --force
```

## After generation: start the stack

Go to the generated repo folder, then:

```bash
docker compose up --build
```

# Default URLs

Frontend: `http://localhost:3000`

Backend: `http://localhost:8000`

Backend endpoints:

`GET /api/health`

`GET /api/hello`

`GET /api/db/ping`

# Environment Variables

Generated at the repo root:

`.env.example` (template)

`.env` (same defaults, used by compose)

Key variables:

`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`

`BACKEND_PORT`, `FRONTEND_PORT`

`NEXT_PUBLIC_API_URL` (used by the browser)

`CORS_ORIGINS` (backend CORS)

`NEXT_TELEMETRY_DISABLED=1`

# Notes

- The scaffold is minimal but functional, designed to be a starting point for hackathon projects.
- You can customize the generated code and configuration as needed for your specific project requirements.
- The script is idempotent and can be re-run with `--force` to overwrite existing files if you want to regenerate the scaffold.