# MeritForge

Minimal runbook for local development and testing.

Operational note: Redis-dependent middlewares default to fail-open; production should enable fail-closed via env vars (see repo/docker-compose.yml).

## Run (Docker)

From `repo`:

```bash
docker compose up --build
```

App URLs:

- Frontend: `https://localhost`
- API base: `https://localhost/api/v1`
- API docs: `https://localhost/docs`

Stop stack:

```bash
docker compose down
```

## Docker Commands

Start app:

```bash
docker compose up --build
```

Start app in background:

```bash
docker compose up -d --build
```

Show logs:

```bash
docker compose logs -f
```

Run all tests (backend + frontend):

```bash
docker compose --profile test up --build --abort-on-container-exit --exit-code-from test test
```

Run only API tests:

```bash
docker compose --profile test run --rm backend-test python -m pytest API_tests -q
```

Run frontend tests:

```bash
docker compose --profile test run --rm frontend-test npm run test:run
```

## Credentials

Default seeded password is controlled by `SEED_DEV_PASSWORD`.

- Default value: `MeritForgeDev!2026`

If you set a different value in `.env`, use that value for all seeded accounts.

## Seeded Accounts

Seed users:

```bash
docker compose exec backend python scripts/seed_dev_users.py
```

Accounts created by seed script:

| Email | Role |
|---|---|
| `student.meritforge@gmail.com` | Student |
| `employer.meritforge@gmail.com` | Employer manager |
| `author.meritforge@gmail.com` | Content author |
| `reviewer.meritforge@gmail.com` | Reviewer |
| `admin.meritforge@gmail.com` | System administrator |

All use the same password (`SEED_DEV_PASSWORD`).
