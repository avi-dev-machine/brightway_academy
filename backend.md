# Brightway Computer Academy

# Backend Engineering Specification

## 0. PRIMARY INSTRUCTION TO CLAUDE CODE

Build a production-ready, modular backend for Brightway Computer Academy.

The backend must be:

* Modular
* Testable
* Maintainable
* Secure
* Database-driven
* API-first
* Easy to extend
* Resistant to duplicate operations
* Capable of recovering from expected failures

DO NOT build the entire backend as one large file.

DO NOT create fake implementations and mark them as complete.

DO NOT silently ignore errors.

DO NOT repeatedly retry the same failing operation without changing the approach.

DO NOT get stuck in an infinite debugging loop.

When an error occurs:

1. Read the complete error.
2. Identify the actual root cause.
3. Inspect the relevant code/configuration/schema.
4. Make one focused correction.
5. Run the smallest relevant test.
6. If successful, continue.
7. If unsuccessful, investigate a different cause/approach.
8. After a reasonable number of failed attempts, STOP and report:

   * what failed
   * what was attempted
   * the exact blocker
   * what input/credential/decision is required

Never repeatedly run the same command hoping it will eventually work.

---

# 1. PRODUCT PURPOSE

Brightway Computer Academy requires a central academy management backend.

The system manages:

* Students
* Student photographs
* Courses
* Batches
* Teachers
* Admins
* Fees
* Payments
* Receipts
* Attendance
* Notifications
* WhatsApp/SMS reminders
* ID cards
* Reports
* Initial CSV migration
* Audit logs

Supabase PostgreSQL is the primary database.

FastAPI is the application backend.

The website will communicate with the backend through REST APIs.

---

# 2. SOURCE OF TRUTH

The existing CSV is a LEGACY DATA SOURCE.

It is used for the initial migration.

Flow:

LEGACY CSV
↓
VALIDATION
↓
IMPORT PREVIEW
↓
ADMIN CONFIRMATION
↓
SUPABASE DATABASE
↓
LIVE APPLICATION

After the initial migration:

SUPABASE DATABASE = SOURCE OF TRUTH

The application must NOT continuously overwrite the database from CSV.

CSV should only be used later for:

* Export
* Backup
* Reporting
* Explicitly authorized migration/update operations

---

# 3. REQUIRED INITIAL CSV FIELDS

The existing student database contains:

* ID No.
* Name
* Guardian's Name
* Address
* Contact No.
* Course

These values must be preserved.

Do not rename or destroy legacy ID numbers.

Internally use UUIDs as primary keys.

The academy's `ID No.` must remain a unique human-readable identifier.

---

# 4. TECHNOLOGY STACK

## Backend

Python 3.12+

FastAPI

Pydantic v2

Pydantic Settings

Uvicorn

pytest

httpx

ruff

mypy where practical

## Database

Supabase PostgreSQL

Use migrations.

Do not manually modify production tables without a migration.

## Authentication

Supabase Auth.

Application roles:

* ADMIN
* TEACHER
* STUDENT

## Storage

Supabase Storage.

Private buckets for:

* student photographs
* ID cards
* receipts
* academy assets

## External Services

Razorpay:

* online payments
* payment verification
* webhooks

WhatsApp provider:

* fee reminders
* payment notifications

SMS provider:

* fee reminders
* payment notifications

Email provider:

* optional

The actual API credentials will be supplied by the owner later.

The backend must be developed so that missing external credentials do not prevent local development of unrelated modules.

---

# 5. MODULAR PROJECT STRUCTURE

Use this structure:

```text
backend/
│
├── app/
│   │
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── logging.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       ├── auth.py
│   │       ├── students.py
│   │       ├── courses.py
│   │       ├── batches.py
│   │       ├── teachers.py
│   │       ├── fees.py
│   │       ├── payments.py
│   │       ├── receipts.py
│   │       ├── attendance.py
│   │       ├── notifications.py
│   │       ├── imports.py
│   │       ├── id_cards.py
│   │       ├── reports.py
│   │       └── admin.py
│   │
│   ├── core/
│   │   ├── security.py
│   │   ├── permissions.py
│   │   ├── constants.py
│   │   └── errors.py
│   │
│   ├── db/
│   │   ├── client.py
│   │   ├── transactions.py
│   │   └── migrations/
│   │
│   ├── models/
│   │   ├── student.py
│   │   ├── course.py
│   │   ├── batch.py
│   │   ├── teacher.py
│   │   ├── fee.py
│   │   ├── payment.py
│   │   ├── receipt.py
│   │   ├── attendance.py
│   │   ├── notification.py
│   │   ├── import_job.py
│   │   ├── audit.py
│   │   └── settings.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── student.py
│   │   ├── course.py
│   │   ├── batch.py
│   │   ├── teacher.py
│   │   ├── fee.py
│   │   ├── payment.py
│   │   ├── receipt.py
│   │   ├── attendance.py
│   │   ├── notification.py
│   │   ├── import_job.py
│   │   └── common.py
│   │
│   ├── repositories/
│   │   ├── student_repository.py
│   │   ├── course_repository.py
│   │   ├── batch_repository.py
│   │   ├── fee_repository.py
│   │   ├── payment_repository.py
│   │   ├── receipt_repository.py
│   │   ├── attendance_repository.py
│   │   ├── notification_repository.py
│   │   └── audit_repository.py
│   │
│   ├── services/
│   │   ├── student_service.py
│   │   ├── course_service.py
│   │   ├── batch_service.py
│   │   ├── fee_service.py
│   │   ├── payment_service.py
│   │   ├── receipt_service.py
│   │   ├── attendance_service.py
│   │   ├── notification_service.py
│   │   ├── id_card_service.py
│   │   ├── csv_import_service.py
│   │   ├── report_service.py
│   │   └── audit_service.py
│   │
│   ├── integrations/
│   │   ├── razorpay/
│   │   │   ├── client.py
│   │   │   ├── service.py
│   │   │   └── webhook.py
│   │   │
│   │   ├── whatsapp/
│   │   │   ├── client.py
│   │   │   └── service.py
│   │   │
│   │   ├── sms/
│   │   │   ├── client.py
│   │   │   └── service.py
│   │   │
│   │   └── storage/
│   │       ├── client.py
│   │       └── service.py
│   │
│   ├── workers/
│   │   ├── scheduler.py
│   │   ├── fee_reminders.py
│   │   └── notification_jobs.py
│   │
│   └── utils/
│       ├── pagination.py
│       ├── validators.py
│       ├── file_validation.py
│       └── id_generator.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── payments/
│   ├── imports/
│   └── security/
│
├── scripts/
│   ├── import_initial_csv.py
│   ├── seed_admin.py
│   └── health_check.py
│
├── .env.example
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

# 6. ARCHITECTURE RULE

Use this dependency direction:

API
↓
Service
↓
Repository
↓
Database

External integration:

Service
↓
Integration adapter
↓
External provider

Do not allow API routes to contain complex business logic.

Example:

BAD:

```text
students.py
    500 lines
    database queries
    validation
    payment logic
    storage logic
```

GOOD:

```text
students.py
    ↓
student_service.py
    ↓
student_repository.py
```

---

# 7. CONFIGURATION

All external configuration must come from environment variables.

Create:

`.env.example`

```env
APP_ENV=development
APP_BASE_URL=http://localhost:8000

SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=

WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_WEBHOOK_VERIFY_TOKEN=

SMS_PROVIDER_API_KEY=
SMS_SENDER_ID=

EMAIL_API_KEY=

STUDENT_PHOTO_BUCKET=student-photos
ID_CARD_BUCKET=id-cards
RECEIPT_BUCKET=receipts
ACADEMY_ASSETS_BUCKET=academy-assets
```

Never commit `.env`.

Never expose secret values through frontend APIs.

---

# 8. DEVELOPMENT WITHOUT API KEYS

The owner will provide the real API credentials.

Until then:

* Implement provider interfaces.
* Implement mock/test adapters where appropriate.
* Do not invent real credentials.
* Do not hard-code fake production credentials.
* Keep external integrations isolated.

Example:

```text
PaymentProvider
    ├── RazorpayPaymentProvider
    └── MockPaymentProvider
```

This allows the backend to be tested before Razorpay credentials are supplied.

When credentials are supplied, replace the configuration/adapter without rewriting the payment domain logic.

---

# 9. STUDENT MODULE

Student service must support:

### Create

* ID No.
* Name
* Guardian name
* Address
* Contact
* Course
* Photo
* Admission date

### Read

* Individual student
* Search
* Pagination
* Course filter
* Batch filter
* Active/inactive filter

### Update

* Name
* Guardian
* Address
* Contact
* Course
* Photo
* Status

### Deactivate

Never hard-delete students by default.

Use:

```text
active
inactive
```

Historical payments and receipts must remain intact.

---

# 10. PHOTO MODULE

When an admin creates a new admission:

```text
Admin enters student data
        ↓
Photo selected/captured
        ↓
Backend validates image
        ↓
Supabase Storage
        ↓
Student photo_path saved
        ↓
ID-card service
        ↓
ID-card generated
```

Validate:

* MIME type
* file extension
* file size
* image dimensions
* corrupted image

Do not store large binary images directly in PostgreSQL.

---

# 11. ID CARD MODULE

ID cards must be template-driven.

Template fields:

```text
{{academy_name}}
{{student_id}}
{{name}}
{{guardian_name}}
{{course}}
{{photo}}
{{contact}}
{{address}}
```

The backend should populate the template dynamically.

Do not generate an ID card by hard-coding student information.

Store generated file reference.

Support regeneration.

---

# 12. CSV IMPORT MODULE

The importer must be independent from the normal student service.

Pipeline:

```text
CSV Upload
    ↓
File Validation
    ↓
Header Validation
    ↓
Row Parsing
    ↓
Data Normalization
    ↓
Duplicate Detection
    ↓
Course Mapping
    ↓
Validation Report
    ↓
Admin Confirmation
    ↓
Database Transaction/Controlled Batch Insert
    ↓
Import Report
```

Required columns:

```text
ID No.
Name
Guardian's Name
Address
Contact No.
Course
```

Do not import until validation succeeds or the admin explicitly confirms the acceptable error policy.

Never silently discard rows.

---

# 13. PAYMENT MODULE

Payment domain must be independent of Razorpay.

Use:

```text
PaymentService
        ↓
PaymentProvider interface
        ↓
Razorpay adapter
```

This makes the system replaceable.

Payment flow:

```text
Student
 ↓
FeeService
 ↓
PaymentService
 ↓
Razorpay
 ↓
Webhook
 ↓
PaymentService
 ↓
Database transaction
 ↓
Fee update
 ↓
Receipt generation
 ↓
Notification
```

Use idempotency.

Unique provider identifiers:

* provider_order_id
* provider_payment_id

A payment must never be processed twice.

---

# 14. FEE MODULE

Support:

* monthly fees
* installments
* one-time fees
* partial payments
* concessions
* offline payments
* overdue fees

Fee states:

```text
PENDING
PARTIALLY_PAID
PAID
OVERDUE
CANCELLED
```

Payment states:

```text
CREATED
PENDING
SUCCESS
FAILED
REFUNDED
```

Do not mix fee status and payment status.

---

# 15. RECEIPT MODULE

After a verified successful payment:

```text
Payment SUCCESS
      ↓
Create receipt record
      ↓
Generate PDF
      ↓
Upload PDF to Storage
      ↓
Save receipt path
      ↓
Notify student
```

Receipt generation must be idempotent.

A duplicate webhook must find the existing receipt rather than generate another one.

---

# 16. NOTIFICATION MODULE

Create a provider-independent interface.

```text
NotificationService
        ↓
NotificationProvider
        ├── WhatsAppProvider
        ├── SMSProvider
        └── EmailProvider
```

This allows providers to be changed later.

Notification states:

```text
QUEUED
SENDING
SENT
DELIVERED
FAILED
```

Store provider message IDs.

---

# 17. FEE REMINDER WORKER

Do not run reminders inside normal API requests.

Use a scheduler/background worker.

Pipeline:

```text
Scheduler
 ↓
Find unpaid fees
 ↓
Determine reminder stage
 ↓
Check reminder history
 ↓
Create notification job
 ↓
Send through provider
 ↓
Record result
```

Reminder deduplication key:

```text
student_id
+
fee_id
+
reminder_stage
+
reminder_date
```

If the fee becomes paid:

```text
STOP FUTURE REMINDERS
```

---

# 18. AUTHORIZATION

Every protected endpoint must verify:

1. authenticated user
2. user role
3. resource ownership/access

Example:

Student:

```text
GET /students/{id}
```

must only succeed if `{id}` belongs to the authenticated student.

Teacher:

Only assigned students/batches.

Admin:

Full authorized access.

Never rely on frontend route protection alone.

---

# 19. DATABASE RULES

Use:

* UUID primary keys
* foreign keys
* unique constraints
* indexes
* check constraints where useful
* created_at
* updated_at

Critical unique values:

```text
students.id_no
payments.provider_payment_id
payments.provider_order_id
receipts.receipt_number
```

Never use:

```text
student name
phone number
course name
```

as a primary identifier.

---

# 20. ERROR HANDLING

Create application-specific exceptions:

```text
StudentNotFoundError
DuplicateStudentError
InvalidCSVError
PaymentVerificationError
UnauthorizedError
ReceiptGenerationError
ExternalServiceError
```

Return consistent API responses.

Example:

```json
{
  "success": false,
  "error": {
    "code": "STUDENT_NOT_FOUND",
    "message": "Student was not found."
  }
}
```

Do not expose:

* stack traces
* database credentials
* API secrets
* internal provider credentials

to users.

---

# 21. LOGGING

Use structured logs.

Every important operation should have:

* timestamp
* request ID
* user ID
* operation
* status
* duration
* error information if applicable

Never log:

* passwords
* API secrets
* access tokens
* full payment secrets

---

# 22. HEALTH CHECKS

Implement:

```text
GET /health
GET /health/db
GET /health/storage
```

`/health` should verify application availability.

Do not make health checks depend on optional external APIs.

A missing WhatsApp credential should not make the entire backend appear dead during development.

---

# 23. API VERSIONING

Use:

```text
/api/v1/
```

Example:

```text
/api/v1/students
/api/v1/fees
/api/v1/payments
```

Do not expose unversioned business APIs in production.

---

# 24. TESTING REQUIREMENT

Every major module must have tests.

Minimum:

### Unit tests

* validation
* fee calculations
* payment state transitions
* reminder scheduling
* CSV parsing
* duplicate detection

### Integration tests

* Supabase/database operations
* student creation
* fee creation
* payment reconciliation
* receipt creation

### API tests

* authentication
* authorization
* CRUD
* filtering
* pagination

### Security tests

* student cannot access another student
* teacher cannot access admin endpoints
* unauthenticated request rejected
* invalid webhook rejected

### Payment tests

Test:

* successful payment
* failed payment
* pending payment
* duplicate webhook
* invalid signature
* wrong amount
* already processed payment

---

# 25. TESTING COMMANDS

Configure standard commands:

```bash
pytest
```

```bash
pytest -q
```

```bash
ruff check .
```

```bash
ruff format --check .
```

If mypy is configured:

```bash
mypy app
```

Before declaring a module complete:

```text
tests pass
lint passes
application starts
API route loads
database interaction works
authorization works
```

---

# 26. DEBUGGING PROTOCOL

When something fails:

### Step 1

Capture the complete error.

### Step 2

Identify whether it is:

* syntax
* dependency
* configuration
* database
* authentication
* authorization
* application logic
* external API
* test failure
* environment problem

### Step 3

Inspect the relevant implementation.

### Step 4

Make the smallest appropriate change.

### Step 5

Run the relevant test.

### Step 6

Run the complete test suite after local success.

### Step 7

Continue only when stable.

---

# 27. ANTI-LOOP RULE

CRITICAL:

Never do this:

```text
run command
↓
same error
↓
same command
↓
same error
↓
same command
```

If the same error occurs twice without a meaningful change in diagnosis or environment:

STOP.

Explain:

```text
BLOCKED

Error:
...

Root cause:
...

Attempts:
1. ...
2. ...

Required action:
...

Waiting for:
...
```

Then wait for the owner.

Do not waste time repeatedly retrying.

---

# 28. EXTERNAL CREDENTIAL BLOCKER

If implementation reaches a point where an external credential is genuinely required:

STOP only that integration.

Do NOT stop the entire project.

Example:

```text
Razorpay credentials unavailable.

Payment domain implementation:
COMPLETE

Razorpay adapter:
WAITING FOR CREDENTIALS

Continue implementing:
- fee management
- receipts
- student dashboard
- tests
- mock payment provider
```

When the owner supplies credentials, continue from the blocked integration.

Never ask for credentials that are not actually needed yet.

---

# 29. DATABASE MIGRATIONS

All schema changes must be represented as migrations.

Never:

* manually change production schema
* delete tables to fix development issues
* destroy existing data during debugging

Migration process:

```text
Create migration
 ↓
Run locally
 ↓
Test
 ↓
Review SQL
 ↓
Apply to target environment
 ↓
Verify
```

---

# 30. ADMIN FIRST-RUN SETUP

The first-run process should allow the admin to:

1. Configure academy details.
2. Create the first admin account.
3. Upload the legacy CSV.
4. Validate the CSV.
5. Preview records.
6. Confirm import.
7. Import students.
8. Review import results.
9. Configure ID-card template.
10. Configure fee settings.
11. Configure notification settings.
12. Complete setup.

After setup is complete, normal admin dashboard becomes the primary interface.

---

# 31. DATA PRESERVATION

Never destroy existing student data during:

* CSV import
* course update
* photo update
* fee changes
* account deactivation

Financial history is immutable except through controlled adjustment/refund mechanisms.

Do not overwrite payment history.

Do not delete receipts.

---

# 32. PRODUCTION READINESS

Before production:

* environment variables configured
* production Supabase project connected
* migrations applied
* RLS reviewed
* admin account created
* storage policies reviewed
* Razorpay configured
* webhook configured
* WhatsApp configured
* SMS configured
* backups enabled
* HTTPS enabled
* CORS restricted
* rate limiting enabled
* logs enabled
* health checks working
* tests passing

---

# 33. IMPLEMENTATION ORDER

Claude Code must implement in this order:

## Phase 1 — Foundation

* project setup
* FastAPI
* configuration
* logging
* error handling
* health checks
* testing infrastructure

## Phase 2 — Supabase

* database connection
* migrations
* storage
* authentication
* roles

## Phase 3 — Students

* student model
* repository
* service
* API
* search
* filtering
* photo upload

## Phase 4 — CSV Migration

* importer
* validation
* duplicate detection
* preview
* import
* report

## Phase 5 — Courses/Batches

* course management
* batch management
* student assignment

## Phase 6 — ID Cards

* template
* rendering
* photo integration
* storage
* regeneration

## Phase 7 — Fees

* fee plans
* installments
* balances
* concessions
* offline payments

## Phase 8 — Payments

* payment abstraction
* mock provider
* Razorpay adapter
* verification
* webhook
* idempotency

## Phase 9 — Receipts

* receipt service
* PDF generation
* storage
* download

## Phase 10 — Attendance

* attendance
* teacher access
* reports

## Phase 11 — Notifications

* notification abstraction
* WhatsApp adapter
* SMS adapter
* email adapter

## Phase 12 — Automation

* scheduler
* fee reminders
* notification jobs
* retry handling
* deduplication

## Phase 13 — Reports

* dashboard statistics
* fee reports
* student reports
* exports

## Phase 14 — Hardening

* security tests
* authorization tests
* payment tests
* failure tests
* performance checks
* production configuration

---

# 34. DEFINITION OF DONE

The backend is complete only when:

[ ] Application starts successfully

[ ] Database migrations work

[ ] Supabase connection works

[ ] Authentication works

[ ] Role-based authorization works

[ ] Existing CSV imports correctly

[ ] Duplicate CSV import is safe

[ ] Student CRUD works

[ ] Student photo upload works

[ ] ID card generation works

[ ] Courses work

[ ] Batches work

[ ] Fees work

[ ] Partial payments work

[ ] Offline payments work

[ ] Razorpay integration works

[ ] Razorpay webhook verification works

[ ] Duplicate webhooks are safe

[ ] Receipts generate correctly

[ ] Attendance works

[ ] Notifications work

[ ] Fee reminders work

[ ] Duplicate reminders are prevented

[ ] Admin reports work

[ ] Audit logs work

[ ] API documentation works

[ ] Unit tests pass

[ ] Integration tests pass

[ ] Security tests pass

[ ] Lint passes

[ ] No critical TODOs remain

[ ] No secrets are committed

[ ] Production configuration is documented

---

# 35. FINAL CLAUDE CODE BEHAVIOUR

Act as a senior backend engineer.

Do not optimize for speed at the expense of correctness.

Do not generate unnecessary complexity.

Do not ask the owner to manually fix something that you can diagnose and fix yourself.

Do not stop because an optional integration credential is missing.

Do not invent credentials.

Do not repeatedly retry a failed operation.

Do not claim a feature is complete without testing it.

When blocked by a genuinely external dependency, clearly report the blocker and continue all independent work.

At the end of every implementation phase, report:

```text
PHASE:
STATUS:

Implemented:
- ...

Tests:
- ...

Issues fixed:
- ...

Remaining:
- ...

Blocked by:
- ...

Next:
- ...
```

The objective is a clean, modular, production-ready backend that can be connected to the frontend later without rewriting the core business logic.
