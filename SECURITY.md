# Security notes and local testing

Vigil is a teaching application. The tests and the manual steps below are for this codebase on your own computer. Do not run them against a system you do not own or do not have permission to test.

Nothing here makes the project "fully OWASP compliant." The tables describe controls that exist in this repository and the gaps that remain.

## Threats this demo addresses

### SQL injection

User search is an SQLAlchemy `ilike` filter. The search string is bound as a parameter, and `%` and `_` are escaped so they are not wildcards. There is no query built by concatenating SQL. Automated coverage: `test_sql_injection_search_stays_a_bound_filter`.

### Cross-site scripting

Profile and directory values are rendered as React text nodes. The API responds with `application/json`. A display name may contain characters such as `<` so the UI can show them safely; control characters are rejected. Automated coverage: `test_xss_payload_is_json_data`. Confirm in the browser that a name containing `<script>alert(1)</script>` appears as text and does not run.

### Cross-site request forgery

Browser sessions use two cookies:

- `access_token` is HttpOnly, `SameSite=Lax`, and `Secure` when `COOKIE_SECURE=true`.
- `csrf_token` is readable by the console. `POST`, `PATCH`, and `DELETE` echo it in `X-CSRF-Token`.

The Vite proxy keeps the UI and the API on one origin during development. A request that sends `Authorization: Bearer` skips the CSRF check. That header is not attached automatically by a browser. Automated coverage: `test_cookie_session_requires_csrf`.

### Broken access control

- `user` can open the personal dashboard, profile, and settings.
- `user` receives 403 for `/api/users`, `/api/logs`, and role changes.
- `user` receives 404 when requesting another account by id, and the attempt is audited.
- `analyst` can read users and logs, and cannot change roles.
- `admin` can change another user's role and active flag, cannot change their own role, and cannot demote the last active administrator.
- The role that matters is the database role, not a role claim that the client can edit.

The React routes repeat these limits so the UI can show Access Denied. The API checks are the control.

### Authentication weaknesses

- Argon2id with a per-password salt. The hash is what the database stores.
- Access tokens expire (`ACCESS_TOKEN_MINUTES`) and include a `jti`. Logout sets `revoked_at`. Later use of that token fails even if the signature is still valid.
- Password changes revoke other sessions.
- Disabling an account revokes its sessions and makes login fail with the same message as a bad password.
- Unknown accounts still run a hash verification so the missing-user path is not a cheap early return.
- Registration ignores any attempt to set `role`. Unknown JSON fields are a 422.

There is no MFA and no breached-password service.

### Security misconfiguration

API responses set:

- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy` with camera, microphone, and geolocation disabled
- `Cache-Control: no-store`

`ENVIRONMENT=production` refuses a default or short `JWT_SECRET` and refuses `COOKIE_SECURE=false`. `ENABLE_DOCS=false` turns off `/docs`. `TRUST_PROXY` defaults to false so clients cannot spoof the audit IP by sending `X-Forwarded-For`.

The development server still uses a known sample secret if you do not set one. That is intentional for a local demo and unsafe to expose.

### Sensitive data exposure

Passwords are never returned. The login response body does not include the JWT. Audit logging refuses messages that contain `password`, `bearer `, or `eyJ`. Settings responses list policy values and header names, not the secret. SQLite itself is not encrypted.

### Brute-force login attempts

Failed logins are counted per client IP and per email. The defaults are 5 failures in 900 seconds, then HTTP 429. A successful login clears the per-email counter. Registration has a separate per-IP counter.

This limiter is stored in the API process. It is not a cluster-wide control, and it resets on restart.

### Insecure input validation

Pydantic checks email shape, name length, password length, and role literals. Names cannot contain ASCII control characters. Passwords need mixed case, a digit, a symbol, and no spaces, and they cannot equal the email. The UI repeats the password rules; the API is the authority.

### Information leakage

Wrong password, unknown email, and disabled account all return `Invalid email or password`. Unhandled server errors return `Internal server error` and the traceback stays in the server log. Validation errors list the field and a short message, not a stack trace.

A remaining hint: a weak password is 422, while a duplicate email is a generic 400. An observer who already has a strong password can tell those cases apart.

## Automated tests

From `backend`, with the virtual environment activated and dependencies installed:

```powershell
..\.venv\Scripts\python.exe -m pytest
```

The tests use an in-memory SQLite database and do not seed the demo accounts. They cover:

| Test module | What it checks |
| --- | --- |
| `test_auth.py` | Registration, login, `/api/auth/me`, identical failure text, weak passwords, rejected `role`, Argon2, logout revocation, duplicate registration, password change, audit redaction |
| `test_rbac.py` | User 403s, audited denials, cross-account 404, analyst read-only access, admin role rules |
| `test_security.py` | Security headers, search injection string, JSON encoding of a script-like name, tampered JWT, expired JWT, login rate limit, CSRF, validation leakage, production secret check |

## Manual checks

Start the API and the Vite app using the commands in the README. Use the seeded accounts.

1. Sign in as `user@example.com`. Confirm the dashboard hides the organization user total. Open `http://127.0.0.1:5173/users` and confirm Access Denied. In the browser network panel, `GET /api/users` is 403.
2. Sign in as `analyst@example.com`. Open Users and Security logs. Confirm the role control is not a dropdown.
3. Sign in as `admin@example.com`. Change the analyst to `user` and back. Confirm the security log records a role change and does not contain a password or a token.
4. From a private window, submit five bad passwords for one email, then a sixth. The sixth response is 429.
5. Register a display name of `Sam <script>alert(1)</script>`. The users table shows the text. The browser does not show an alert.
6. In the browser devtools, try `fetch('/api/auth/logout', {method:'POST', credentials:'include'})` while signed in. It should fail CSRF. The in-app Logout button should succeed.

## Logging rules

Recorded events: successful login, failed login, logout, registration, password change, role change, account enable/disable, unauthorized access, and rate limiting.

Never log passwords, JWTs, cookie values, or the `Authorization` header. The helper replaces a message that looks like it contains those values.
