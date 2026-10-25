# Brightway Academy — Enterprise Academy Management Platform

A production-grade, end-to-end secured academy management and student fee payment platform built with Next.js 16 (App Router), FastAPI (Python 3.12), PostgreSQL / Supabase, and Razorpay.

---

## Architecture Overview

```
brightway/
├── backend/                  # FastAPI backend service
│   ├── app/
│   │   ├── api/v1/          # Modular REST API endpoints (students, fees, payments, admin, etc.)
│   │   ├── core/            # Security, JWT tokens, constants, custom exception handling
│   │   ├── db/              # Database connection pool and migrations (PostgreSQL/Supabase)
│   │   ├── integrations/    # Razorpay payment gateway, Meta WhatsApp, Fast2SMS, Supabase Storage
│   │   ├── models/          # Domain data models with strict validation
│   │   ├── repositories/    # Transaction-safe data access layer with row-level locks
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   ├── services/        # Core business logic (PaymentService, FeeService, StudentService)
│   │   └── utils/           # Rate limiting, date utilities, pagination
│   └── tests/               # 318+ automated unit, integration, and security tests
│
└── frontend/                 # Next.js 16 (React 19) web client
    ├── src/
    │   ├── app/             # Editorial public pages, student portal, and admin dashboard
    │   ├── components/      # Refined UI design system (Geist + Instrument Serif typography)
    │   ├── lib/             # API clients, session management, and auth tokens
    │   └── hooks/           # TanStack Query data hooks
    └── tests/               # Vitest component and logic tests
```

---

## Security & Payment Protection Measures

This platform handles financial transactions and sensitive student records. Multiple defense-in-depth security layers are enforced:

1. **Cryptographic Webhook Verification**:
   - Razorpay webhook payloads are strictly validated using constant-time HMAC-SHA256 comparison (`hmac.compare_digest`) with the configured `RAZORPAY_WEBHOOK_SECRET`.
   - Max payload size is bounded to 256 KB with per-IP rate limiting to thwart Denial of Service (DoS) attacks.
2. **Double-Spend & Race Condition Prevention**:
   - All payment settlements, offline fee records, and balance updates execute within ACID database transactions using row-level locking (`SELECT ... FOR UPDATE`).
   - Idempotency keys (`Idempotency-Key` HTTP header) are required for checkout orders and offline fee settlements to guarantee that network retries never charge twice.
3. **Integer Currency Handling**:
   - All monetary figures are calculated and stored in integer paise (`amount_paise`) across the frontend, API contracts, and database columns. Floating-point rounding errors are strictly eliminated.
4. **Server-Side Fee Reconciliation**:
   - Payment order amounts are computed and locked server-side from the student's actual fee schedule. Client-provided amounts can never exceed outstanding balances.
   - The checkout verification flow verifies the signature **and** fetches the payment record directly from Razorpay's API server-to-server before marking any record as `SUCCESS`.
5. **Zero Secret Leakage in Source Control**:
   - All production credentials, private keys, `.env` files, Supabase secrets, and student PII CSVs are strictly git-ignored and never committed.
   - `.env.example` templates document every configuration key with dummy placeholders.
6. **Robust HTTP Security Headers**:
   - `Content-Security-Policy`: Restricts scripts, styles, and frames to trusted endpoints (e.g. Razorpay Checkout iframe).
   - `X-Content-Type-Options: nosniff`: Prevents MIME-sniffing exploits.
   - `X-Frame-Options: SAMEORIGIN` / `DENY`: Protects against clickjacking.
   - `X-XSS-Protection: 1; mode=block`: Enables cross-site scripting filters.
   - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`: Enforces TLS encryption.
   - `Referrer-Policy: strict-origin-when-cross-origin`: Minimizes referrer leakage.
   - `Permissions-Policy`: Restricts camera, microphone, and geolocation.
7. **Role-Based Access Control (RBAC) & Ownership Verification**:
   - Endpoints enforce strict RBAC roles (`ADMIN`, `TEACHER`, `STUDENT`).
   - Broken Object Level Authorization (BOLA) is mitigated: student tokens can only view, download receipts for, or initiate payments on their own records.
8. **Rate Limiting**:
   - High-sensitivity endpoints (login, OTP authentication, payment initiation, and webhooks) are throttled via in-memory sliding window rate limiters.

---

## Getting Started

### Prerequisites
- Node.js 20+ and npm 10+
- Python 3.12+
- PostgreSQL or Supabase instance

### Backend Setup
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your PostgreSQL/Supabase & Razorpay keys

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local if needed

# Run unit tests
npm run test

# Build production bundle
npm run build

# Start development server
npm run dev
```

---

## License
Proprietary — Brightway Computer Academy. All rights reserved.
