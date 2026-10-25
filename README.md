# 🎓 Brightway Computer Academy — Management & Fee Payment Platform

A modern, production-grade academy management system and fee payment platform designed for Brightway Computer Academy. Built with **Next.js 16 (App Router)**, **FastAPI (Python 3.12)**, **PostgreSQL / Supabase**, and **Razorpay**.

---

## 🚀 Quick Access URLs

| Portal / Page | Local URL | Description |
| :--- | :--- | :--- |
| **Public Website** | [http://localhost:3000](http://localhost:3000) | Academy homepage, course catalog, admissions, and contact |
| **Unified Login** | [http://localhost:3000/login](http://localhost:3000/login) | Single sign-in for Admins, Teachers, and Students |
| **Admin Dashboard** | [http://localhost:3000/admin](http://localhost:3000/admin) | Full management of students, fees, attendance, notices, and reports |
| **Student Portal** | [http://localhost:3000/student](http://localhost:3000/student) | Fee balance, online/UPI payment, attendance, and PDF receipts |
| **Teacher Portal** | [http://localhost:3000/teacher](http://localhost:3000/teacher) | Class batches and student daily roll-call attendance |
| **Backend API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger API documentation |

---

## 🔑 Default Sign-in Credentials

The platform features a unified login interface at `/login` that automatically redirects users based on their role:

### 1. Administrator Account
- **ID / Username**: `BWADMIN` *(or `admin@brightway.academy`)*
- **Password**: `Brightway@Admin2026!`
- **Destination**: `/admin` (Full administrative privileges)

### 2. Student Accounts
- **ID / Identifier**: Assigned Student ID *(e.g. `BW-2024-001`, roll number, or registered email)*
- **Password / Passcode**: Universal student passcode *(Format: First 3 letters of student's name in UPPERCASE + last 4 digits of Student ID, e.g. `RAH0001`)*
- **Destination**: `/student` (Personal profile, fees, and receipts)

### 3. Teacher Accounts
- **ID / Identifier**: Teacher email or phone number
- **Password**: Configured teacher password
- **Destination**: `/teacher` (Batch rosters and attendance)

---

## ✨ Features Overview

### 🏛️ 1. Administrative Suite (`/admin`)

- **Live Executive Dashboard (`/admin`)**:
  - Real-time KPI counters: Active Students, Total Revenue Collected, Pending Fee Dues, and Overall Attendance Percentage.
  - Interactive monthly revenue chart and recent activity feed.

- **Student Directory & Detail Editor (`/admin/students`)**:
  - Search students instantly by name, student code, phone, course, or admission date.
  - Filter by course, batch, or fee status (`Paid`, `Partial`, `Overdue`).
  - **Edit Any Student Attribute**: Click the **Edit** action to update:
    - Student Code / ID (re-assign or update student IDs at any time).
    - Full Name, Contact Number (E.164 format), and Email.
    - Guardian Name & Guardian Phone.
    - Course Enrollment & Batch Allocation.
    - Status (`Active`, `Suspended`, `Completed`, `Dropped`) and Admin Remarks.

- **📲 WhatsApp Due Fees Notice System**:
  - **Individual Student Notice**: Click the green **WhatsApp Notice** button beside any student with pending fees:
    - Calculates total outstanding fee balance.
    - Lists specific unpaid months (e.g. *Jan 2026, Feb 2026*).
    - Pre-composes a polite, professional notice in English/Hindi.
    - Provides a direct 1-click **Open in WhatsApp** button (`https://wa.me/...`) to send via WhatsApp Web or mobile app.
  - **Master Broadcast Button ("Notify All Unpaid")**:
    - Click **Notify All Unpaid** at the top of the student directory.
    - Scans all active students with outstanding dues.
    - Allows adding a custom announcement note.
    - Queues notifications and reports how many students were notified.

- **Fee Settlement & Payments (`/admin/fees`, `/admin/receipts`)**:
  - Track fee schedules, course installments, and monthly subscriptions.
  - **Record Offline Payments**: Record Cash, Cheque, Bank Transfer, POS Card, or manual UPI payments.
  - **Automatic PDF Receipt**: Generates a downloadable, tax-compliant PDF receipt with a unique receipt number for every transaction.

- **Attendance Management (`/admin/attendance`)**:
  - Mark daily attendance batch-by-batch with 1-click toggles: `Present`, `Absent`, or `Late`.
  - Monthly attendance calendar and student attendance percentages.

- **Course & Batch Management (`/admin/courses`, `/admin/batches`)**:
  - Configure course duration, curriculum, fee amounts, and installment rules.
  - Schedule class batches with day/time slots and assign faculty instructors.

- **🪪 Student ID Card Studio (`/admin/id-cards`)**:
  - Generate official student ID cards complete with photo, barcode/QR code, course name, and emergency contacts.
  - Print individual ID cards or batch export to PDF.

- **📁 Legacy CSV Data Migration (`/admin/import`)**:
  - Upload legacy Excel or CSV spreadsheets (`cert` and `non-cert` records).
  - Automatically parses students, calculates historical fee balances, and maps course enrollments with transactional rollback safety.

- **Reports & Analytics (`/admin/reports`)**:
  - Fee collection ledger, fee aging report, course-wise enrollment metrics, and attendance trends.
  - 1-click CSV and PDF exports for accounting.

- **Academy Settings (`/admin/settings`)**:
  - Manage academy contact info, address, logo, WhatsApp API tokens, and payment credentials.

---

### 👨‍🎓 2. Student Portal (`/student`)

- **Student Dashboard (`/student`)**: Overview of current course, batch timing, upcoming schedule, and fee summary.
- **Pay Fees Online (`/student/fees`)**:
  - View detailed fee breakdown (Total Course Fee, Concessions, Paid Amount, Balance Due).
  - **Pay Online via Razorpay**: Credit/Debit Card, Net Banking, and Wallet checkout.
  - **Direct UPI / QR Code Payment**: Instant UPI QR code generator for payments via GPay, PhonePe, Paytm, or BHIM.
- **Fee Receipts Repository (`/student/receipts`)**: View complete payment history and download signed PDF receipts anytime.
- **Attendance Records (`/student/attendance`)**: Transparent view of individual attendance percentage and date-wise status.
- **Notices & Profile (`/student/notifications`, `/student/profile`)**: Academy announcements, fee alerts, and personal details.

---

### 👨‍🏫 3. Teacher Portal (`/teacher`)

- **Assigned Batches (`/teacher/batches`)**: Roster of enrolled students and class schedules.
- **Fast Attendance Roll-Call (`/teacher/attendance`)**: Mark batch attendance in seconds with auto-save.

---

### 🌐 4. Public Web Pages

- **Homepage (`/`)**: Academy showcase with editorial typography (Geist + Instrument Serif), featured courses, why choose us, and student testimonials.
- **About Us (`/about`)**: Academy mission, lab infrastructure, faculty credentials, and history.
- **Course Catalog (`/courses`)**: Detailed course syllabus, duration, prerequisites, and certifications.
- **Admissions (`/admissions`)**: Online admission inquiry form for prospective students.
- **Contact & Location (`/contact`)**: Interactive Google Map embed, academy phone numbers, WhatsApp link, and physical address.

---

## 🛠️ How to Operate the Platform

### Step 1: Start the Backend Service
Open a terminal in the project directory:
```powershell
cd backend
# Activate Python virtual environment
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux / macOS

# Launch FastAPI development server
uvicorn app.main:app --reload --port 8000
```
Backend is now running at `http://localhost:8000` (API documentation at `http://localhost:8000/docs`).

---

### Step 2: Start the Frontend Application
Open a second terminal:
```powershell
cd frontend
# Launch Next.js development server
npm run dev
```
Frontend is now accessible at `http://localhost:3000`.

---

### Step 3: Common Operating Workflows

#### A. How to Edit a Student's Details or Re-assign Student ID
1. Log in as Admin (`BWADMIN` / `Brightway@Admin2026!`).
2. Go to **Students** (`/admin/students`) in the sidebar.
3. Locate the student and click the **Edit** icon (pencil) in the actions column.
4. Update any field: **Student ID / Code**, **Name**, **Phone**, **Course**, **Batch**, **Guardian**, or **Remarks**.
5. Click **Save Changes**. The directory and all linked records update immediately.

#### B. How to Send WhatsApp Fee Reminders
- **For an individual student**:
  1. On the **Students** page, look for the green **WhatsApp Notice** button in the student's row.
  2. A preview dialog opens displaying their unpaid months and calculated due balance.
  3. Click **Open in WhatsApp** to launch WhatsApp Web or your desktop app with the pre-formatted reminder text ready to send.
- **For all unpaid students at once**:
  1. Click the **Notify All Unpaid** master button located above the student table.
  2. Optionally type a custom broadcast announcement (e.g. *"Please clear dues before monthly exams"*).
  3. Click **Send Notices to All**. All unpaid students receive queued notifications with detailed payment breakdowns.

#### C. How to Record an Offline Payment (Cash / Cheque / UPI)
1. Go to **Fees** (`/admin/fees`) or click **Collect Fee** on any student's profile.
2. Select the payment method: **Cash**, **UPI**, **Bank Transfer**, **Cheque**, or **POS Card**.
3. Enter the amount received and reference / receipt note.
4. Click **Confirm Payment**. The balance updates automatically, and an official PDF receipt is generated instantly.

#### D. How a Student Pays Fees Online
1. The student logs in at `/login` using their Student ID and Passcode.
2. Navigates to **My Fees** (`/student/fees`).
3. Selects either:
   - **Pay via Razorpay**: Opens secure checkout modal supporting Cards, NetBanking, and UPI.
   - **Direct UPI / Dynamic QR**: Scans the auto-generated QR code using any UPI app (GPay / PhonePe / Paytm).
4. After payment, the receipt is immediately available under **Receipts** (`/student/receipts`).

#### E. How to Generate Student ID Cards
1. Go to **ID Cards** (`/admin/id-cards`).
2. Select a batch or individual students.
3. Preview the card layout with photograph and barcode.
4. Click **Export / Print ID Cards** to generate high-resolution, print-ready PDF cards.

---

## 🔒 Security & Payment Protection Highlights

The platform adheres to banking-grade payment security standards:
- **Zero Secrets in Git**: All credentials (`.env`, database URLs, Razorpay keys, student CSVs) are strictly excluded from source control.
- **HMAC-SHA256 Signature Verification**: Every webhook and payment callback is verified using constant-time cryptographic checks (`hmac.compare_digest`).
- **Two-Way Server Verification**: Frontend payment callbacks are confirmed by calling Razorpay's API server-to-server (`fetch_payment`) before marking any fee as paid.
- **Double-Spend & Race Condition Prevention**: Database transactions utilize row-level locking (`SELECT ... FOR UPDATE`) and `Idempotency-Key` headers.
- **Integer Currency**: All calculations use integer paise (`amount_paise`), eliminating floating-point rounding errors.
- **Strict Content-Security-Policy (CSP)**: Configured to prevent XSS, clickjacking, and unauthorized script injection.
- **Up-to-Date & Audited**: Powered by **Next.js 16.4.3** with 0 security audit vulnerabilities.

---

## 📞 Support & Maintenance
For questions, administrative setup, or server deployment support, contact the Brightway Computer Academy IT administration.
