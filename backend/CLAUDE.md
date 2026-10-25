# Brightway backend — working notes for Claude Code

Spec: `../backend.md` (source of truth for requirements). Human docs: `README.md`.

## Commands (run from `backend/`)

```bash
uv run pytest -q                      # full suite; starts a throwaway local Postgres (pgserver)
uv run pytest tests/payments -q       # smallest relevant subset after a change
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run python -m app.db.migrate status|up
uv run uvicorn app.main:app --reload
RUN_LIVE_TESTS=1 uv run pytest tests/payments -k live   # real Razorpay *test* mode
```

All four gates (pytest, ruff check, ruff format --check, mypy) must pass before a change
is declared done.

## Architecture rules

- Layering: `api/v1` (thin, sync `def` routes) → `services` → `repositories` → Postgres.
  Integrations (`app/integrations`) are only called from services.
- Services are built by factory functions in `app/dependencies.py` from a `Container`
  (settings, db, token verifier, storage, payment provider, notification providers).
  Tests build their own `Container` (see `tests/conftest.py`).
- One `with db.transaction() as conn:` per unit of work; it commits on success and rolls
  back on any exception. Audit rows (`record_audit`) are written in the same transaction.
- Never hold a DB transaction open across an external HTTP call (see
  `PaymentService.create_order`).
- Payment settlement always goes through `PaymentService._record_success` with the
  payment row locked `FOR UPDATE` (lock order: payment → fee).
- Errors: raise `app.exceptions.*` (each has a stable `code`); handlers in
  `app/core/errors.py` render the envelope. Never return raw exceptions/tracebacks.
- Repository/service methods are named `search(...)`, not `list(...)` (a method named
  `list` shadows the builtin in annotations).

## Database conventions

- New schema changes = new file `app/db/migrations/NNNN_name.sql`. Never edit an applied
  migration (the runner verifies checksums). Every new table: UUID PK, `created_at`,
  `updated_at` + `set_updated_at` trigger, RLS enabled (no policies), named constraints.
- Money is integer paise (`*_paise`). Business dates use `TIMEZONE` (Asia/Kolkata) via
  `app.utils.dates.local_today`; don't rely on the database's time-zone data.
- Students/fees/payments/receipts cannot be deleted (triggers); `audit_logs` is append-only.
- `students.id_no` is unique case-insensitively (`students_id_no_lower_key`); legacy
  values are stored exactly as imported.
- Map constraint names to domain errors with `translate_constraint_errors`.

## Security decisions

- Tokens: Supabase ES256 JWTs verified via JWKS; only asymmetric algorithms accepted.
  Role/ownership come from `user_profiles`, never from JWT metadata.
- Ownership checks live in `app/core/permissions.py` (`ensure_student_access`,
  `ensure_batch_access`) and service-level `_ensure_access` helpers. Every new endpoint
  needs a role dependency (`AdminUser` / `StaffUser` / `CurrentUserDep`) **and** an
  ownership check when it takes a resource id.
- Webhooks (Razorpay, WhatsApp) are unauthenticated; trust comes only from HMAC
  signatures and they fail closed when the secret is not configured.
- Uploaded images are re-encoded (strips metadata/payloads); exports neutralise CSV
  formulas; storage paths are generated server-side and validated.

## Environment notes

- Local Python is 3.12 (pgserver has no wheels for newer versions).
- `.env` holds real credentials and is gitignored; never print or commit it.
- The Supabase direct DB host is IPv6-only; IPv4-only hosts need the pooler URL.
- Integrations without credentials fall back to mock/logging providers outside
  production; production configuration validation refuses those fallbacks.
