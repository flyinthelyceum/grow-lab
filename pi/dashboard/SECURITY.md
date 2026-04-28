# GROWLAB Dashboard Security (Stage 1)

This document describes the Stage 1 security baseline applied to the public dashboard at `grow.aaand.space`. It covers the threat model, what is protected, how to set and rotate the admin password, and operational notes.

## Threat model

The dashboard is a publicly reachable read-only telemetry surface for a single Raspberry Pi growing system. Stage 1 assumes:

- The threats are opportunistic scanners, drive-by actors, and casual abuse (rate-pegged probes, credential stuffing on any auth endpoint).
- The Pi is not a high-value target. There are no user accounts, no payments, no PII beyond visitor IPs the operator already sees in any reverse proxy log.
- Loss of confidentiality on sensor data is acceptable (the data is essentially public anyway). Loss of integrity (someone forcing the fan, irrigation pump, lights) is not acceptable.
- The Pi may be on a residential network behind a tunnel; HTTPS is terminated upstream, so cookies are issued with `secure=False` until that's confirmed.

Stage 1 does NOT defend against:

- A determined attacker who has the admin password.
- An attacker who has filesystem access to the Pi (game over: read `config.toml`, the SQLite DB, etc.).
- Sophisticated CSRF chains. The session cookie is `SameSite=Lax`, which blocks the easy cases. No CSRF tokens yet.

## What's protected

| Surface | Public | Admin only |
| --- | --- | --- |
| `/`, `/art`, `/dream` | yes | — |
| `GET /api/readings/*`, `/api/events`, `/api/images*`, `/api/alerts*`, `/api/system/status`, `/api/fan/status` | yes | — |
| `POST /api/fan/override` | — | yes (`require_admin` + admin rate limit) |
| `/admin/login`, `/admin/logout` | yes (form) | — |
| `/admin/visitors` | — | yes |
| WebSocket `/ws/*` | yes | — |

All routes are subject to the default rate limit (`security.rate_limit_default`, default `60/minute` per IP). Admin POST routes also obey `security.rate_limit_admin` (default `10/minute`).

## Setting the admin password

Secrets come from environment variables in production, with `config.toml` as a fallback for local dev. Env vars always win.

```bash
# 1. Generate a hex sha256 of your chosen password.
python -c "import hashlib, getpass; print(hashlib.sha256(getpass.getpass('pw: ').encode()).hexdigest())"

# 2. Generate a session key (32+ chars).
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 3. Drop both into /etc/growlab.env (or wherever your service reads from):
GROWLAB_ADMIN_PASSWORD_SHA256=<hex>
GROWLAB_SESSION_SECRET_KEY=<token>

# 4. Restart the service.
sudo systemctl restart growlab
```

## Rotating the password

1. Run step 1 above with the new password.
2. Replace `GROWLAB_ADMIN_PASSWORD_SHA256` in the env file.
3. Restart. All previously-logged-in sessions remain valid until the cookie expires; rotate `GROWLAB_SESSION_SECRET_KEY` simultaneously to invalidate every existing session.

## Hashing notes

- Passwords are hashed with `hashlib.sha256` (stdlib only). This is intentional: there are no per-user accounts and no realistic threat of an offline hash crack on a single hex digest behind a rate-limited endpoint. If that changes, swap in `argon2-cffi` or `bcrypt` and migrate.
- IP addresses and User-Agent strings in `access_log` are stored as the first 16 hex chars of `sha256(value)`. This is a privacy compromise: enough to count distinct visitors, not enough to reverse to a real IP.
- Password verification uses `secrets.compare_digest` for constant-time comparison.

## Disabling auth (dev only)

Set `GROWLAB_ADMIN_PASSWORD_SHA256=` (empty) or omit it entirely. The dashboard logs a WARN at startup and admin endpoints will refuse with a 503 from the login form (they cannot be authenticated, since no valid hash exists to compare against). Do NOT ship this state.

## Logs and aggregation

- The `access_log` table grows indefinitely. Plan: prune rows older than 90 days via cron, or VACUUM weekly. Not in Stage 1.
- `/static/*` and `/ws/*` are NOT logged (high-volume, low-signal).
- Query strings are dropped from the logged path to avoid leaking tokens that may appear in URL parameters.

## Future stages

- HTTPS enforcement and `secure=True` cookies once TLS is confirmed end-to-end.
- CSRF tokens on POST forms.
- IP allowlist for `/admin/*` in addition to the password.
- Switch the password hash to argon2 if user accounts ever multiply.
