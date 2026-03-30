# MeritForge Career Media & Hiring Platform

A comprehensive career media and hiring platform designed for offline/intranet-first deployment.

## Architecture Overview

### Offline/Intranet-First Design

MeritForge is designed to run entirely within a local network without requiring internet connectivity:

- **Self-contained services**: All dependencies (database, cache, backend, frontend) run in Docker containers
- **No external API calls**: The platform operates independently of third-party services
- **Local file storage**: All uploads and media are stored within Docker volumes
- **Offline-ready frontend**: Vue SPA with local state management

### Multi-Device Usage

Multiple users can access the platform simultaneously from different devices:

- All devices connect to the same local server via the host machine's IP address
- Example: `https://192.168.1.100` (frontend + API through nginx)
- Shared database ensures real-time data consistency across all connected devices

MeritForge is currently single-tenant. Data isolation is enforced by authenticated user identity, role checks, and resource ownership (for example employer-owned job resources and self-scoped student progress/profile routes), not by a SaaS multi-tenant `tenant_id` model.

### Container Services

| Service | Published Port | Purpose |
|---------|----------------|---------|
| `nginx` | 443 | HTTPS entrypoint and reverse proxy |
| `frontend` | internal-only | Vue SPA app container |
| `backend` | internal-only | FastAPI REST API |
| `db` | internal-only* | PostgreSQL database |
| `redis` | internal-only* | Celery broker/cache |

\* Expose DB/Redis for local debugging tools with `--profile dev-tools`.

```bash
docker compose --profile dev-tools up --build
```

## How to Run

Run commands from `repo/meritforge` (relative to the TASK root).

Prerequisite: Docker Desktop (or Docker Engine + Compose plugin).

Start application (build included):

```bash
docker compose up --build
```

Dev TLS behavior:

- On first run, the stack auto-generates development self-signed certs in `nginx/ssl/` if `cert.pem`/`key.pem` are missing.
- For production, replace these files with trusted CA-issued certificates.

Demo / seeded accounts (development only):

```bash
docker compose exec backend python scripts/seed_dev_users.py
```

| Email | Role | Password |
|---|---|---|
| `student.meritforge@gmail.com` | Student | value of `SEED_DEV_PASSWORD` (default `MeritForgeDev!2026`) |
| `employer.meritforge@gmail.com` | Employer manager | value of `SEED_DEV_PASSWORD` (default `MeritForgeDev!2026`) |
| `author.meritforge@gmail.com` | Content author | value of `SEED_DEV_PASSWORD` (default `MeritForgeDev!2026`) |
| `reviewer.meritforge@gmail.com` | Reviewer | value of `SEED_DEV_PASSWORD` (default `MeritForgeDev!2026`) |
| `admin.meritforge@gmail.com` | System administrator | value of `SEED_DEV_PASSWORD` (default `MeritForgeDev!2026`) |

Development-only warning: do not use shared default credentials in staging/production; rotate immediately if exposed.

Role verification checklist:

- `student.meritforge@gmail.com` -> student workspace (videos/bookmarks)
- `employer.meritforge@gmail.com` -> hiring workspace (jobs/applications)
- `author.meritforge@gmail.com` -> content submission flows
- `reviewer.meritforge@gmail.com` -> review queue/workflow
- `admin.meritforge@gmail.com` -> admin + operations + audit views

Run tests:

```bash
docker compose --profile test run --rm test sh -c \
"python -m unittest discover -s unit_tests -p 'test_*.py' -v && \
 python -m unittest discover -s API_tests -p 'test_*.py' -v"
```

Run tests with coverage:

```bash
docker compose --profile test run --rm test
```

`--profile test` is required because the `test` service is defined under the optional `test` Compose profile.

Frontend automated tests (Vitest + Vue Test Utils):

```bash
cd frontend
npm run test:run
```

Service Address:

- Frontend: https://localhost
- Backend API: https://localhost/api
- API Docs: https://localhost/docs
- If startup fails on nginx TLS checks, ensure `nginx/ssl/` is writable so cert generation can create `cert.pem` and `key.pem`.

Verification Method:

- Open frontend in browser
- Perform login/register
- Access API via Swagger or endpoints
- Run basic tests using the `Run tests` command and confirm both suites pass
- Run coverage tests using the `Run tests with coverage` command and confirm coverage summary is printed

Expected result:

- All services start successfully
- Both unit_tests and API_tests execute
- Clear pass/fail output
- Both test commands exit non-zero if any test fails

Data retention behavior:

- Hard deletion of users marked past the retention window runs automatically via a daily Celery beat job.
- The admin endpoint (`POST /api/v1/users/deletion/process-due`) remains available for explicit/manual processing by system administrators.

Coverage output:

- The `test` service command runs both `unit_tests` and `API_tests` through `coverage run`.
- A terminal summary is printed with per-file line coverage and total percentage.
- Example output snippet:

```text
Name                              Stmts   Miss Branch BrPart   Cover
--------------------------------------------------------------------
app/core/security.py                74      6     18      3  89.13%
app/api/v1/review_workflow.py      170     29     44      8  79.82%
--------------------------------------------------------------------
TOTAL                               912    158    210     41  81.76%
```

- HTML report is generated at `coverage_html/index.html` on the host.
- Open it in a browser to inspect uncovered lines.
- You can use the total percentage as a quality gate target in CI.

Security controls note:

- Passwords are stored as salted hashes with optional pepper.
- Refresh tokens are stored as keyed hashes (HMAC/legacy hash fallback), not raw values.
- Step-up confirmation uses `POST /api/v1/auth/step-up` with password in JSON body and a short-lived httpOnly cookie proof for sensitive actions.
- If your reverse proxy or ingress can log request bodies, disable full-body logging for auth and step-up routes to avoid capturing passwords.
- Annotations support `private`, `cohort`, and `public` visibility. `public` annotations are visible to all authenticated users and should only be used for intentionally shared notes.
- These controls protect secrets in the application database layer; they are not filesystem/disk encryption at the OS level.

Operations / middleware resilience:

- Rate limiting and idempotency middleware currently run in fail-open mode when Redis is unavailable (requests continue and a warning is logged).
- During Redis outages, abuse protection can degrade and duplicate writes can slip through despite `Idempotency-Key` usage.
- Monitor Redis health and alert on middleware warnings like `rate_limit_redis_unavailable_fail_open` and `idempotency_redis_*_unavailable_fail_open`.
- If your deployment requires stricter posture, plan a future fail-closed toggle (for example, env-driven `*_FAIL_CLOSED`) so write traffic can be blocked or degraded explicitly during Redis failure windows.

On-prem / integration (HMAC):

- Integration requests require `X-MeritForge-Key-Id`, `X-MeritForge-Timestamp`, and `X-MeritForge-Signature` headers.
- Configure key pairs in `INTEGRATION_HMAC_KEYS` as `key_id:secret` entries (comma-separated for rotation).
- Available HMAC routes include `POST /api/v1/integration/echo` and `GET /api/v1/integration/published-content`.
- Signature format is `<timestamp>.<canonical_json_body>`, where JSON is serialized with sorted keys and compact separators.

Idempotency caveat:

- Without an access cookie, idempotency keys are scoped by client IP (`ip:<address>`), so users behind shared NAT/proxy can collide on the same `Idempotency-Key`.
- Prefer authenticated requests for mutating endpoints and always send a unique `Idempotency-Key` per logical operation.
- If you rely on client IP identity, only trust forwarded IP headers behind controlled reverse proxies and explicit trust boundaries.

## Local HTTPS Setup (Optional Override)

Use this only if you want to replace the auto-generated development certs with mkcert-generated certs.

### Using mkcert (Recommended)

1. Install mkcert on the host machine:
   ```bash
   # macOS
   brew install mkcert nss
   mkcert -install
   ```

2. Generate certificates in the default path `nginx/ssl/`:
   ```bash
   cd meritforge/nginx/ssl
   mkcert localhost 127.0.0.1 ::1
   mv localhost+2-key.pem key.pem
   mv localhost+2.pem cert.pem
   ```

3. For network access, include your machine's IP:
   ```bash
   mkcert localhost 127.0.0.1 192.168.1.100
   ```

4. Restart nginx:
   ```bash
   docker compose restart nginx
   ```

Access via HTTPS: `https://localhost`

## Development

### Prerequisites

- Docker Desktop or Docker Engine with docker-compose
- (Optional) mkcert for local HTTPS

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Set `CORS_ORIGINS` as a comma-separated list for allowed browser origins (example: `https://localhost,http://localhost:3000` for nginx HTTPS + Vite dev).
For local verbose error output, set `DEBUG=true` explicitly in `.env` (default compose behavior is `DEBUG=false`).
Set `VITE_API_URL` to empty for Docker/nginx same-origin (`/api/v1/...` paths). For standalone local Vite dev without nginx, set `VITE_API_URL=http://localhost:8000`.
`REFRESH_TOKEN_HASH_ROTATION_DAYS` is an operational policy window; rotate `REFRESH_TOKEN_HASH_ACTIVE_KEY_ID` and keep prior keys in `REFRESH_TOKEN_HASH_KEYS` manually on that cadence.
Set `ALLOW_REGISTRATION=false` to disable self-registration (`POST /api/v1/auth/register` returns `403`).

### Running Services

```bash
# Start all services
docker compose up
```

### Optional: run backend without Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export PYTHONPATH=backend
export DATABASE_URL=postgresql://meritforge:meritforge@localhost:5432/meritforge
export REDIS_URL=redis://localhost:6379/0
alembic -c backend/alembic.ini upgrade head
uvicorn app.main:app --app-dir backend --reload
```

Use this only when local Postgres/Redis are already running and configured.

### Database Migrations

```bash
# Create migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec backend alembic upgrade head

# Rollback
docker compose exec backend alembic downgrade -1
```

## Project Structure

```
meritforge/
├── docker-compose.yml      # Service orchestration
├── .env.example            # Environment template
├── README.md               # This file
├── backend/
│   ├── Dockerfile          # Backend container
│   ├── requirements.txt    # Python dependencies
│   ├── app/
│   │   ├── main.py         # FastAPI entry point
│   │   └── __init__.py
│   └── alembic/            # Database migrations
├── frontend/
│   ├── Dockerfile          # Frontend container
│   ├── package.json        # Node dependencies
│   ├── vite.config.ts      # Vite configuration
│   └── src/
│       ├── main.ts         # Vue entry point
│       └── App.vue
└── nginx/
    ├── nginx.conf          # Reverse proxy config
    └── ssl/                # SSL certificates
```

## Production Considerations

When deploying to production:

1. Change default passwords in `.env`
2. Use strong `SECRET_KEY`
3. Set `DEBUG=false`
4. Configure proper SSL certificates
5. Set up regular database backups
6. Configure log aggregation

## License

Proprietary - All rights reserved.
