# Vigil

Vigil is a small security-operations console for a cybersecurity portfolio or a university demonstration. It is a real FastAPI and React application: registration, login, role checks, audit logs, and the automated tests all run against the API.

The controls below are defensive patterns mapped to common OWASP Top 10 risks. Implementing them does **not** make the project "OWASP compliant." Compliance is an assessment of a deployed system, not a checklist in a student repository.

## Architecture

```text
Browser (React, Vite, Tailwind)
        |  same-origin /api via the Vite proxy
        v
FastAPI
  routers: auth, users, dashboard, logs, settings
  Argon2id passwords, JWT access tokens, server-side sessions
  SQLAlchemy ORM (bound parameters)
        |
        v
SQLite by default, or PostgreSQL when DATABASE_URL is set
```

The browser does not store the access token in `localStorage`. Login sets an HttpOnly `access_token` cookie and a readable `csrf_token` cookie. Mutating requests from the console send that CSRF value back in `X-CSRF-Token`. API clients may instead send `Authorization: Bearer`. Bearer requests skip the CSRF check because a browser will not attach that header on its own.

Authorization uses the role stored in the database. A normal user's hidden navigation is only a convenience; the API returns 403 or 404 on its own.

## Features

- Register, login, logout, token expiry, and server-side session revocation.
- Argon2id password hashes and a password-strength policy.
- Roles: `admin`, `analyst`, and `user`.
- Dashboard with user totals, active sessions, recent logins, failed logins, security events, and audit rows.
- User directory, profile updates, password changes, and admin role / status changes.
- Audit log for logins, logouts, password changes, role changes, lockouts, and denied access.
- Security headers, generic authentication errors, and an in-process login rate limit.

## Tech stack

| Area | Choice |
| --- | --- |
| API | Python, FastAPI, Pydantic, SQLAlchemy |
| Data | PostgreSQL, or SQLite when no database URL is configured |
| Auth | PyJWT, Argon2id (`argon2-cffi`) |
| UI | React, Vite, JavaScript, Tailwind CSS, Axios, React Router, Lucide |
| Tests | pytest, FastAPI `TestClient` |

## Installation

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend
npm install
```

## Database setup

On startup the API creates tables with `Base.metadata.create_all`. That is appropriate for this demo. A production service would use reviewed migrations instead.

### SQLite (default)

Leave `DATABASE_URL` unset. The API creates `backend/aegis.db` on first launch. The file is gitignored.

With `SEED_DEMO_USERS=true` and an empty user table, three local accounts are inserted:

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@example.com | VigilAdmin!234 |
| Security analyst | analyst@example.com | VigilAnalyst!234 |
| Normal user | user@example.com | VigilUser!234 |

These exist for a local demonstration. Do not reuse the passwords anywhere else. The addresses use `example.com` because the email validator rejects special-use domains such as `.local`.

### PostgreSQL

```sql
CREATE USER vigil WITH PASSWORD 'choose-a-password';
CREATE DATABASE vigil OWNER vigil;
```

Set `DATABASE_URL` in `.env`:

```text
DATABASE_URL=postgresql+psycopg://vigil:choose-a-password@localhost:5432/vigil
```

Restart the API. Tables are created on startup. If that URL is set and PostgreSQL is down, startup fails on purpose. There is no silent fallback once you have chosen PostgreSQL.

## Environment configuration

```powershell
copy .env.example .env
```

Replace `JWT_SECRET` before any shared deployment. `ENVIRONMENT=production` refuses the sample secret, refuses a secret shorter than 32 characters, and requires `COOKIE_SECURE=true`.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Optional. Unset means SQLite. |
| `JWT_SECRET` | HMAC secret for access tokens. |
| `ACCESS_TOKEN_MINUTES` | Token and cookie lifetime. Default 30. |
| `COOKIE_SECURE` | Set `true` only behind HTTPS. |
| `SEED_DEMO_USERS` | Seed the three demo accounts into an empty database. |
| `RATE_LIMIT_LOGIN` | Failed logins allowed per IP and per email. |
| `RATE_LIMIT_WINDOW_SECONDS` | Window for that limit. |
| `ENABLE_DOCS` | Interactive API docs at `/docs`. |
| `TRUST_PROXY` | When `true`, the first `X-Forwarded-For` hop is stored. Leave `false` unless a trusted proxy overwrites that header. |
| `CORS_ORIGINS` | Allowed browser origins if the UI is not using the Vite proxy. |

## Backend startup

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: `http://127.0.0.1:8000/api/health`

Interactive docs, when enabled: `http://127.0.0.1:8000/docs`

## Frontend startup

In a second terminal, from `frontend`:

```powershell
npm run dev
```

Open `http://127.0.0.1:5173`. The dev server proxies `/api` to port 8000, so the cookie stays on the UI origin. If those ports are already taken, start the API on another port and set `VITE_API_PROXY` before `npm run dev` (for example `VITE_API_PROXY=http://127.0.0.1:8010` and `npm run dev -- --port 5174`).

## API documentation

| Method | Path | Who |
| --- | --- | --- |
| POST | `/api/auth/register` | Public. Creates a normal user and a session. |
| POST | `/api/auth/login` | Public. Generic failure text. |
| POST | `/api/auth/logout` | Signed in. Cookie calls also need `X-CSRF-Token`. |
| GET | `/api/auth/me` | Signed in. |
| POST | `/api/auth/revoke-other-sessions` | Signed in. |
| GET | `/api/dashboard` | Signed in. Organization metrics for admin and analyst; personal metrics for a normal user. |
| GET | `/api/users` | Admin, analyst. Optional `q` search. |
| GET | `/api/users/me` | Signed in. |
| PATCH | `/api/users/me` | Signed in. Display name only. |
| POST | `/api/users/me/password` | Signed in. Requires the current password. |
| GET | `/api/users/{id}` | Admin and analyst, or the account owner. Other users get 404. |
| PATCH | `/api/users/{id}/role` | Admin. Cannot change your own role or demote the last active admin. |
| PATCH | `/api/users/{id}/status` | Admin. Disabling an account revokes its sessions. |
| GET | `/api/logs` | Admin, analyst. Optional `event_type`. |
| GET | `/api/settings/security` | Signed in. No secrets. |
| GET | `/api/health` | Public. |

Unknown fields on input bodies are rejected (`extra` is forbidden), so a client cannot submit `role` during registration.

## Security implementations

See [SECURITY.md](SECURITY.md) for the testing guide and a risk-by-risk mapping. Short version:

- Queries go through SQLAlchemy. User search uses a bound `LIKE` pattern with `%` and `_` escaped.
- React renders account names as text. The API returns JSON, not HTML.
- Cookie sessions use a double-submit CSRF token and `SameSite=Lax`.
- Role and object checks run in the API. Denied calls are audited.
- Passwords are hashed with Argon2id. Login compares a dummy hash when the account is missing.
- Failed logins are rate limited per IP and per email. The limit lives in memory for this single process.
- Unhandled exceptions return `Internal server error` without a traceback. Login failures share one message.
- Audit messages are dropped if they contain `password`, `bearer`, or a JWT-shaped `eyJ` fragment.

## OWASP mapping

| Risk | What Vigil does |
| --- | --- |
| Broken Access Control | Server-side roles and per-account checks. Normal users cannot list users, read logs, or edit roles. |
| Cryptographic Failures | Argon2id hashes, JWT expiry, HttpOnly cookies, `Cache-Control: no-store`. |
| Injection | ORM parameters and escaped `LIKE` input. |
| Insecure Design | Server-side sessions can be revoked. Registration cannot choose a role. |
| Security Misconfiguration | Security headers, production secret checks, docs can be disabled, secrets stay in `.env`. |
| Vulnerable Components | Dependencies are pinned in `requirements.txt` and `package.json`. They still need updates. |
| Identification and Authentication Failures | Strength policy, generic errors, rate limit, session revocation. No MFA. |
| Software and Data Integrity Failures | Extra JSON fields are rejected. This demo does not sign releases. |
| Security Logging and Monitoring Failures | Audit table for the events listed above. Not a SIEM. |
| Server-Side Request Forgery | The API does not fetch remote URLs. |

## Testing

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
```

The suite covers registration, login, bad credentials, Argon2, JWT tampering, expiry, roles, unauthorized routes, a SQL injection string in search, validation errors, CSRF on cookie logout, and the login rate limit. Details and manual checks are in [SECURITY.md](SECURITY.md).

Only point those checks at this application on your own machine.

## Screenshots

Capture these after both servers are running. They are not checked in, so the repository stays small.

1. Login, including the seeded-account picker.
2. Registration with the password policy hints.
3. Administrator dashboard: user total, sessions, failures, event bars, audit table.
4. User management with the role control.
5. Profile and password change.
6. Security log table filtered to failed logins.
7. Access denied, reached as `user@example.com` by opening `/users`.
8. Settings, showing the live policy and response headers.

A normal user's dashboard should show "Restricted" for the organization user count.

## Limitations

- The rate limiter is in-process. Multiple workers, or a restart, do not share counters.
- There is no MFA, password reset email, refresh-token family, or account recovery.
- `create_all` is not a migration tool.
- SQLite is unencrypted and local. The demo secret in source is for development only.
- Registration returns 422 for a weak password and 400 when the account cannot be created. That difference is a small enumeration hint, documented in SECURITY.md.
- The Vite dev server does not use the API's strict content security policy, because hot reload needs it.
- Interactive docs, if left on, describe the API to anyone who can reach the port.
- This repository is not a penetration test, and the presence of these controls is not a compliance claim.

## Future improvements

- MFA and a hashed refresh token with rotation.
- Redis (or the database) for a shared rate limit.
- Alembic migrations and a production static host with a locked content security policy.
- Security response headers on the built frontend, served behind HTTPS.
- Optional export of audit events to a log collector.
