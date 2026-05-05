# Dynamic Form Builder — Backend

A schema-driven form engine built with **Django** and **Django REST Framework**. Forms are defined as structured JSON, stored in PostgreSQL, and executed by a pipeline of five backend engines. The frontend is a separate repository — this API serves as the single source of truth for all form logic.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started — Local](#getting-started--local)
- [Getting Started — Docker](#getting-started--docker)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [Engine Pipeline](#engine-pipeline)
- [Project Structure](#project-structure)
- [Management Commands](#management-commands)
- [Running Tests](#running-tests)

---

## Features

- **Schema-driven forms** — entire form definition stored as JSONB; no code changes needed to update a form
- **Multi-step forms** — backend controls navigation between steps
- **Conditional fields** — fields show/hide based on other field values
- **Validation engine** — required, min, max, regex rules evaluated server-side
- **Rule engine** — post-submit automation: set values, assign statuses, add tags
- **Form versioning** — every schema update bumps the version; old submissions stay valid
- **Draft support** — save partial responses per user per form
- **Public share** — unauthenticated endpoints for sharing forms via link
- **Seeded test data** — one command populates users, forms, submissions, and a draft

---

## Tech Stack

| | |
|---|---|
| Framework | Django 4.2 |
| API | Django REST Framework 3.15 |
| Database | PostgreSQL 15 / SQLite (local) |
| DB Driver | psycopg2-binary 2.9 |
| CORS | django-cors-headers 4.3 |
| Runtime | Python 3.11 |
| Containers | Docker + Compose 3.9 |

---

## Prerequisites

**Local development**
- Python 3.11+
- pip

**Docker**
- Docker Desktop (or Docker Engine + Compose plugin)

---

## Getting Started — Local

### 1. Clone and enter the repo

```bash
git clone <repo-url>
cd Dynamic-Form-Backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env            # if .env.example exists, otherwise create it
```

Minimum `.env` for local SQLite development:

```ini
SECRET_KEY=any-local-dev-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Seed test data (optional)

```bash
python manage.py seed_db
```

### 7. Start the development server

```bash
python manage.py runserver 8001
```

API is now available at `http://127.0.0.1:8001/api/`

---

## Getting Started — Docker

### 1. Configure Docker environment

The Docker setup reads from `.env.docker`. Create it from the example below (already included in the repo — update credentials as needed):

```ini
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,0.0.0.0,web

DB_ENGINE=django.db.backends.postgresql
DB_NAME=dynamic_form_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_HOST_PORT=5433
```

> `DB_PORT` is the port Django uses inside the Docker network (always 5432).
> `DB_HOST_PORT` is the port exposed to your machine (5433, to avoid conflicts with a local PostgreSQL instance).

### 2. Build and start

```bash
docker-compose up --build
```

Migrations run automatically on container start. The API will be available at `http://localhost:8001/api/`

### 3. Seed test data

```bash
docker-compose exec web python manage.py seed_db
```

### 4. Useful Docker commands

```bash
# Run in background
docker-compose up --build -d

# Stream logs
docker-compose logs -f web
docker-compose logs -f db

# Open Django shell
docker-compose exec web python manage.py shell

# Stop (keeps database volume)
docker-compose down

# Stop and wipe all data
docker-compose down -v
```

### Seeded Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Superuser |
| `testuser` | `testpass123` | Regular user |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Django secret key (required) |
| `DEBUG` | `False` | Enable debug mode |
| `ALLOWED_HOSTS` | _(empty)_ | Comma-separated list of allowed hosts |
| `DB_ENGINE` | `django.db.backends.sqlite3` | Database backend |
| `DB_NAME` | `db.sqlite3` | Database name or SQLite file path |
| `DB_USER` | _(empty)_ | Database user (PostgreSQL) |
| `DB_PASSWORD` | _(empty)_ | Database password (PostgreSQL) |
| `DB_HOST` | _(empty)_ | Database host (PostgreSQL) |
| `DB_PORT` | _(empty)_ | Database port (PostgreSQL, internal) |
| `DB_HOST_PORT` | `5433` | Host port mapped to container (Docker only) |

---

## API Overview

All endpoints are prefixed with `/api/`.

### Health

```
GET  /api/health/                          → { "status": "ok" }
```

### User

```
POST   /api/user/register/                 → create account
GET    /api/user/me/                       → current user + profile
PATCH  /api/user/me/                       → update name / email
DELETE /api/user/me/                       → delete account
GET    /api/user/me/profile/               → get profile
PATCH  /api/user/me/profile/               → update bio
```

### Builder — Authenticated

```
GET    /api/builder/forms/                 → list own forms
POST   /api/builder/forms/                 → create form
GET    /api/builder/forms/{id}/            → get form + schema
PATCH  /api/builder/forms/{id}/            → update form (bumps version)
DELETE /api/builder/forms/{id}/            → delete form

POST   /api/builder/forms/{id}/submit/     → run engine pipeline
GET    /api/builder/forms/{id}/submissions/ → list submissions

GET    /api/builder/forms/{id}/draft/      → get draft
POST   /api/builder/forms/{id}/draft/      → save / update draft
DELETE /api/builder/forms/{id}/draft/      → delete draft
```

### Builder — Public (no auth)

```
GET    /api/builder/forms/{id}/share/          → get form for public render
POST   /api/builder/forms/{id}/share/submit/   → submit form publicly
```

### Authentication

All protected endpoints use **HTTP Basic Authentication**:

```
Authorization: Basic base64(username:password)
```

---

## Engine Pipeline

On every `POST /submit/` the following engines run in order:

```
1. validation_engine   → enforces required, min, max, regex
                          (only on fields visible per condition_engine)
       ↓ (if valid)
2. rule_engine         → applies post-submit rules (set_value, set_status, tag)

3. navigation_engine   → determines the next step (or None if form is complete)
       ↓
  next step?  → 200 { next_step, data }
  complete?   → Submission saved → 201
```

`schema_parser` runs at **create/update time** — it validates the form DSL before it is stored.

### Form Schema Structure

```json
{
  "steps": [
    {
      "id": "step_1",
      "title": "Step Title",
      "fields": [
        {
          "id": "salary",
          "type": "number",
          "label": "Monthly Salary",
          "required": true,
          "validations": [{ "type": "min", "value": 10000 }],
          "visibility": {
            "condition": { "field": "employed", "operator": "==", "value": "yes" }
          }
        }
      ]
    }
  ],
  "navigation": [
    { "from_step": "step_1", "to_step": "step_2" }
  ],
  "rules": [
    {
      "if":   { "field": "salary", "operator": ">", "value": 100000 },
      "then": { "action": "set_status", "value": "approved" }
    }
  ],
  "settings": {}
}
```

**Field types:** `text` · `textarea` · `number` · `email` · `date` · `select` · `radio` · `checkbox`

**Validation types:** `min` · `max` · `regex`

**Rule actions:** `set_value` · `set_status` · `tag`

**Condition operators:** `==` · `!=` · `>` · `<` · `>=` · `<=`

---

## Project Structure

```
Dynamic-Form-Backend/
├── config/               Django project (settings, root URLs)
├── api/                  Health check app
├── user/                 Registration, profile, account management
├── builder/              Core form engine
│   ├── models.py         Form, Submission, DraftSubmission
│   ├── views.py          CRUD, submit, share, draft endpoints
│   ├── serializers.py
│   ├── urls.py
│   ├── engines/
│   │   ├── schema_parser.py
│   │   ├── condition_engine.py
│   │   ├── validation_engine.py
│   │   ├── navigation_engine.py
│   │   └── rule_engine.py
│   └── management/commands/
│       └── seed_db.py
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── env_loader.py         Reads .env using the os module
├── manage.py
├── requirements.txt
├── .env                  Local dev config (gitignored)
├── .env.docker           Docker config (gitignored)
└── SYSTEM_DESIGN.md      Full backend system design
```

---

## Management Commands

### `seed_db`

Populates the database with test data.

```bash
python manage.py seed_db             # local
docker-compose exec web python manage.py seed_db   # Docker
```

Creates:

| Resource | Details |
|---|---|
| `admin` | Superuser, password: `admin123` |
| `testuser` | Regular user, password: `testpass123` |
| Loan Application | Multi-step form with conditions, navigation, and rules |
| Contact Form | Single-step form with validation and a tagging rule |
| 5 Submissions | 3 for Loan Application, 2 for Contact Form |
| 1 Draft | Contact Form, 3 of 4 fields filled |

The command is idempotent — running it multiple times will not create duplicates.

### Standard Django commands

```bash
python manage.py migrate               # apply migrations
python manage.py makemigrations        # create new migrations
python manage.py createsuperuser       # create an admin account
python manage.py shell                 # open interactive Django shell
python manage.py runserver 8001        # start dev server on port 8001
```

---

## Running Tests

```bash
python manage.py test
```

---

> For full architecture details, engine design, schema DSL reference, and data flow diagrams see [SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md).
