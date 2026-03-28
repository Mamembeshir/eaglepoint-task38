# Business Logic Questions Log

**Project:** MeritForge Career Media & Hiring Platform  
**Date:** March 27, 2026  
**Author:** AI Developer (Grok)

## 1. Offline-First & Local-Only Architecture
**Question:** The prompt emphasizes "fully offline-ready" and "all data stored locally" with no internet required for core functionality. How should we handle user authentication and multi-device resume/continuation in a completely offline environment?

**Understanding/Hypothesis:** Since it's fully offline and local, we cannot rely on any external auth provider (Firebase, Supabase Auth, etc.). We need a local-first authentication system. "Resume where left off across devices" is challenging without sync. We assume this means the platform is designed for single-machine or intranet use (e.g., school/organization deployment), where "across devices" might be handled via local export/import or future local network sync (not implemented in v1).

**Solution:** 
- Implement local username + password authentication with JWT stored in HttpOnly cookies (local HTTPS).
- Progress, bookshelf, bookmarks, and annotations stored per user in PostgreSQL.
- For "across devices": Provide a "Export User Data" / "Import User Data" feature (JSON + encrypted backup) so students can manually transfer progress between devices. No real-time sync in this version.

## 2. Review Workflow for Content Submissions
**Question:** Content Authors submit articles, videos, and job announcements into a configurable review workflow with initial, secondary, and final review stages. Who can be assigned as reviewers? Can reviewers be from different roles? Is the workflow linear or can it be parallel? What happens if a reviewer rejects at any stage?

**Understanding/Hypothesis:** The prompt mentions "initial, secondary, and final review stages" and "at least two distinct reviewer approvals" for Medium risk content. It also mentions "one-click 'return for revision' action with required reason text (minimum 20 characters)".

**Solution:**
- Make the review stages configurable via admin settings (number of stages, required approvers per stage).
- Any user with "Reviewer" or "System Administrator" role can be assigned as reviewer.
- Workflow is sequential by default but supports parallel assignment for secondary review.
- Rejection at any stage sends back to author with mandatory reason (≥20 chars) and resets status to "Needs Revision".
- High-risk content is auto-blocked until final reviewer + admin approval.

## 3. Publishing Features (Scheduling, Canary, Takedown)
**Question:** Publishing supports scheduling, canary release (default 5% for 2 hours), immediate takedown with retraction notice, and traceable publishing record. How should "canary release to a configurable slice of users" be implemented in an offline/local environment?

**Understanding/Hypothesis:** True user slicing (e.g., by user ID hash or cohort) is complex for offline use. Since it's local/offline, we can simulate canary by user role or random percentage for demo purposes, but it should be deterministic and auditable.

**Solution:**
- Implement scheduled publishing using PostgreSQL + a background task queue (Celery or FastAPI BackgroundTasks + APScheduler).
- Canary release: Configurable percentage + duration. For simplicity in offline mode, use a "canary_group" flag or hash-based assignment (e.g., user_id % 100 < canary_percent). Visible only to canary users for the specified duration, then auto-promote or rollback.
- Takedown: Soft delete with visible "This content has been retracted" notice + full audit trail.
- All publishing actions logged with before/after state.

## 4. Student Progress Tracking & Milestones
**Question:** Students can track employment progress milestones (e.g., “resume approved” → “offer accepted”). Are these milestones predefined or fully configurable by employers/admins? How is progress updated (manual by student/employer or automated)?

**Understanding/Hypothesis:** The prompt gives examples but doesn't specify the full list or who controls them.

**Solution:**
- Predefined common milestones with ability for admins/employers to add custom ones per job posting.
- Progress updated manually by students (self-reported) and employers (verification).
- Status changes trigger notifications (in-app only, since offline).

## 5. Risk Assessment & Compliance Checks
**Question:** Submissions receive a risk grade (Low/Medium/High) based on administrator-managed local dictionary for sensitive-word and compliance checks. How sophisticated should the check be? Simple keyword match or more advanced (e.g., regex, context awareness)?

**Understanding/Hypothesis:** Since it's fully offline and local, we cannot use heavy ML models.

**Solution:**
- Simple but effective: Configurable dictionary of sensitive words/phrases + regex patterns managed by admin.
- Score-based system: count of matches + severity weights → Low/Medium/High.
- High = auto-block from publishing until final approval.
- Medium = requires minimum 2 distinct reviewer approvals.
- Log the specific triggering words for reviewers.

## 6. Annotations, Bookmarks & Privacy
**Question:** Highlights/annotations are private by default and optionally shareable to a "cohort". What is a "cohort" in this context? How is sharing implemented?

**Understanding/Hypothesis:** Cohort likely means a group (class, batch, department, or custom group created by admins).

**Solution:**
- Support user-created or admin-defined cohorts/groups.
- Annotations have visibility: Private / Share with specific cohort / Public (admin only).
- Default = Private.
- When shared, visible to cohort members on the same content item.

## 7. Data Storage & Audit Logs
**Question:** All data is stored locally in PostgreSQL. Audit logs must capture who did what and when (including IP, before/after values). In a Docker/local environment, how do we capture client IP reliably?

**Understanding/Hypothesis:** Since everything runs in Docker and accessed via local HTTPS, the "IP" will mostly be from the Docker network or host.

**Solution:**
- Use FastAPI middleware to capture `X-Forwarded-For` or real client IP.
- Store IP, user_id, timestamp, action, before/after JSON diff for sensitive changes.
- Retention: 365 days (configurable), with auto-cleanup job.

## 8. Open API & Webhook Capabilities
**Question:** "Open API and webhook capabilities are supported for on-prem/intranet integrations only". Should we implement full OpenAPI spec + actual webhook endpoints?

**Understanding/Hypothesis:** Since it's a complete runnable project, we should provide a proper OpenAPI (Swagger) interface and at least basic webhook support.

**Solution:**
- Auto-generated OpenAPI docs via FastAPI.
- Webhook system: Admin can configure webhook URLs (local/intranet only) with HMAC signing and idempotency keys.
- Async queue for webhook delivery with retry + dead-letter queue.

## 9. Technology Stack Confirmation
**Question:** The prompt specifies Vue.js frontend + FastAPI backend + PostgreSQL. Are there any other constraints or preferred libraries?

**Solution:**
- Frontend: Vue 3 + Vite + TypeScript + Pinia + Vue Router + Tailwind CSS (for modern UI).
- Backend: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL + Celery/BackgroundTasks + Pydantic v2.
- Containerization: Docker + docker-compose with multi-service setup (app, db, optional redis for queue).
- Local HTTPS: Self-signed certificates or mkcert for development.

---

**Additional Notes:**
- All core features will be implemented with real logic (no heavy mocking).
- Emphasis on auditability, role-based access control (RBAC), and offline functionality.
- Tests (unit + API) will be included as per delivery requirements.