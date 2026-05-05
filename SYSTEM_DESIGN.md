# System Design — Dynamic Form Builder · Backend

> This document covers the **backend API** only.
> The frontend repository is maintained separately.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Repository Structure](#4-repository-structure)
5. [Django Apps](#5-django-apps)
6. [Database Design](#6-database-design)
7. [Engine Pipeline](#7-engine-pipeline)
8. [Schema DSL](#8-schema-dsl)
9. [API Endpoints](#9-api-endpoints)
10. [Data Flow](#10-data-flow)
11. [Authentication](#11-authentication)
12. [Environment & Configuration](#12-environment--configuration)
13. [Docker & Infrastructure](#13-docker--infrastructure)
14. [Security Considerations](#14-security-considerations)

---

## 1. Overview

This is the backend for a **schema-driven form engine**. Forms are defined as structured JSON (a DSL), stored in PostgreSQL, and executed by a pipeline of five independent engines. The frontend (any client) receives the schema and renders it — all business logic lives here.

### Core Responsibilities

- Store and version form schemas (JSONB)
- Validate submitted data against schema rules
- Evaluate conditional field visibility
- Drive multi-step navigation
- Execute post-submission rules (set values, assign statuses, add tags)
- Store submissions and draft responses
- Expose public share endpoints (no auth required)

### Design Principles

- **No eval / no dynamic code** — all logic is data-driven and whitelisted
- **Backend-authoritative** — the client is a dumb renderer; all decisions happen here
- **Schema versioning** — every update bumps the form version; old submissions stay valid
- **Environment-driven config** — SQLite for local dev, PostgreSQL for Docker; same codebase

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Any HTTP Client (Browser / Postman)             │
│                                                              │
│   GET  /api/builder/forms/{id}/        ← fetch schema        │
│   POST /api/builder/forms/{id}/submit/ ← submit data         │
│   GET  /api/builder/forms/{id}/share/  ← public (no auth)    │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP / REST  (Basic Auth)
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                   Django + DRF  (port 8001)                  │
│                                                              │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐  │
│   │  api/    │  │  user/   │  │        builder/           │  │
│   │  health  │  │  auth    │  │                           │  │
│   └──────────┘  └──────────┘  │  ┌────────────────────┐  │  │
│                               │  │  Engine Pipeline    │  │  │
│                               │  │                     │  │  │
│                               │  │  schema_parser      │  │  │
│                               │  │  condition_engine   │  │  │
│                               │  │  validation_engine  │  │  │
│                               │  │  navigation_engine  │  │  │
│                               │  │  rule_engine        │  │  │
│                               │  └────────────────────┘  │  │
│                               └──────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│               PostgreSQL  (host: 5433 → container: 5432)     │
│                                                              │
│   auth_user          user_userprofile                        │
│   builder_form       builder_submission                      │
│   builder_draftsubmission                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

| Component | Technology | Version |
|---|---|---|
| Web framework | Django | 4.2 |
| REST API layer | Django REST Framework | 3.15 |
| Database | PostgreSQL | 15 |
| DB driver | psycopg2-binary | 2.9 |
| CORS headers | django-cors-headers | 4.3 |
| Runtime | Python | 3.11 |
| Container | Docker + Compose | 3.9 |

---

## 4. Repository Structure

```
Dynamic-Form-Backend/
│
├── Dockerfile               ← python:3.11-slim, installs psycopg2 system deps
├── docker-compose.yml       ← db (postgres:15) + web (django) services
├── entrypoint.sh            ← migrate → runserver 0.0.0.0:8001
├── .env                     ← local dev (SQLite, gitignored)
├── .env.docker              ← Docker (PostgreSQL, gitignored)
├── .dockerignore
├── .gitignore
├── requirements.txt
├── manage.py
├── env_loader.py            ← reads .env using os module, sets os.environ
├── SYSTEM_DESIGN.md
│
├── config/                  ← Django project package
│   ├── settings.py          ← all config via os.environ.get()
│   ├── urls.py              ← root URL conf
│   ├── wsgi.py
│   └── asgi.py
│
├── api/                     ← health check app
│   ├── views.py             ← HealthCheckView → GET /api/health/
│   ├── urls.py
│   ├── models.py
│   ├── serializers.py
│   ├── apps.py
│   ├── admin.py
│   └── migrations/
│
├── user/                    ← user management app
│   ├── models.py            ← UserProfile (1:1 with auth_user)
│   ├── serializers.py       ← UserSerializer, UserProfileSerializer
│   ├── views.py             ← RegisterView, UserDetailView, UserProfileView
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
│
└── builder/                 ← core form engine app
    ├── models.py            ← Form, Submission, DraftSubmission
    ├── serializers.py
    ├── views.py             ← CRUD + submit + share + draft
    ├── urls.py
    ├── admin.py
    ├── apps.py
    ├── migrations/
    ├── engines/
    │   ├── __init__.py
    │   ├── schema_parser.py
    │   ├── condition_engine.py
    │   ├── validation_engine.py
    │   ├── navigation_engine.py
    │   └── rule_engine.py
    └── management/
        └── commands/
            └── seed_db.py   ← python manage.py seed_db
```

---

## 5. Django Apps

| App | URL Prefix | Responsibility |
|---|---|---|
| `api` | `/api/` | Health check only |
| `user` | `/api/user/` | Registration, profile, account management |
| `builder` | `/api/builder/` | Form CRUD, engine pipeline, submissions, drafts, public share |

### Root URL Configuration (`config/urls.py`)

```
/admin/                  → Django admin
/api/                    → api.urls      (health check)
/api/user/               → user.urls
/api/builder/            → builder.urls
```

---

## 6. Database Design

### Entity Relationship Diagram

```
auth_user  (Django built-in)
    │
    ├──< UserProfile          (OneToOne)
    │       ├── bio            TextField
    │       ├── created_at     DateTimeField
    │       └── updated_at     DateTimeField
    │
    ├──< Form                 (ForeignKey owner)
    │       ├── name           CharField
    │       ├── version        PositiveIntegerField  ← bumped on schema change
    │       ├── schema         JSONField             ← full DSL
    │       ├── is_published   BooleanField
    │       ├── created_at     DateTimeField
    │       └── updated_at     DateTimeField
    │               │
    │               ├──< Submission            (ForeignKey form)
    │               │       ├── version        PositiveIntegerField
    │               │       ├── data           JSONField
    │               │       └── created_at     DateTimeField
    │               │
    │               └──< DraftSubmission       (ForeignKey form)
    │                       ├── user           FK → auth_user (nullable)
    │                       ├── partial_data   JSONField
    │                       ├── updated_at     DateTimeField
    │                       └── unique_together: (user, form)
    │
    └──< DraftSubmission      (ForeignKey user, nullable)
```

### Model Field Details

**Form**

| Field | Type | Notes |
|---|---|---|
| `owner` | FK → auth_user | CASCADE delete |
| `name` | CharField(255) | Human-readable title |
| `version` | PositiveIntegerField | Default 1, increments on schema PATCH |
| `schema` | JSONField | Full DSL — steps, navigation, rules, settings |
| `is_published` | BooleanField | Default False |

**Submission**

| Field | Type | Notes |
|---|---|---|
| `form` | FK → Form | CASCADE delete |
| `version` | PositiveIntegerField | Snapshot of `form.version` at submit time |
| `data` | JSONField | Submitted values + rule mutations (`_status`, `_tags`) |

**DraftSubmission**

| Field | Type | Notes |
|---|---|---|
| `user` | FK → auth_user | Nullable, SET_NULL on delete |
| `form` | FK → Form | CASCADE delete |
| `partial_data` | JSONField | Incomplete submission data |
| `unique_together` | (user, form) | One draft per user per form |

---

## 7. Engine Pipeline

All five engines live in `builder/engines/`. Each has a single responsibility and no side effects — they take data in and return results out.

### Execution Order on Submit

```
POST /api/builder/forms/{id}/submit/
  { current_step: "step_id", data: { field_id: value } }
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  1. validation_engine.validate_submission(schema, data) │
│                                                         │
│     internally calls:                                   │
│     condition_engine.get_visible_fields(step, data)     │
│     → skip hidden fields entirely                       │
│     → enforce required, min, max, regex on visible only │
│                                                         │
│     returns: (is_valid, { field_id: ["error msg"] })    │
└───────────────┬─────────────────────────────────────────┘
                │ 400 if not valid
                ▼ (valid)
┌─────────────────────────────────────────────────────────┐
│  2. rule_engine.execute_rules(schema, data)             │
│                                                         │
│     for each rule in schema.rules:                      │
│       condition_engine.evaluate_condition(rule.if, data)│
│       → if True: apply rule.then action                 │
│                                                         │
│     returns: mutated data dict                          │
└───────────────┬─────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────┐
│  3. navigation_engine.get_next_step(schema, step, data) │
│                                                         │
│     checks schema.navigation[] rules first              │
│     → condition_engine.evaluate_condition(nav.condition)│
│     falls back to linear step order                     │
│                                                         │
│     returns: next_step_id  or  None                     │
└───────────────┬─────────────────────────────────────────┘
                │
       ┌────────┴─────────┐
  next_step exists      no next_step
       │                   │
  200 { next_step,    Submission.objects.create()
        data }         201 { id, form, version, data }
```

> `schema_parser` runs at **CREATE / UPDATE** time, not at submit time.
> It validates the DSL structure before it is ever stored.

### Engine Reference

| Engine | Module | Input | Output |
|---|---|---|---|
| `schema_parser` | `schema_parser.py` | Raw schema `dict` | `(bool, [str])` |
| `condition_engine` | `condition_engine.py` | `condition` obj + `data` dict | `bool` |
| `validation_engine` | `validation_engine.py` | `schema` + `data` | `(bool, {field: [str]})` |
| `navigation_engine` | `navigation_engine.py` | `schema` + `step_id` + `data` | `str` or `None` |
| `rule_engine` | `rule_engine.py` | `schema` + `data` | mutated `data` dict |

### Condition Operators

| Operator | Type | Description |
|---|---|---|
| `==` | string | String equality |
| `!=` | string | String inequality |
| `>` | numeric | Greater than |
| `<` | numeric | Less than |
| `>=` | numeric | Greater than or equal |
| `<=` | numeric | Less than or equal |

### Rule Actions

| Action | `then` fields | Effect on data |
|---|---|---|
| `set_value` | `field`, `value` | `data[field] = value` |
| `set_status` | `value` | `data["_status"] = value` |
| `tag` | `value` | `data["_tags"].append(value)` |

### Schema Parser Validation Rules

The parser enforces these structural rules before any schema is stored:

- `steps` must be a non-empty list
- Each step must have `id` and `title`
- Each field must have a unique `id`, a valid `type`, and a `label`
- Field types must be one of: `text`, `textarea`, `number`, `email`, `date`, `select`, `radio`, `checkbox`
- Validation rules must have `type` (min/max/regex) and `value`
- Visibility conditions must have `field`, `operator`, `value`
- Operators must be one of: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Navigation rules must have `from_step` and `to_step`
- Rule actions must be one of: `set_value`, `set_status`, `tag`

---

## 8. Schema DSL

The entire form definition is stored as a single JSON document in `Form.schema`.

### Top-Level Structure

```json
{
  "steps":      [],
  "navigation": [],
  "rules":      [],
  "settings":   {}
}
```

### Full Example

```json
{
  "steps": [
    {
      "id": "step_personal",
      "title": "Personal Information",
      "fields": [
        {
          "id": "employment_status",
          "type": "select",
          "label": "Employment Status",
          "required": true,
          "options": ["employed", "self-employed", "unemployed"]
        },
        {
          "id": "salary",
          "type": "number",
          "label": "Monthly Salary",
          "required": true,
          "validations": [
            { "type": "min", "value": 10000 },
            { "type": "max", "value": 500000 }
          ],
          "visibility": {
            "condition": {
              "field": "employment_status",
              "operator": "==",
              "value": "employed"
            }
          }
        }
      ]
    },
    {
      "id": "step_financial",
      "title": "Financial Information",
      "fields": [
        {
          "id": "loan_amount",
          "type": "number",
          "label": "Loan Amount",
          "required": true,
          "validations": [
            { "type": "min", "value": 1000 }
          ]
        }
      ]
    }
  ],
  "navigation": [
    {
      "from_step": "step_personal",
      "to_step":   "step_financial",
      "condition": {
        "field": "employment_status",
        "operator": "!=",
        "value": "unemployed"
      }
    }
  ],
  "rules": [
    {
      "if":   { "field": "salary", "operator": ">",  "value": 100000 },
      "then": { "action": "set_value", "field": "status", "value": "pre-approved" }
    },
    {
      "if":   { "field": "salary", "operator": "<=", "value": 100000 },
      "then": { "action": "set_status", "value": "under_review" }
    }
  ],
  "settings": {
    "theme":  "indigo",
    "style":  "modern",
    "font":   "sans",
    "radius": "rounded",
    "layout": "classic"
  }
}
```

### Field Object Reference

| Key | Required | Description |
|---|---|---|
| `id` | ✓ | Unique field identifier (used in conditions and rules) |
| `type` | ✓ | Field type (see supported types below) |
| `label` | ✓ | Display label |
| `required` | — | Boolean, default false |
| `placeholder` | — | Hint text (text/number/email/textarea) |
| `options` | — | Array of strings (select/radio/checkbox) |
| `validations` | — | Array of `{ type, value }` objects |
| `visibility` | — | `{ condition: { field, operator, value } }` |

### Supported Field Types

| Type | Description |
|---|---|
| `text` | Single-line text |
| `textarea` | Multi-line text |
| `number` | Numeric input |
| `email` | Email address |
| `date` | Date picker |
| `select` | Dropdown (requires `options`) |
| `radio` | Radio button group (requires `options`) |
| `checkbox` | Checkbox group (requires `options`) |

### Supported Validation Types

| Type | Applies to | Description |
|---|---|---|
| `min` | number, text | Minimum value (number) or minimum length (text) |
| `max` | number, text | Maximum value (number) or maximum length (text) |
| `regex` | text, email | Full match against the pattern string |

### `settings` Object

The `settings` key is used by the frontend to render the form with the correct visual design. It is stored but not processed by the backend engines.

| Key | Values | Description |
|---|---|---|
| `theme` | indigo, blue, teal, green, orange, rose, violet, slate | Primary colour |
| `style` | modern, minimal, bold, glass, dark | Card appearance |
| `font` | sans, serif, mono | Typeface |
| `radius` | sharp, rounded, pill | Border radius |
| `layout` | classic, card | Field display mode |

---

## 9. API Endpoints

### Health

| Method | Endpoint | Auth | Response |
|---|---|---|---|
| GET | `/api/health/` | None | `{ "status": "ok" }` |

### User

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/user/register/` | None | Create account — `{ username, email, password, first_name, last_name }` |
| GET | `/api/user/me/` | Required | Current user with nested profile |
| PATCH | `/api/user/me/` | Required | Update `email`, `first_name`, `last_name` |
| DELETE | `/api/user/me/` | Required | Delete account |
| GET | `/api/user/me/profile/` | Required | Get profile `{ bio }` |
| PATCH | `/api/user/me/profile/` | Required | Update `bio` |

### Builder — Authenticated

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/builder/forms/` | Required | List forms owned by the current user |
| POST | `/api/builder/forms/` | Required | Create form — schema validated by `schema_parser` |
| GET | `/api/builder/forms/{id}/` | Required | Retrieve form with full schema |
| PATCH | `/api/builder/forms/{id}/` | Required | Update form — schema change bumps `version` |
| DELETE | `/api/builder/forms/{id}/` | Required | Delete form and all submissions |
| POST | `/api/builder/forms/{id}/submit/` | Required | Run engine pipeline; store submission if final step |
| GET | `/api/builder/forms/{id}/submissions/` | Required | List all submissions (owner only) |
| GET | `/api/builder/forms/{id}/draft/` | Required | Get current user's draft |
| POST | `/api/builder/forms/{id}/draft/` | Required | Save or update draft |
| DELETE | `/api/builder/forms/{id}/draft/` | Required | Delete draft |

### Builder — Public (no auth)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/builder/forms/{id}/share/` | None | Retrieve form schema for public rendering |
| POST | `/api/builder/forms/{id}/share/submit/` | None | Submit form — same engine pipeline, no user stored |

### Request / Response Reference

**POST `/api/builder/forms/{id}/submit/`**

Request:
```json
{
  "current_step": "step_personal",
  "data": {
    "employment_status": "employed",
    "salary": 120000
  }
}
```

Response — more steps remain:
```json
{
  "next_step": "step_financial",
  "data": { "employment_status": "employed", "salary": 120000 }
}
```

Response — final step (201 Created):
```json
{
  "id": 7,
  "form": 1,
  "version": 2,
  "data": {
    "employment_status": "employed",
    "salary": 120000,
    "status": "pre-approved"
  },
  "created_at": "2026-05-05T10:00:00Z"
}
```

Response — validation failure (400):
```json
{
  "errors": {
    "salary": ["Value must be at least 10000."],
    "loan_amount": ["This field is required."]
  }
}
```

---

## 10. Data Flow

### Form Creation

```
Client
  │  POST /api/builder/forms/
  │  { name, is_published, schema: { steps, navigation, rules, settings } }
  ▼
FormSerializer.validate_schema()
  │  calls schema_parser.parse_and_validate(schema)
  │  → checks structural rules (unique IDs, valid types, valid operators...)
  │  → 400 { schema: ["steps[0].fields[1]: duplicate field id"] } if invalid
  ▼
Form.objects.create(owner=request.user, schema=schema, version=1)
  │
  ▼
201 { id, owner, name, version, schema, is_published, created_at }
```

### Form Update (version bump)

```
Client
  │  PATCH /api/builder/forms/{id}/
  │  { schema: { ... updated ... } }
  ▼
schema_parser validates new schema
  ▼
form.version += 1
form.schema  = new_schema
form.save()
  │
  ▼
200 { ..., version: 3, schema: { ... } }
```

Existing submissions retain their `version` field, so the submission record always reflects the exact schema that was active when the user filled the form.

### Form Submission (multi-step)

```
Step 1                     Step 2 (final)
  │                            │
POST /submit/              POST /submit/
  { current_step: "s1",      { current_step: "s2",
    data: { f1: v1 } }         data: { f1: v1, f2: v2 } }
  │                            │
validate (s1 fields)       validate (s2 fields)
  │ ✓                          │ ✓
rule_engine                rule_engine
  │                            │  → data["status"] = "pre-approved"
nav_engine → "s2"          nav_engine → None
  │                            │
200 { next_step: "s2",     Submission.create()
      data: {...} }         201 { id, version, data }
```

### Public Share

```
Share URL copied → localhost:5173/share/{id}
                         │
                         ▼
                  GET /api/builder/forms/{id}/share/   (no auth)
                  returns same schema as authenticated GET
                         │
                         ▼
                  User fills form
                         │
                         ▼
                  POST /api/builder/forms/{id}/share/submit/
                  same engine pipeline runs
                  Submission stored (user field = null)
                  201 { id, version, data }
```

---

## 11. Authentication

Django REST Framework's built-in **HTTP Basic Authentication** is used.

```
Authorization: Basic base64(username:password)
```

### Permission Classes

| Endpoint group | Permission |
|---|---|
| `/api/user/register/` | `AllowAny` |
| `/api/health/` | `AllowAny` |
| `/api/builder/forms/{id}/share/` | `AllowAny` |
| `/api/builder/forms/{id}/share/submit/` | `AllowAny` |
| All other endpoints | `IsAuthenticated` |

### Ownership Enforcement

All authenticated `builder` endpoints filter by `owner=request.user`:

```python
Form.objects.filter(owner=request.user)          # list
get_object_or_404(Form, pk=pk, owner=request.user) # detail, patch, delete
```

Users cannot read, modify, or delete another user's forms.

---

## 12. Environment & Configuration

Configuration is read exclusively via `os.environ`. The `env_loader.py` module reads a `.env` file and calls `os.environ.setdefault()` — Docker environment variables always take precedence since they are already set before `env_loader` runs.

### `.env` — local development (SQLite)

```ini
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

### `.env.docker` — Docker (PostgreSQL)

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

### Database Connection Logic (`config/settings.py`)

```python
_DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')
_DB_NAME   = os.environ.get('DB_NAME', 'db.sqlite3')

DATABASES = {
    'default': {
        'ENGINE':   _DB_ENGINE,
        'NAME':     BASE_DIR / _DB_NAME if _DB_ENGINE == 'django.db.backends.sqlite3' else _DB_NAME,
        'USER':     os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST':     os.environ.get('DB_HOST', ''),
        'PORT':     os.environ.get('DB_PORT', ''),
    }
}
```

SQLite receives a `Path` object; PostgreSQL receives a plain string. No other code changes are needed to switch between databases.

---

## 13. Docker & Infrastructure

### Services

```
docker-compose.yml
  │
  ├── db   postgres:15-alpine
  │         POSTGRES_DB:       dynamic_form_db
  │         POSTGRES_USER:     postgres
  │         POSTGRES_PASSWORD: postgres
  │         ports:             5433 (host) → 5432 (container)
  │         volume:            postgres_data  (named, persistent)
  │         healthcheck:       pg_isready -U postgres -d dynamic_form_db
  │                            interval: 5s  retries: 10
  │
  └── web  built from ./Dockerfile
            base image:   python:3.11-slim
            system deps:  libpq-dev, gcc   (required by psycopg2)
            pip install:  -r requirements.txt
            env_file:     .env.docker
            ports:        8001 (host) → 8001 (container)
            volume:       . → /app            (live reload in dev)
            depends_on:   db (condition: service_healthy)
            entrypoint:   sh entrypoint.sh
```

### entrypoint.sh

```sh
#!/bin/sh
set -e
python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8001
```

Migrations run automatically every time the container starts. If there is nothing to migrate, Django skips them silently.

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x entrypoint.sh
EXPOSE 8001
ENTRYPOINT ["sh", "entrypoint.sh"]
```

### Commands

```bash
# Build and start both services
docker-compose up --build

# Run in background
docker-compose up --build -d

# Run migrations manually
docker-compose exec web python manage.py migrate

# Seed test data (users, forms, submissions, draft)
docker-compose exec web python manage.py seed_db

# Create a superuser
docker-compose exec web python manage.py createsuperuser

# Open Django shell
docker-compose exec web python manage.py shell

# Stream logs
docker-compose logs -f web
docker-compose logs -f db

# Stop containers (keep DB volume)
docker-compose down

# Stop and delete all data
docker-compose down -v
```

### Seeded Test Data (`seed_db`)

Running `python manage.py seed_db` creates:

| Resource | Details |
|---|---|
| Users | `admin / admin123` (superuser), `testuser / testpass123` |
| Form 1 | **Loan Application** — 2 steps, visibility conditions, navigation rules, 3 post-submit rules, published |
| Form 2 | **Contact Form** — 1 step, min-length validation, 1 post-submit rule, published |
| Submissions | 3 for Loan Application (Alice pre-approved, Bob under_review+tagged, Carol self-employed) |
| Submissions | 2 for Contact Form (David needs_support, Eve sales) |
| Draft | Contact Form — 3 of 4 fields filled by testuser |

---

## 14. Security Considerations

| Area | Implementation |
|---|---|
| **Schema validation** | `schema_parser` runs on every create/update; malformed schemas are rejected before the DB is touched |
| **No dynamic execution** | The condition, rule, and navigation engines use explicit operator whitelists — no `eval()`, no `exec()` |
| **Input validation** | DRF serialisers validate all request data; JSON fields only accept valid JSON |
| **Ownership enforcement** | All authenticated form endpoints scope queries to `owner=request.user` |
| **Public endpoint scope** | Share endpoints are read + submit only; no schema modification without auth |
| **CORS** | Restricted to `localhost:5173` and `127.0.0.1:5173` in development |
| **Secret key** | Always loaded from `SECRET_KEY` environment variable |
| **SQL injection** | Django ORM + parameterised queries throughout; no raw SQL |
| **Credentials** | Never logged; loaded from environment at startup |
| **Version consistency** | Submissions record the form version at time of submission; old data is never invalidated by schema updates |

---

*Last updated: 2026-05-05*
