# System Design — Dynamic Form Builder & Execution Engine

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Backend Design](#5-backend-design)
   - 5.1 [Django Apps](#51-django-apps)
   - 5.2 [Database Models](#52-database-models)
   - 5.3 [Engine Pipeline](#53-engine-pipeline)
   - 5.4 [Schema DSL](#54-schema-dsl)
   - 5.5 [API Endpoints](#55-api-endpoints)
6. [Frontend Design](#6-frontend-design)
   - 6.1 [Page Map](#61-page-map)
   - 6.2 [Component Tree](#62-component-tree)
   - 6.3 [State & Context](#63-state--context)
   - 6.4 [Design System](#64-design-system)
7. [Data Flow](#7-data-flow)
   - 7.1 [Form Creation](#71-form-creation)
   - 7.2 [Form Submission](#72-form-submission)
   - 7.3 [Public Share](#73-public-share)
8. [Authentication](#8-authentication)
9. [Docker & Infrastructure](#9-docker--infrastructure)
10. [Security Considerations](#10-security-considerations)
11. [Feature Summary](#11-feature-summary)

---

## 1. Overview

**Dynamic Form Builder** is a full-stack schema-driven form engine where forms are defined as structured JSON (a DSL), stored in a database, and executed by a backend pipeline. The frontend acts purely as a rendering layer — it receives the schema and renders it; all business logic (validation, conditional visibility, navigation, post-submit rules) lives in the backend.

### Problem Statement

Traditional forms are statically coded in the frontend. Any change in structure or logic requires a code deployment. This system decouples form logic from the UI, enabling:

- Form updates without code changes
- Multi-step, conditional, and rule-driven workflows
- Sharable public forms without requiring login
- Versioned forms where old submissions remain valid

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Browser)                           │
│                                                                     │
│   React + Vite + Tailwind CSS                                       │
│   ┌───────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│   │ Form List │  │ Form Builder │  │ Form Renderer (fill/share)│   │
│   └───────────┘  └──────────────┘  └──────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP / REST (Basic Auth)
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                       DJANGO + DRF (port 8001)                      │
│                                                                     │
│  ┌──────────┐  ┌──────────────────────────────────────────────┐    │
│  │  user/   │  │                  builder/                    │    │
│  │  app     │  │  ┌──────────────────────────────────────┐   │    │
│  └──────────┘  │  │           Engine Pipeline             │   │    │
│                │  │                                        │   │    │
│  ┌──────────┐  │  │  SchemaParser → ValidationEngine      │   │    │
│  │  api/    │  │  │  ConditionEngine → NavigationEngine   │   │    │
│  │  health  │  │  │  RuleEngine                           │   │    │
│  └──────────┘  │  └──────────────────────────────────────┘   │    │
│                └──────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    PostgreSQL (port 5433 → 5432)                    │
│                                                                     │
│   auth_user │ user_userprofile │ builder_form │                     │
│   builder_submission │ builder_draftsubmission                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Backend Framework** | Django | 4.2 | Web framework |
| **API** | Django REST Framework | 3.15 | RESTful API layer |
| **Database** | PostgreSQL | 15 | Primary data store |
| **DB Driver** | psycopg2-binary | 2.9 | Python ↔ PostgreSQL |
| **CORS** | django-cors-headers | 4.3 | Cross-origin requests |
| **Frontend** | React | 18 | UI library |
| **Build Tool** | Vite | 8 | Dev server + bundler |
| **CSS** | Tailwind CSS | 3 | Utility-first styling |
| **HTTP Client** | Axios | latest | API calls |
| **Routing** | React Router DOM | 6 | Client-side routing |
| **Container** | Docker + Compose | 3.9 | Deployment |

---

## 4. Project Structure

```
dynamic_form/
├── SYSTEM_DESIGN.md
│
├── backend/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   ├── .env                      ← local dev (SQLite)
│   ├── .env.docker               ← Docker (PostgreSQL)
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── manage.py
│   ├── env_loader.py             ← reads .env using os module
│   │
│   ├── config/                   ← Django project package
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── api/                      ← health check app
│   │   ├── views.py
│   │   └── urls.py
│   │
│   ├── user/                     ← user management app
│   │   ├── models.py             ← UserProfile
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   │
│   └── builder/                  ← core form engine app
│       ├── models.py             ← Form, Submission, DraftSubmission
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       ├── admin.py
│       ├── engines/
│       │   ├── schema_parser.py
│       │   ├── condition_engine.py
│       │   ├── validation_engine.py
│       │   ├── navigation_engine.py
│       │   └── rule_engine.py
│       └── management/commands/
│           └── seed_db.py
│
└── frontend/
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── api/
        │   └── client.js         ← axios (auth) + publicClient (no auth)
        ├── context/
        │   ├── AuthContext.jsx
        │   └── ThemeContext.jsx
        ├── utils/
        │   ├── themes.js         ← color themes, styles, fonts, radii, layouts
        │   ├── conditionEngine.js ← mirrors backend (real-time field visibility)
        │   └── schemaHelpers.js  ← genId, createStep/Field/NavRule/Rule, cleanSchema
        ├── pages/
        │   ├── LoginPage.jsx
        │   ├── FormsListPage.jsx
        │   ├── FormPage.jsx
        │   ├── FormBuilderPage.jsx
        │   ├── PublicFormPage.jsx
        │   └── SuccessPage.jsx
        └── components/
            ├── FormRenderer.jsx
            ├── FormStep.jsx
            ├── CardStep.jsx
            ├── FormField.jsx
            ├── ProgressBar.jsx
            ├── builder/
            │   ├── StepList.jsx
            │   ├── FieldCard.jsx
            │   ├── ThemePicker.jsx
            │   ├── DesignPreview.jsx
            │   ├── NavigationEditor.jsx
            │   ├── RulesEditor.jsx
            │   ├── ValidationsEditor.jsx
            │   ├── VisibilityEditor.jsx
            │   └── OptionsEditor.jsx
            ├── fields/
            │   ├── TextField.jsx
            │   ├── TextareaField.jsx
            │   ├── NumberField.jsx
            │   ├── EmailField.jsx
            │   ├── DateField.jsx
            │   ├── SelectField.jsx
            │   ├── RadioField.jsx
            │   └── CheckboxField.jsx
            └── ui/
                ├── Button.jsx
                ├── Badge.jsx
                ├── Spinner.jsx
                └── ShareButton.jsx
```

---

## 5. Backend Design

### 5.1 Django Apps

| App | Responsibility |
|---|---|
| `api` | Health check endpoint |
| `user` | Registration, profile, account management |
| `builder` | Form CRUD, engine pipeline, submissions, drafts, public share |

### 5.2 Database Models

#### Entity Relationship Diagram

```
auth_user
    │
    ├──< UserProfile (1:1)
    │       └── bio, created_at, updated_at
    │
    ├──< Form (1:N, owner)
    │       ├── name
    │       ├── version          ← increments on each schema update
    │       ├── schema (JSONB)   ← full DSL: steps, navigation, rules, settings
    │       ├── is_published
    │       ├── created_at
    │       └── updated_at
    │             │
    │             ├──< Submission (1:N)
    │             │       ├── version  ← snapshot of form version at submit time
    │             │       ├── data (JSONB)
    │             │       └── created_at
    │             │
    │             └──< DraftSubmission (1:N, unique per user+form)
    │                     ├── user (FK, nullable)
    │                     ├── partial_data (JSONB)
    │                     └── updated_at
    │
    └──< DraftSubmission (1:N, user)
```

#### Model Details

**Form**
```python
name        CharField        # human-readable form name
version     PositiveInteger  # auto-incremented on schema change
schema      JSONField        # full DSL (see Section 5.4)
is_published BooleanField    # controls who can submit
owner       FK → auth_user
```

**Submission**
```python
form      FK → Form
version   PositiveInteger   # version of form at time of submission
data      JSONField         # submitted values + rule mutations (_status, _tags)
```

**DraftSubmission**
```python
user          FK → auth_user (nullable)
form          FK → Form
partial_data  JSONField
unique_together: (user, form)
```

### 5.3 Engine Pipeline

All five engines live in `builder/engines/`. They run on every `POST /submit/` call in this order:

```
POST /forms/{id}/submit/
         │
         ▼
  1. schema_parser        ← runs at CREATE/UPDATE time, not submit time
         │
         ▼ (submit time)
  2. validation_engine
     └── calls condition_engine.get_visible_fields()
         only validates visible fields
         returns { field_id: [errors] }
         │
         ▼ (if valid)
  3. rule_engine
     └── calls condition_engine.evaluate_condition()
         mutates data: set_value / tag / set_status
         │
         ▼
  4. navigation_engine
     └── calls condition_engine.evaluate_condition()
         checks explicit nav rules → falls back to linear order
         returns next_step_id or None
         │
         ▼
  ┌──────┴───────┐
  │              │
next_step      no next_step
  │              │
return         store Submission
{ next_step,   return 201
  data }
```

#### Engine Responsibilities

| Engine | Input | Output |
|---|---|---|
| `schema_parser` | Raw schema dict | `(is_valid, [errors])` |
| `condition_engine` | Condition object + data dict | `True / False` |
| `validation_engine` | Schema + submitted data | `(is_valid, {field: [errors]})` |
| `navigation_engine` | Schema + current_step + data | `next_step_id` or `None` |
| `rule_engine` | Schema + data | Mutated data dict |

#### Condition Operators

| Operator | Description |
|---|---|
| `==` | Equal (string comparison) |
| `!=` | Not equal |
| `>` | Greater than (numeric) |
| `<` | Less than (numeric) |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |

#### Rule Actions

| Action | Effect |
|---|---|
| `set_value` | Writes a value to a specific field in `data` |
| `set_status` | Writes to `data._status` |
| `tag` | Appends a string to `data._tags[]` |

### 5.4 Schema DSL

The entire form definition is stored as a single JSON document in `Form.schema`.

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
            { "type": "min", "value": 10000 }
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
    }
  ],
  "navigation": [
    {
      "from_step": "step_personal",
      "to_step":   "step_financial",
      "condition": {
        "field": "employment_status",
        "operator": "!=",
        "value":  "unemployed"
      }
    }
  ],
  "rules": [
    {
      "if":   { "field": "salary", "operator": ">", "value": 100000 },
      "then": { "action": "set_value", "field": "status", "value": "pre-approved" }
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

#### Supported Field Types

| Type | Input rendered |
|---|---|
| `text` | Single-line text input |
| `textarea` | Multi-line text input |
| `number` | Numeric input |
| `email` | Email input with format validation |
| `date` | Date picker |
| `select` | Dropdown with `options[]` |
| `radio` | Radio group with `options[]` |
| `checkbox` | Checkbox group with `options[]` |

#### Supported Validation Types

| Type | Applies to | Description |
|---|---|---|
| `min` | number, text | Minimum value or minimum character length |
| `max` | number, text | Maximum value or maximum character length |
| `regex` | text, email | Value must match the regex pattern |

### 5.5 API Endpoints

#### Health

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/health/` | None | Service health check |

#### User

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/user/register/` | None | Create new user |
| GET | `/api/user/me/` | Required | Get current user + profile |
| PATCH | `/api/user/me/` | Required | Update name / email |
| DELETE | `/api/user/me/` | Required | Delete account |
| GET | `/api/user/me/profile/` | Required | Get profile (bio) |
| PATCH | `/api/user/me/profile/` | Required | Update profile |

#### Builder — Authenticated

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/builder/forms/` | Required | List all forms owned by user |
| POST | `/api/builder/forms/` | Required | Create form (validates schema DSL) |
| GET | `/api/builder/forms/{id}/` | Required | Get form with full schema |
| PATCH | `/api/builder/forms/{id}/` | Required | Update form (bumps version on schema change) |
| DELETE | `/api/builder/forms/{id}/` | Required | Delete form |
| POST | `/api/builder/forms/{id}/submit/` | Required | Run engine pipeline, store submission |
| GET | `/api/builder/forms/{id}/submissions/` | Required | List submissions (owner only) |
| GET | `/api/builder/forms/{id}/draft/` | Required | Get saved draft |
| POST | `/api/builder/forms/{id}/draft/` | Required | Save / update draft |
| DELETE | `/api/builder/forms/{id}/draft/` | Required | Delete draft |

#### Builder — Public (no auth)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/builder/forms/{id}/share/` | None | Get form schema for public rendering |
| POST | `/api/builder/forms/{id}/share/submit/` | None | Submit form publicly |

---

## 6. Frontend Design

### 6.1 Page Map

```
/login                  LoginPage          (public)
/                       FormsListPage      (protected)
/forms/:id              FormPage           (protected)
/forms/:id/success      SuccessPage        (protected)
/builder/new            FormBuilderPage    (protected, create mode)
/builder/:id            FormBuilderPage    (protected, edit mode)
/share/:id              PublicFormPage     (public — no login required)
/share/:id/success      SuccessPage        (public)
```

### 6.2 Component Tree

```
App
├── AuthProvider
├── BrowserRouter
│
├── LoginPage
│
├── FormsListPage
│   ├── Search input
│   ├── Status filter pills  (All / Published / Draft)
│   ├── View toggle          (List / Grid)
│   ├── ListRow[]            (fill + share + edit)
│   └── GridCard[]           (fill + share + edit)
│
├── FormBuilderPage
│   ├── Sticky header        (name input, publish toggle, share, save)
│   ├── Tab bar              (Steps / Navigation / Rules / Design)
│   │
│   ├── Steps tab
│   │   ├── StepList         (add / rename / delete steps)
│   │   └── FieldCard[]      (collapsible field editor)
│   │       ├── OptionsEditor
│   │       ├── ValidationsEditor
│   │       └── VisibilityEditor
│   │
│   ├── Navigation tab → NavigationEditor
│   ├── Rules tab      → RulesEditor
│   └── Design tab
│       ├── ThemePicker      (colour / style / layout / font / shape)
│       └── DesignPreview    (live browser-frame preview)
│
├── FormPage / PublicFormPage
│   └── FormRenderer         (applies design settings)
│       ├── ThemeProvider    (CSS variables)
│       ├── ProgressBar
│       └── FormCard (style-specific wrapper)
│           ├── FormStep     (classic layout — all fields)
│           │   └── FormField[]
│           │       └── TextField / NumberField / SelectField / ...
│           └── CardStep     (card layout — one field at a time)
│
└── SuccessPage
```

### 6.3 State & Context

| Context | Provider | Consumers | State held |
|---|---|---|---|
| `AuthContext` | `App` | All protected pages | `authenticated`, `login()`, `logout()` |
| `ThemeContext` (+ Design) | `FormRenderer` | `ProgressBar`, `CardStep`, buttons | Full design object: theme colours + style + font + radius + layout |

#### Credentials flow
```
LoginPage → login(username, password)
         → setCredentials() → btoa(user:pass) → localStorage
         → client.interceptors adds Authorization: Basic … header
```

#### Design context flow
```
Form.schema.settings → getDesign(settings) → ThemeProvider
  sets CSS variables:
    --theme-color, --theme-color-dark, --theme-color-light
    --theme-color-text, --theme-color-ring
    --input-radius, --card-radius, --font-family
  sets data attributes:
    data-theme, data-style
  CSS classes .t-btn, .t-progress-fill, .t-step-active
  read these variables at render time
```

### 6.4 Design System

The form appearance is fully configurable per-form via `schema.settings`.

#### Colour Themes (8)

| ID | Name | Primary |
|---|---|---|
| `indigo` | Indigo | `#4f46e5` |
| `blue` | Ocean | `#0284c7` |
| `teal` | Teal | `#0d9488` |
| `green` | Forest | `#16a34a` |
| `orange` | Sunset | `#ea580c` |
| `rose` | Rose | `#e11d48` |
| `violet` | Violet | `#7c3aed` |
| `slate` | Slate | `#475569` |

#### Style Presets (5)

| ID | Description |
|---|---|
| `modern` | White card with border and shadow |
| `minimal` | No card — fields float on the background |
| `bold` | Coloured header block + white body |
| `glass` | Frosted glass card over gradient background |
| `dark` | Dark card (`#1e293b`) with light text |

#### Layouts (2)

| ID | Description |
|---|---|
| `classic` | All fields visible at once per step |
| `card` | One field at a time with slide animation (Typeform-style) |

#### Fonts (3) · Border Radii (3)

| Font | Family | &nbsp; | Radius | Input |
|---|---|---|---|---|
| `sans` | Inter | &nbsp; | `sharp` | `0` |
| `serif` | Georgia | &nbsp; | `rounded` | `0.5rem` |
| `mono` | Courier New | &nbsp; | `pill` | `9999px` |

---

## 7. Data Flow

### 7.1 Form Creation

```
User (FormBuilderPage)
  │
  │  1. Fills name, adds steps + fields, sets design
  │
  ▼
ThemePicker / FieldCard / StepList
  │
  │  2. Local state: schema object (steps/navigation/rules/settings)
  │
  ▼
handleSave()
  │
  │  3. cleanSchema() strips internal _id fields
  │
  ▼
POST /api/builder/forms/     (create)
PATCH /api/builder/forms/id/ (update → version++)
  │
  │  4. FormSerializer.validate_schema()
  │     calls schema_parser.parse_and_validate()
  │     → rejects malformed DSL with error list
  │
  ▼
Form saved to PostgreSQL (schema JSONB)
```

### 7.2 Form Submission

```
User fills fields in FormRenderer
  │
  │  1. handleSubmit() called (classic: Next/Submit button)
  │                           (card: OK → or Enter key)
  │
  ▼
POST /api/builder/forms/id/submit/
  { current_step: "step_1", data: { field_id: value, ... } }
  │
  │  2. validation_engine.validate_submission(schema, data)
  │     → condition_engine.get_visible_fields()  (skip hidden)
  │     → check required, min, max, regex
  │     ← 400 { errors: { field_id: ["msg"] } } if invalid
  │
  ▼  (valid)
  │  3. rule_engine.execute_rules(schema, data)
  │     → for each rule: evaluate_condition(if, data)
  │     → if true: apply then action (set_value / tag / set_status)
  │     ← mutated data dict
  │
  ▼
  │  4. navigation_engine.get_next_step(schema, current_step, data)
  │     → check explicit navigation[] rules first
  │     → fall back to linear step order
  │     ← next_step_id or None
  │
  ├── next_step exists → 200 { next_step, data }
  │                           Frontend advances to next step
  │
  └── no next_step   → Submission.objects.create(...)
                        201 { id, form, version, data }
                        Frontend navigates to /success
```

### 7.3 Public Share

```
Builder clicks Share button
  → copies window.location.origin + /share/{form_id} to clipboard

Anonymous user opens /share/{form_id}
  │
  ▼
PublicFormPage
  → publicClient.get(/api/builder/forms/id/share/)   ← no auth header
  → renders FormRenderer with submitFn override
  │
  ▼
User submits
  → publicClient.post(/api/builder/forms/id/share/submit/)
  → same engine pipeline runs
  → Submission stored with no user reference
  → Redirects to /share/id/success
```

---

## 8. Authentication

The API uses **HTTP Basic Authentication** (Django REST Framework default).

```
Client                          Server
  │                               │
  │  POST /api/user/register/     │
  │  { username, password, ... }  │
  │──────────────────────────────▶│
  │  201 { id, username, ... }    │
  │◀──────────────────────────────│
  │                               │
  │  Any protected request        │
  │  Authorization: Basic         │
  │  base64(username:password)    │
  │──────────────────────────────▶│
  │  200 / 201 / 204              │
  │◀──────────────────────────────│
```

**Frontend storage:** credentials are stored as `btoa(user:pass)` in `localStorage` and attached to every axios request via an interceptor. Public endpoints use a separate `publicClient` instance with no interceptor.

**Scope:** Public share endpoints (`/share/` and `/share/submit/`) use `AllowAny` permission and require no credentials.

---

## 9. Docker & Infrastructure

### Services

```
docker-compose.yml
  │
  ├── db  (postgres:15-alpine)
  │   ├── POSTGRES_DB:       dynamic_form_db
  │   ├── POSTGRES_USER:     postgres
  │   ├── POSTGRES_PASSWORD: postgres
  │   ├── host port:         5433 → container: 5432
  │   ├── volume:            postgres_data (persistent)
  │   └── healthcheck:       pg_isready -U postgres -d dynamic_form_db
  │
  └── web  (built from Dockerfile)
      ├── base image:  python:3.11-slim
      ├── system deps: libpq-dev, gcc  (for psycopg2)
      ├── env_file:    .env.docker
      ├── host port:   8001 → container: 8001
      ├── volume:      . → /app  (live code reload)
      ├── depends_on:  db (healthy)
      └── entrypoint:  migrate → runserver 0.0.0.0:8001
```

### Environment Variables

| Variable | Local (`.env`) | Docker (`.env.docker`) |
|---|---|---|
| `SECRET_KEY` | dev key | change in production |
| `DEBUG` | `True` | `True` |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | `127.0.0.1,localhost,0.0.0.0,web` |
| `DB_ENGINE` | `django.db.backends.sqlite3` | `django.db.backends.postgresql` |
| `DB_NAME` | `db.sqlite3` | `dynamic_form_db` |
| `DB_USER` | _(empty)_ | `postgres` |
| `DB_PASSWORD` | _(empty)_ | `postgres` |
| `DB_HOST` | _(empty)_ | `db` |
| `DB_PORT` | _(empty)_ | `5432` |
| `DB_HOST_PORT` | N/A | `5433` |

### Database Connection Logic (`settings.py`)

```python
# SQLite  → NAME is a filesystem Path
# PostgreSQL → NAME is a plain string
NAME = BASE_DIR / DB_NAME  if ENGINE == 'sqlite3'  else DB_NAME
```

### Commands

```bash
# Start everything (builds image on first run)
docker-compose up --build

# Run in background
docker-compose up --build -d

# Apply migrations manually
docker-compose exec web python manage.py migrate

# Seed test data
docker-compose exec web python manage.py seed_db

# Open Django shell
docker-compose exec web python manage.py shell

# View logs
docker-compose logs -f web
docker-compose logs -f db

# Stop (keep DB volume)
docker-compose down

# Stop and wipe database
docker-compose down -v
```

---

## 10. Security Considerations

| Area | Implementation |
|---|---|
| **Schema validation** | Every create/update runs `schema_parser` before writing to DB; malformed schemas are rejected with structured error messages |
| **Input sanitisation** | DRF serialisers validate all incoming data; JSON fields accept only valid JSON |
| **Condition engine** | No `eval()` or dynamic code execution; conditions are evaluated with explicit operator checks |
| **Rule engine** | Actions are whitelisted (`set_value`, `tag`, `set_status`); no arbitrary code paths |
| **Ownership enforcement** | All authenticated form endpoints filter by `owner=request.user`; users cannot access other users' forms |
| **Public endpoints** | Only expose read + submit; no schema modification possible without auth |
| **Credentials** | Stored as Base64 in `localStorage`; use HTTPS in production |
| **CORS** | Restricted to `localhost:5173` and `127.0.0.1:5173` in development |
| **Secret key** | Loaded from environment variable; never hardcoded |
| **SQL injection** | Django ORM + DRF parameterised queries; no raw SQL used |

---

## 11. Feature Summary

### Form Builder
- Multi-step form creation with drag-and-drop field ordering
- 8 field types: text, textarea, number, email, date, select, radio, checkbox
- Per-field configuration: label, placeholder, required toggle, options
- Validation rules: min, max, regex
- Visibility conditions: show/hide fields based on other field values
- Step navigation rules: conditional step routing
- Post-submit rules: `set_value`, `set_status`, `tag`
- Form versioning: every schema update increments the version
- Design tab: live preview with full design customisation

### Form Filling
- Multi-step rendering with progress bar
- Real-time field visibility (condition engine mirrored in frontend)
- Backend-authoritative validation with field-level error messages
- Backend-driven navigation (frontend follows `next_step` from API)
- Draft save and restore (per user per form)
- Classic layout (all fields visible) and Card layout (one field at a time)

### Design System
- 8 colour themes, 5 style presets, 2 layouts, 3 fonts, 3 border radii
- All settings stored in `schema.settings` — no code change needed
- Live preview in the builder showing exact rendering
- CSS variable architecture: single wrapper div sets all design tokens

### Sharing
- Public share link (`/share/:id`) — no login required
- Separate `publicClient` (no auth header)
- Separate backend endpoints (`AllowAny` permission)
- Shared forms respect all design settings (theme, style, layout)

### Forms List
- Grid and list view with localStorage persistence
- Live search by form name
- Filter by status (All / Published / Draft) with counts
- Per-form actions: Fill Out, Share (copy link), Edit

### Infrastructure
- Docker Compose: PostgreSQL 15 + Django 4.2 services
- Health-check–gated startup (web waits for db to be ready)
- Automatic migrations on container start
- Seed command for test data (`seed_db`)
- SQLite for local dev, PostgreSQL for Docker — same settings file

---

*Last updated: 2026-05-05*
