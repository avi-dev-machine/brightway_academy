# Brightway Computer Academy — Backend

FastAPI + Supabase (PostgreSQL, Auth, Storage) backend for students, courses, batches,
fees, Razorpay payments, receipts, attendance, notifications, ID cards, reports and the
legacy CSV migration. The full specification is in [`../backend.md`](../backend.md).

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync                                   # creates .venv with app + dev dependencies
cp .env.example .env                      # then fill in the values (never commit .env)
uv run python -m app.db.migrate up        # apply database migrations
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs
uv run python -m app.workers.scheduler    # background jobs (separate process)
```

## Commands

| Task | Command |
| --- | --- |
| Run all tests | `uv run pytest -q` |
| Lint / format check | `uv run ruff check .` · `uv run ruff format --check .` |
| Type check | `uv run mypy app` |
| Migration status / apply | `uv run python -m app.db.migrate status` · `... up` |
| First admin | `uv run python -m scripts.seed_admin --email owner@example.com` |
| Legacy CSV import (CLI) | `uv run python -m scripts.import_initial_csv students.csv --admin-email owner@example.com [--confirm]` |
| Probe a running server | `uv run python -m scripts.health_check --url http://localhost:8000` |
| Live Razorpay test-mode check | `RUN_LIVE_TESTS=1 uv run pytest tests/payments -k live` |

Tests start a throwaway local PostgreSQL automatically (`pgserver`); nothing touches
Supabase. To use another server set `TEST_DATABASE_URL` (its database name must contain
`test` — tests truncate every table).

## Configuration

All configuration is environment variables (see [`.env.example`](.env.example)).
Integrations that are not configured never block unrelated features:

| Feature | Needs | Without it |
| --- | --- | --- |
| Database | `DATABASE_URL` | required |
| Auth | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` | required (tokens verified via JWKS) |
| File storage | `SUPABASE_SERVICE_ROLE_KEY` | files saved to `LOCAL_STORAGE_DIR` (dev only) |
| User invites | `SUPABASE_SERVICE_ROLE_KEY` | create users in the dashboard, then link them |
| Online payments | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | mock provider (dev only) |
| Payment webhooks | `RAZORPAY_WEBHOOK_SECRET` | webhook endpoint answers 503 |
| WhatsApp (Meta) | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` (+ `WHATSAPP_APP_SECRET`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN` for status webhooks) | messages are only logged (dev only) |
| WhatsApp (Fast2SMS) | `WHATSAPP_PROVIDER=fast2sms`, `WHATSAPP_ACCESS_TOKEN` (Fast2SMS key), `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEMPLATE_FEE_REMINDER`, `WHATSAPP_TEMPLATE_PAYMENT_SUCCESS` (message ids) | messages are only logged (dev only) |
| SMS | `SMS_PROVIDER=fast2sms`, `SMS_PROVIDER_API_KEY` | messages are only logged (dev only) |

`APP_ENV=production` refuses to start with unsafe settings (mock payments, local storage,
missing webhook secret, wildcard CORS, non-HTTPS base URL).

**Database URL:** Supabase's direct host (`db.<ref>.supabase.co`) is IPv6-only. Hosts
without IPv6 must use the Supavisor pooler URL from *Project Settings → Database*. The
scheduler needs a session connection (direct or session pooler, port 5432) for its
advisory lock. URL-encode special characters in the password (`@` → `%40`).

## Architecture

```text
app/api/v1/*        thin routes: auth, role check, call one service method, envelope
app/services/*      business logic and transactions
app/repositories/*  SQL (psycopg 3, bound parameters only)
app/integrations/*  Razorpay, WhatsApp Cloud API, Fast2SMS, Supabase Storage/Auth adapters
app/workers/*       scheduler, fee reminders, notification delivery
app/db/migrations   numbered SQL migrations (checksum-verified runner: app/db/migrate.py)
```

* **Auth** — the frontend signs in with Supabase Auth and sends `Authorization: Bearer
  <access token>`. The backend verifies the ES256 signature against the project's JWKS
  and loads the role (ADMIN / TEACHER / STUDENT) from `user_profiles`. Roles are never read
  from user-editable token metadata.
* **Data access** — only this backend touches the database. Every table has RLS enabled
  with no policies and `anon`/`authenticated` privileges revoked, so the publishable key
  cannot read data through the Supabase Data API. Storage buckets are private; files are
  streamed through authorised endpoints.
* **Responses** — `{"success": true, "data": ..., "meta": {...}}` or
  `{"success": false, "error": {"code", "message", "request_id", "details"}}`.
  Money is integer **paise** everywhere (`amount_paise`).
* **Data preservation** — students are deactivated, never deleted; database triggers
  block deletes of students, fees, payments and receipts, and make the audit log
  append-only.

## First-run setup

1. Apply migrations; create the owner in Supabase (*Authentication → Add user*), then
   `python -m scripts.seed_admin --email <owner email>`.
2. `PUT /api/v1/admin/settings/academy` — name, address, phone, ID/receipt prefixes.
3. `POST /api/v1/courses` for each course (CSV course names are matched to course
   names or codes, ignoring case and punctuation).
4. `POST /api/v1/imports/students/preview` with the legacy CSV (columns `ID No.`,
   `Name`, `Guardian's Name`, `Address`, `Contact No.`, `Course`). Review the summary and
   `GET /api/v1/imports/{id}/rows`. Nothing is imported yet.
5. `POST /api/v1/imports/{id}/confirm` — `error_policy` `STRICT` (default) or
   `SKIP_ERRORS`; `course_mapping` / `create_missing_courses` for unknown courses.
   Re-running an import is safe: existing ID numbers are reported and never overwritten.
6. Review the ID-card template (`/api/v1/id-cards/templates`), fee plans
   (`/api/v1/fees/plans`) and notification settings, then `POST /api/v1/admin/setup/complete`.
   `GET /api/v1/admin/setup` shows the checklist at any time.

## Payments (Razorpay)

1. Frontend: `POST /api/v1/payments/orders {fee_id}` (optional `Idempotency-Key`
   header). The amount comes from the fee balance on the server.
2. Open Razorpay Checkout with the returned `key_id` and `provider_order_id`.
3. On success send the handler's ids and signature to `POST /api/v1/payments/verify`.
   The backend checks the signature **and** fetches the payment from Razorpay before
   marking it paid.
4. Configure a Razorpay webhook to `https://<api>/api/v1/payments/webhooks/razorpay`
   for `payment.captured`, `payment.failed`, `payment.authorized`, `order.paid` and
   `refund.processed`, and put its secret in `RAZORPAY_WEBHOOK_SECRET`.

Settlement is idempotent (row lock + unique provider ids + one receipt per payment), so
duplicate webhooks and repeated verifications are safe. A wrong amount or a mismatched
order is never applied; it is flagged with `requires_review`. Offline (cash/UPI/cheque)
payments use `POST /api/v1/fees/{fee_id}/offline-payments`.

## Notifications

Fee reminders and payment confirmations are queued in `notifications` and delivered by
the scheduler (never inside API requests), with retries and exponential backoff.
Reminders are sent at `reminder_offsets_days` relative to the due date (default
-3, 0, +3, +7) and deduplicated on student + fee + stage + date; paid or cancelled fees
stop receiving reminders. WhatsApp uses approved **template** messages for
`fee_reminder` (variables in order: name, fee title, amount, due date) and
`payment_success` (name, amount, fee title, receipt number). With Meta, name the templates
accordingly (or set `WHATSAPP_TEMPLATE_*`); with Fast2SMS, put each template's
`message_id` in `WHATSAPP_TEMPLATE_*`. `GET /api/v1/admin/system/status` shows which
provider each channel really uses (`log-*` means messages are only logged).

**Fast2SMS setup:** in the Fast2SMS panel's *Dev API* section allow the server's public IP
(requests from other IPs are refused with "IP is blacklisted"), connect the WhatsApp
Business number to get its `phone_number_id`, and create the two templates. SMS is sent
on the Quick route (`q`, no DLT template); for DLT-registered production SMS, a sender id
and template ids will be needed.

## Deployment

```bash
docker build -t brightway-backend backend
docker run --env-file backend/.env -p 8000:8000 brightway-backend
docker run --env-file backend/.env brightway-backend python -m app.workers.scheduler
```

Run the API behind HTTPS with `FORWARDED_ALLOW_IPS` set to the proxy address. Rate
limits are per process; use one API process per container or move limits to the proxy.
