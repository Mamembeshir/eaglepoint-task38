# MeritForge — API specification

**Version:** 1.0  
**Last updated:** March 28, 2026  
**Related:** [Design document](./design.md) · [Product prompt](../metadata.json) (`prompt` field)

This document describes the **MeritForge** HTTP API as implemented in the FastAPI backend. It is the human-readable companion to the machine-readable **OpenAPI** schema served at runtime.

---

## 1. Base URL, versioning, and discovery

| Item | Value |
|------|--------|
| API prefix | `/api/v1` |
| Interactive docs | `/docs` (Swagger UI) |
| Alternative docs | `/redoc` |
| Health | `GET /health` (no version prefix) |
| Root | `GET /` |

Behind the shipped **nginx** reverse proxy, the API is typically reached at **`https://<host>/api/...`** (see `repo/meritforge/README.md`).

**Source of truth for schemas:** Run the stack and inspect OpenAPI at `/openapi.json`, or browse `/docs`. This file summarizes routes and policies; field-level types belong in the generated spec and Pydantic models under `app/schemas/`.

---

## 2. Authentication

### 2.1 Mechanism

- **JWT access** and **refresh** tokens are issued on login/register and returned in the JSON body **and** set as **HttpOnly** cookies (`access_token`, `refresh_token` by default; names configurable via env).
- Authenticated requests rely on the **access** cookie unless clients attach the same token another way the app accepts (the primary consumer is the Vue SPA with `credentials: "include"`).
- Refresh token cookie path is scoped to **`/api/v1/auth`** for the refresh flow.

### 2.2 Auth routes

All paths below are under **`/api/v1/auth`**.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/register` | Create account; sets cookies |
| `POST` | `/login` | Issue tokens; sets cookies |
| `POST` | `/refresh` | Rotate access token using refresh cookie/body |
| `POST` | `/logout` | Invalidate refresh session; clears cookies |

### 2.3 Role checks

Protected routes use **`get_current_user`** and **`require_roles(...)`** with `RoleType` values (e.g. student, employer, author, reviewer, system administrator). A **`403`** indicates an authenticated user whose role is not allowed for that operation.

---

## 3. Step-up confirmation

High-risk actions require the caller to prove knowledge of the account password again via a header (default name configurable; default **`X-Step-Up-Password`**).

**Used for (non-exhaustive):**

- **Content takedown** (`POST /api/v1/publishing/content/{content_id}/takedown`)
- **Cohort membership mutations** that change permissions visibility (add/remove user in cohort)
- **Marking account for deletion**

If the header is missing or the password does not match the user’s hash, the API returns **`403`** with an explicit step-up message.

---

## 4. Rate limiting

- **Global middleware** applies to incoming requests.
- Limit is **per minute**, keyed by **`user:{user_id}`** when a valid access cookie is present, otherwise by **client IP**.
- Default cap: **120 requests/minute** (`USER_RATE_LIMIT_PER_MINUTE`).
- Violations return **`429`** with JSON `detail`, `limit`, and `window`.

Redis is required for counters in the default configuration.

---

## 5. Idempotency

For **`POST`** and **`PUT`**, clients may send:

```http
Idempotency-Key: <opaque string>
```

Behavior (Redis-backed):

- Same key + **same** method, path, query, and body → **replays stored response** (safe retries).
- Same key with **different** payload → **`409`** (`Idempotency key reuse with different payload`).
- Keys are scoped per **user id** (from access token) or per **IP** if unauthenticated.

Omitting the header skips idempotency handling (normal processing).

---

## 6. Integration API (HMAC)

Server-to-server style calls use **HMAC-SHA256** over a canonical string. Configure keys via **`INTEGRATION_HMAC_KEYS`** (`key_id:secret` pairs, comma-separated).

### 6.1 Headers

| Header | Env override | Purpose |
|--------|----------------|---------|
| `X-MeritForge-Timestamp` | `INTEGRATION_HMAC_TIMESTAMP_HEADER` | ISO-8601 timestamp (UTC) |
| `X-MeritForge-Signature` | `INTEGRATION_HMAC_SIGNATURE_HEADER` | Hex-encoded HMAC-SHA256 |
| `X-MeritForge-Key-Id` | `INTEGRATION_HMAC_KEY_ID_HEADER` | Key id (optional if exactly one key configured) |

### 6.2 String to sign

```
<string_to_sign> = "<timestamp>" + "." + <canonical_json_body>
```

Where `<canonical_json_body>` is `json.dumps(body, separators=(",", ":"), sort_keys=True)` (UTF-8). For an empty body, the parsed payload is `{}`.

### 6.3 Clock skew

Rejected if timestamp differs from server UTC by more than **`INTEGRATION_HMAC_CLOCK_SKEW_SECONDS`** (default **300**).

### 6.4 Endpoint

| Method | Path | Auth |
|--------|------|------|
| `POST` | `/api/v1/integration/echo` | HMAC only (no session cookie required) |

Response echoes the resolved `key_id` and payload for connectivity testing.

---

## 7. Resource API (by area)

Unless noted, routes expect a **logged-in** user with an appropriate **role**. Paths are relative to **`/api/v1`**.

### 7.1 Bookmarks

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/bookmarks` | List |
| `POST` | `/bookmarks` | Create |
| `DELETE` | `/bookmarks/{content_id}` | Remove |

### 7.2 Topic subscriptions

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/users/me/topic-subscriptions` | List |
| `POST` | `/users/me/topic-subscriptions` | Subscribe |
| `DELETE` | `/users/me/topic-subscriptions` | Unsubscribe; required query param **`topic`** |

### 7.3 Content catalog and submission

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/content` | Catalog / browse |
| `POST` | `/content/submissions` | Author submission |
| `GET` | `/content/submissions/mine` | Author’s submissions |

### 7.4 Review workflow

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/review-workflow/queue` | Reviewer queue |
| `POST` | `/review-workflow/templates/stages` | Configure template stages |
| `GET` | `/review-workflow/templates/stages` | List stages |
| `POST` | `/review-workflow/contents/{content_id}/initialize` | Start workflow for content |
| `POST` | `/review-workflow/stages/{stage_id}/decisions` | Submit approve/reject/revision |

### 7.5 Publishing

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/publishing/content/{content_id}/schedule` | Schedule / publish actions per body |
| `POST` | `/publishing/content/{content_id}/takedown` | **Step-up** required |
| `GET` | `/publishing/content/{content_id}/visibility/{user_id}` | Canary / visibility evaluation |
| `GET` | `/publishing/content/{content_id}/history` | Publishing history |

### 7.6 Engagement, progress, milestones, annotations

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/telemetry/events` | Play/skip/favorite/search style events |
| `GET` | `/telemetry/progress` | Playback progress |
| `POST` | `/milestone-templates` | Template CRUD context |
| `POST` | `/students/{student_id}/milestones/manual` | Manual milestone |
| `PATCH` | `/students/{student_id}/milestones/{milestone_id}` | Update |
| `GET` | `/students/{student_id}/milestones` | List |
| `POST` | `/annotations` | Create annotation |
| `GET` | `/contents/{content_id}/annotations` | List for content |
| `PATCH` | `/annotations/{annotation_id}` | Update |

### 7.7 User management, cohorts, privacy

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/users/me` | Profile |
| `PATCH` | `/users/me` | Update profile |
| `GET` | `/users/{user_id}` | Profile by id (authorized) |
| `POST` | `/users/me/import` | Import user data backup |
| `GET` | `/users/me/export` | Export payload |
| `POST` | `/users/me/deletion/mark` | **Step-up**; schedule deletion |
| `POST` | `/users/deletion/process-due` | Admin/system processing of due deletions |
| `POST` | `/cohorts` | Create cohort |
| `POST` | `/cohorts/{cohort_id}/users/{user_id}` | Add member (**step-up** where enforced) |
| `DELETE` | `/cohorts/{cohort_id}/users/{user_id}` | Remove member (**step-up** where enforced) |

### 7.8 Employer jobs and applications

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/employer/job-posts` | Create job |
| `GET` | `/employer/job-posts` | List |
| `PATCH` | `/employer/job-posts/{job_post_id}` | Update |
| `GET` | `/employer/job-posts/{job_post_id}/applications` | Applications |
| `PATCH` | `/employer/applications/{application_id}/status` | Status update |
| `POST` | `/employer/job-posts/{job_post_id}/milestone-templates` | Templates per job |
| `POST` | `/student/applications/{application_id}/milestones` | Student milestone |
| `PATCH` | `/employer/milestones/{milestone_id}/verify` | Employer verification |
| `GET` | `/employer/job-posts/{job_post_id}/milestones` | List milestones |

### 7.9 Admin

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/admin/risk-dictionary` | List dictionary entries |
| `POST` | `/admin/risk-dictionary` | Create |
| `PATCH` | `/admin/risk-dictionary/{risk_id}` | Update |
| `DELETE` | `/admin/risk-dictionary/{risk_id}` | Delete |
| `GET` | `/admin/cohorts` | Cohorts with members |

### 7.10 Audit logs

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/audit-logs` | Searchable list; **admin** role; query filters: `user_id`, `user_email`, `action`, `entity_type`, `ip_address`, `q`, `start_at`, `end_at`, `limit`, `offset` |

### 7.11 Operations dashboard

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/operations/metrics` | Dashboard aggregates |
| `GET` | `/operations/metrics/export.csv` | CSV export (permission-controlled) |

### 7.12 Webhooks (configuration and operations)

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/webhooks/configs` | **Admin**; URL must pass **intranet** check |
| `GET` | `/webhooks/configs` | **Admin** |
| `POST` | `/webhooks/dispatch` | **Admin**; queue deliveries for matching configs |
| `GET` | `/webhooks/deliveries` | **Admin** |
| `POST` | `/webhooks/deliveries/{delivery_id}/retry` | **Admin** |

**Webhook URL policy:** Only **localhost**, **private IPs**, **link-local**, certain **single-label** hosts, and hosts ending in **`.local` / `.internal` / `.lan`** are accepted for configs. Public internet URLs are rejected with **`422`**.

**Outbound signature:** Same canonicalization as integration: `HMAC-SHA256(secret, "<timestamp>.<canonical_json>")` hex digest. Deliveries use **Celery** (or configured worker) for async send, retries, and dead-letter storage.

**Dedup:** Internal idempotency key derived from config id, event name, and canonical payload hash to avoid duplicate deliveries.

---

## 8. CORS and cookies

- **CORS** allows configured origins (`CORS_ORIGINS`) with **`allow_credentials=True`** so the browser may send cookies.
- Cookies use **`Secure`** when `SECURE_COOKIES=true` (typical behind HTTPS).

---

## 9. Error shape

FastAPI returns JSON error bodies such as:

```json
{ "detail": "Human-readable message" }
```

Validation errors may return a **`detail`** array of objects (standard FastAPI / Pydantic). Clients should branch on **HTTP status** (`401`, `403`, `404`, `409`, `422`, `429`, etc.) first.

---

## 10. Traceability

| Concern | Location in repo |
|---------|------------------|
| Route registration | `backend/app/api/v1/__init__.py` |
| Middleware order | `backend/app/main.py` |
| Auth & step-up | `backend/app/dependencies/auth.py` |
| Integration HMAC | `backend/app/dependencies/integration.py` |
| Webhook signing & URL rules | `backend/app/services/webhook_service.py` |
| Schemas | `backend/app/schemas/` |

---

## 11. Revision history

| Version | Date | Notes |
|---------|------|--------|
| 1.0 | 2026-03-28 | Full spec from implemented routers and middleware |
