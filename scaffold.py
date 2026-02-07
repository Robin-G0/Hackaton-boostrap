#!/usr/bin/env python3
"""
Repo scaffold generator (FastAPI + Postgres + Next.js) for hackathon.

Fixes based on your logs:
- Prevent Next.js from mutating tsconfig.json at first boot:
  * adds .next/types/**/*.ts to include
  * adds { name: "next" } to compilerOptions.plugins
  * sets esModuleInterop=true
- Disables Next.js telemetry by default (NEXT_TELEMETRY_DISABLED=1)
- Adds sensible Next-specific compilerOptions used by Next (jsx, moduleResolution, etc.)

Usage:
  python scaffold.py
  python scaffold.py --root ./my-repo
  python scaffold.py --force
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict


def write_file(path: Path, content: str, *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return
    path.write_text(content, encoding="utf-8")


def render_env_example() -> str:
    return """# Copy to ".env" for docker compose usage.
# (This scaffold also creates a .env identical to this file for convenience.)

# --------------------
# Postgres
# --------------------
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_DB=app
POSTGRES_PORT=5432

# --------------------
# Backend / Frontend
# --------------------
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Frontend calls backend from your browser, so localhost is correct here.
NEXT_PUBLIC_API_URL=http://localhost:8000

# Comma-separated list for CORS (backend)
CORS_ORIGINS=http://localhost:3000

# Next.js
# Disable anonymous telemetry (avoids the prompt/noise in logs)
NEXT_TELEMETRY_DISABLED=1
"""


def render_docker_compose() -> str:
    return """services:
  db:
    image: postgres:16
    container_name: hack_db
    restart: unless-stopped
    env_file: .env
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 20

  backend:
    build:
      context: ./backend
    container_name: hack_backend
    restart: unless-stopped
    env_file: .env
    environment:
      # Use the docker network hostname "db" inside compose
      DATABASE_URL: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
      CORS_ORIGINS: "${CORS_ORIGINS}"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
    ports:
      - "${BACKEND_PORT}:8000"

  frontend:
    build:
      context: ./frontend
    container_name: hack_frontend
    restart: unless-stopped
    env_file: .env
    environment:
      # Used by the browser (public env var)
      NEXT_PUBLIC_API_URL: "${NEXT_PUBLIC_API_URL}"
      # Disable telemetry (prevents the startup notice)
      NEXT_TELEMETRY_DISABLED: "${NEXT_TELEMETRY_DISABLED}"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "${FRONTEND_PORT}:3000"

volumes:
  db_data:
"""


def render_gitignore() -> str:
    return """# Env
.env

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node / Next
node_modules/
.next/
out/
dist/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS / IDE
.DS_Store
.idea/
.vscode/
"""


def render_readme() -> str:
    return """# Hackathon Stack (FastAPI + Postgres + Next.js)

## Run (Docker)
1) Ensure you have Docker + Docker Compose.
2) Copy `.env.example` to `.env` (this scaffold also generates `.env` by default).
3) Start:
   - `docker compose up --build`

## URLs
- Frontend: http://localhost:${FRONTEND_PORT:-3000}
- Backend:   http://localhost:${BACKEND_PORT:-8000}

## Backend endpoints
- GET /api/health
- GET /api/hello
- GET /api/db/ping
"""


def render_backend_requirements() -> str:
    return """fastapi>=0.110
uvicorn[standard]>=0.27
psycopg[binary]>=3.1
python-dotenv>=1.0
"""


def render_backend_dockerfile() -> str:
    return """FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

EXPOSE 8000

# Dev-friendly (hot reload) for hackathon
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
"""


def render_backend_dockerignore() -> str:
    return """__pycache__
*.pyc
.venv
venv
.env
"""


def render_backend_main_py() -> str:
    return r'''from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import db_ping


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


load_dotenv()  # allows local runs outside docker (optional)

app = FastAPI(title="Hackathon API", version="0.1.0")

cors_origins = _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:3000"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"


@app.get(f"{API_PREFIX}/health")
def health():
    return {"status": "ok"}


@app.get(f"{API_PREFIX}/hello")
def hello():
    return {
        "message": "Hello from FastAPI",
        "apiPrefix": API_PREFIX,
        "nextPublicApiUrl": os.getenv("NEXT_PUBLIC_API_URL"),
    }


@app.get(f"{API_PREFIX}/db/ping")
def ping_db():
    ok, detail = db_ping()
    return {"ok": ok, "detail": detail}
'''


def render_backend_db_py() -> str:
    return r'''from __future__ import annotations

import os
from typing import Tuple

import psycopg


def db_ping() -> Tuple[bool, str]:
    """
    Simple connectivity check.
    DATABASE_URL is expected to look like:
      postgresql://user:password@host:port/dbname
    """
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return False, "DATABASE_URL is not set"

    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                _ = cur.fetchone()
        return True, "db ok"
    except Exception as e:
        return False, f"db error: {type(e).__name__}: {e}"
'''


def render_frontend_package_json() -> str:
    return """{
  "name": "hack-frontend",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev -H 0.0.0.0 -p 3000",
    "build": "next build",
    "start": "next start -H 0.0.0.0 -p 3000"
  },
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.30",
    "@types/react": "^18.2.67",
    "@types/react-dom": "^18.2.22",
    "typescript": "^5.4.5"
  }
}
"""


def render_frontend_dockerfile() -> str:
    return """FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY . /app

EXPOSE 3000

CMD ["npm", "run", "dev"]
"""


def render_frontend_dockerignore() -> str:
    return """.next
node_modules
.env
npm-debug.log
"""


def render_frontend_next_config() -> str:
    return """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true
};

module.exports = nextConfig;
"""


def render_frontend_tsconfig() -> str:
    # Pre-empt exactly what Next added in your logs:
    # - include: add '.next/types/**/*.ts'
    # - plugins: add { name: 'next' }
    # - mandatory: esModuleInterop=true
    return """{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "es2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "esModuleInterop": true,
    "plugins": [{ "name": "next" }]
  },
  "include": [
    "next-env.d.ts",
    ".next/types/**/*.ts",
    "**/*.ts",
    "**/*.tsx"
  ],
  "exclude": ["node_modules"]
}
"""


def render_frontend_next_env() -> str:
    return """/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited.
"""


def render_frontend_layout_tsx() -> str:
    return """export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: 24 }}>
        {children}
      </body>
    </html>
  );
}
"""


def render_frontend_page_tsx() -> str:
    return r"""'use client';

import { useEffect, useMemo, useState } from "react";

type HelloResponse = {
  message: string;
  apiPrefix?: string;
  nextPublicApiUrl?: string | null;
};

export default function Page() {
  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    []
  );

  const [data, setData] = useState<HelloResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const url = `${apiBase}/api/hello`;
    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as HelloResponse;
      })
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [apiBase]);

  return (
    <main style={{ maxWidth: 900 }}>
      <h1>Hackathon Starter</h1>
      <p>Frontend: Next.js | Backend: FastAPI | DB: Postgres</p>

      <section style={{ marginTop: 24, padding: 16, border: "1px solid #ddd", borderRadius: 12 }}>
        <h2>Backend check</h2>
        <p><strong>NEXT_PUBLIC_API_URL</strong>: {apiBase}</p>
        {error && <p style={{ color: "crimson" }}>Error: {error}</p>}
        {!error && !data && <p>Loading...</p>}
        {data && (
          <pre style={{ background: "#f7f7f7", padding: 12, borderRadius: 8, overflowX: "auto" }}>
{JSON.stringify(data, null, 2)}
          </pre>
        )}
      </section>
    </main>
  );
}
"""


def build_plan(root: Path) -> Dict[Path, str]:
    files: Dict[Path, str] = {}

    # Root
    files[root / "docker-compose.yml"] = render_docker_compose()
    files[root / ".env.example"] = render_env_example()
    files[root / ".env"] = render_env_example()
    files[root / ".gitignore"] = render_gitignore()
    files[root / "README.md"] = render_readme()

    # Backend
    files[root / "backend" / "Dockerfile"] = render_backend_dockerfile()
    files[root / "backend" / ".dockerignore"] = render_backend_dockerignore()
    files[root / "backend" / "requirements.txt"] = render_backend_requirements()
    files[root / "backend" / "app" / "__init__.py"] = ""
    files[root / "backend" / "app" / "main.py"] = render_backend_main_py()
    files[root / "backend" / "app" / "db.py"] = render_backend_db_py()

    # Frontend
    files[root / "frontend" / "Dockerfile"] = render_frontend_dockerfile()
    files[root / "frontend" / ".dockerignore"] = render_frontend_dockerignore()
    files[root / "frontend" / "package.json"] = render_frontend_package_json()
    files[root / "frontend" / "next.config.js"] = render_frontend_next_config()
    files[root / "frontend" / "tsconfig.json"] = render_frontend_tsconfig()
    files[root / "frontend" / "next-env.d.ts"] = render_frontend_next_env()
    files[root / "frontend" / "app" / "layout.tsx"] = render_frontend_layout_tsx()
    files[root / "frontend" / "app" / "page.tsx"] = render_frontend_page_tsx()

    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Target repo root (default: current directory)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    plan = build_plan(root)

    written = 0
    skipped = 0
    for path, content in plan.items():
        existed = path.exists()
        write_file(path, content, force=args.force)
        if existed and not args.force:
            skipped += 1
        else:
            written += 1

    print(f"Scaffold complete in: {root}")
    print(f"Files written: {written} | skipped (already existed): {skipped}")
    print("\nNext:")
    print("  docker compose up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
