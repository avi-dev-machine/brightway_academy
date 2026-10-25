# Brightway Computer Academy — Frontend Specification

## 1. Objective

Build a modern, responsive, production-ready frontend for Brightway Computer Academy.

The frontend consists of:

1. Public Academy Website
2. Student Portal
3. Teacher Portal
4. Admin Dashboard
5. Authentication flows
6. Online fee payment
7. Payment receipt access
8. Student ID-card generation workflow
9. Notifications and announcements
10. Reports and management interfaces

The frontend must communicate with the FastAPI backend.

The backend and Supabase database remain the source of truth.

Do NOT implement business-critical logic exclusively in the frontend.

---

# 2. Technology

Use:

* Next.js
* TypeScript
* React
* Tailwind CSS
* shadcn/ui where appropriate
* React Hook Form
* Zod
* TanStack Query
* Lucide icons
* Recharts for dashboard charts where useful

Use the existing project conventions if the repository already contains a working frontend setup.

Do not unnecessarily replace an existing working framework.

---

# 3. Design Direction

The interface should feel:

* Professional
* Modern
* Clean
* Trustworthy
* Educational
* Premium but not flashy
* Easy for non-technical academy staff to use

Avoid:

* Excessive gradients
* Excessive glassmorphism
* Over-animated interfaces
* Huge decorative elements
* Childish educational UI
* Dashboard clutter
* Excessive rounded cards
* Unnecessary animations

Prioritize clarity and usability.

Use subtle animation only where it improves UX.

---

# 4. Responsive Design

The entire application must work on:

* Desktop
* Laptop
* Tablet
* Mobile

Admin dashboard is desktop-first but must remain usable on tablets.

Student portal must be fully mobile-friendly.

Public website must be mobile-first.

Test at:

* 320px
* 375px
* 390px
* 768px
* 1024px
* 1440px+

Never allow horizontal overflow.

---

# 5. Application Structure

Recommended frontend structure:

frontend/
├── app/
│   ├── page.tsx
│   ├── login/
│   ├── admissions/
│   ├── courses/
│   ├── contact/
│   ├── student/
│   ├── teacher/
│   ├── admin/
│   └── api/
│
├── components/
│   ├── ui/
│   ├── layout/
│   ├── public/
│   ├── student/
│   ├── teacher/
│   ├── admin/
│   ├── payments/
│   ├── students/
│   ├── fees/
│   ├── attendance/
│   └── id-cards/
│
├── lib/
│   ├── api/
│   ├── auth/
│   ├── validations/
│   ├── utils/
│   └── constants/
│
├── hooks/
├── types/
├── providers/
├── stores/
├── public/
├── tests/
├── middleware.ts
└── README.md

Adapt this structure if the existing repository has a better established
architecture.

---

# 6. Public Website

Create:

/

/about

/courses

/admissions

/contact

/login

The homepage should contain:

* Academy introduction
* Main value proposition
* Courses
* Why Brightway
* Student-focused information
* Admission CTA
* Fee/payment information
* Contact information
* Academy location/map section
* Footer

Do not invent academy statistics, achievements, addresses, phone numbers,
faculty information, or course details.

Where information is unavailable, create configurable placeholders.

Academy location must come from configuration/database.

---

# 7. Admissions

Create an admission enquiry form.

Fields should support:

* Student name
* Guardian name
* Contact number
* Address
* Interested course
* Preferred batch
* Message

Validate all fields.

Submit to backend.

Show:

* Loading state
* Success state
* Validation errors
* Server errors

Prevent duplicate submissions.

---

# 8. Authentication

Implement role-aware authentication.

Roles:

ADMIN
TEACHER
STUDENT

Authentication should integrate with the backend/Supabase Auth architecture.

Never trust a role supplied by the browser.

The backend must enforce authorization.

Frontend role checks are only for navigation/UI.

After login:

ADMIN → /admin
TEACHER → /teacher
STUDENT → /student

Unauthorized users must be redirected appropriately.

---

# 9. Authentication UI

Create:

/login

Optional future routes:

/forgot-password

/reset-password

Login UI should support:

* Email/username according to backend implementation
* Password
* Show/hide password
* Loading state
* Invalid credentials
* Session errors
* Logout

Do not store sensitive credentials in localStorage.

---

# 10. Admin Dashboard

Route:

/admin

Layout:

Sidebar + top navigation + main content.

Sidebar:

* Dashboard
* Students
* Admissions
* Courses
* Batches
* Teachers
* Fees
* Payments
* Receipts
* Attendance
* ID Cards
* Notifications
* Reports
* Settings

Dashboard overview should show:

* Total students
* Active students
* New admissions
* Fees collected this month
* Outstanding fees
* Overdue fees
* Today's attendance
* Recent payments

Use charts only when they communicate useful information.

---

# 11. Student Management

Route:

/admin/students

Features:

* Search students
* Filter students
* Sort students
* Pagination
* View student
* Edit student
* Deactivate student
* Add student
* Upload photo

Filters:

* Course
* Batch
* Active/inactive
* Paid
* Partially paid
* Unpaid
* Overdue

Table columns:

* ID No.
* Photo
* Name
* Guardian
* Contact
* Course
* Batch
* Fee status
* Status
* Actions

Do not load the entire student database into the browser unnecessarily.

Use server-side pagination/filtering.

---

# 12. Student Profile

Create:

/admin/students/[id]

Show:

* Student photo
* ID No.
* Name
* Guardian
* Address
* Contact
* Course
* Batch
* Admission date
* Status

Tabs:

* Overview
* Fees
* Payments
* Receipts
* Attendance
* ID Card
* Activity/Audit

Allow authorized admin users to edit information.

---

# 13. Student Photo Upload

Photo upload UI must:

* Accept JPG/JPEG/PNG/WebP
* Validate file size
* Validate MIME type
* Show preview
* Allow replacement
* Show upload progress
* Handle failed uploads

The frontend must not assume that a file extension makes a file safe.

Backend validation remains authoritative.

Do not expose private Supabase Storage buckets directly.

Use signed URLs or backend-controlled access.

---

# 14. CSV Import

Admin route:

/admin/import

Workflow:

STEP 1
Upload CSV

STEP 2
Validate

STEP 3
Preview

STEP 4
Show errors/warnings

STEP 5
Admin confirmation

STEP 6
Import

STEP 7
Import report

Show:

* Total rows
* Valid rows
* Invalid rows
* Duplicate rows
* Imported rows
* Failed rows

Never immediately import a CSV merely because it was uploaded.

The initial CSV is a migration source, not the permanent database.

---

# 15. Courses

Route:

/admin/courses

Features:

* List courses
* Add course
* Edit course
* Activate/deactivate course
* Default fee
* Duration

Do not allow deletion if historical student/payment records depend on the course.

Use deactivation instead.

---

# 16. Batches

Route:

/admin/batches

Support:

* Batch name
* Course
* Teacher
* Schedule
* Capacity
* Active status

Show enrolled student count.

Prevent invalid batch/course combinations.

---

# 17. Fees

Route:

/admin/fees

Provide:

* Fee overview
* Monthly fees
* Outstanding fees
* Overdue fees
* Partial payments
* Discounts/concessions
* Offline payments

Filters:

* Month
* Course
* Batch
* Status
* Student
* Payment method

Statuses:

PENDING
PARTIALLY_PAID
PAID
OVERDUE
CANCELLED

---

# 18. Fee Collection

Admin can record an offline payment.

Require:

* Student
* Fee
* Amount
* Payment method
* Payment date
* Reference/transaction number where applicable
* Notes

Show confirmation before submission.

Never silently modify an existing payment.

Backend must create an audit record.

---

# 19. Student Fee Portal

Student route:

/student/fees

Show:

* Current fee
* Due date
* Paid amount
* Outstanding amount
* Payment status
* Previous payments

Provide:

PAY NOW

button for eligible unpaid/outstanding fees.

---

# 20. Razorpay Payment

Payment flow:

1. Student clicks Pay Now.
2. Frontend requests payment order from backend.
3. Backend creates Razorpay order.
4. Frontend opens Razorpay checkout.
5. Payment completes.
6. Frontend sends required result to backend.
7. Backend verifies payment/signature.
8. Backend/webhook confirms final status.
9. Frontend refreshes payment state.
10. Receipt becomes available after verified success.

IMPORTANT:

Never mark a payment as successful solely because Razorpay's frontend
callback says it succeeded.

Never calculate authoritative payment status in the frontend.

Do not expose Razorpay secret credentials.

---

# 21. Payment UI

Show:

* Amount
* Fee period
* Student
* Payment method
* Processing state
* Success
* Failed
* Pending

After success:

"Payment verified"

Then:

* Receipt number
* Download receipt
* View receipt

If payment is pending, clearly show that the payment is still being verified.

---

# 22. Receipts

Route:

/student/receipts

Admin:

/admin/receipts

Show:

* Receipt number
* Student
* Amount
* Date
* Payment method
* Fee period
* Status

Allow:

VIEW
DOWNLOAD

Receipts are immutable historical records.

Do not allow users to edit receipt amounts from the frontend.

---

# 23. Student Dashboard

Route:

/student

Show:

* Welcome section
* Student information
* Current course
* Batch
* Current fee status
* Next due date
* Recent payments
* Attendance summary
* Announcements

Primary actions:

PAY FEES
VIEW RECEIPTS
VIEW ATTENDANCE
VIEW PROFILE

Keep the student dashboard simple.

---

# 24. Student Profile

Route:

/student/profile

Display:

* Photo
* Name
* ID No.
* Guardian
* Contact
* Address
* Course
* Batch
* Admission date

Students should only be allowed to edit fields explicitly permitted by backend policy.

---

# 25. Attendance

Teacher route:

/teacher/attendance

Teacher should be able to:

* Select batch
* Select date
* View enrolled students
* Mark present/absent
* Submit attendance
* Edit attendance only when authorized

Use a fast table/toggle interface.

Avoid making teachers open individual student pages to mark attendance.

Student:

/student/attendance

Show:

* Attendance percentage
* Present
* Absent
* Attendance history

---

# 26. Teacher Portal

Route:

/teacher

Dashboard:

* Assigned batches
* Student count
* Today's classes
* Attendance pending
* Announcements

Teacher permissions:

* View assigned students
* Mark attendance
* View relevant student information
* View assigned batches
* Create/view announcements if authorized

Teacher must NOT have admin access.

---

# 27. Notifications

Admin:

/admin/notifications

Show:

* SMS
* WhatsApp
* Email if enabled
* Delivery status
* Failed notifications

Student:

/student/notifications

Show relevant notifications.

The frontend should display backend notification status.

Do not implement SMS/WhatsApp delivery logic in React.

---

# 28. ID Card Generation

Admin:

/admin/id-cards

Student profile should have:

GENERATE ID CARD

The frontend should:

1. Send student/template information to backend.
2. Show generation state.
3. Poll or receive completion state if asynchronous.
4. Display generated ID card.
5. Allow preview.
6. Allow download/print.

The backend owns template rendering and generated file storage.

Frontend must not permanently store generated ID-card files locally.

---

# 29. Reports

Admin:

/admin/reports

Useful reports:

* Student list
* Course-wise students
* Batch-wise students
* Fee collection
* Outstanding fees
* Overdue fees
* Payment history
* Attendance
* Admissions

Provide:

* Date filters
* Course filters
* Batch filters
* Export action

Large exports should be generated by the backend rather than processing
thousands of records in the browser.

---

# 30. API Client

Create a centralized API client.

Example:

lib/api/client.ts

Responsibilities:

* Base URL
* Authentication headers
* Request handling
* JSON parsing
* Error normalization
* Timeout handling

Do not scatter fetch() calls throughout components.

Create domain-specific API modules:

lib/api/auth.ts
lib/api/students.ts
lib/api/courses.ts
lib/api/batches.ts
lib/api/fees.ts
lib/api/payments.ts
lib/api/receipts.ts
lib/api/attendance.ts
lib/api/notifications.ts
lib/api/id-cards.ts
lib/api/reports.ts

---

# 31. TanStack Query

Use TanStack Query for server state.

Use it for:

* Students
* Courses
* Batches
* Fees
* Payments
* Receipts
* Attendance
* Notifications
* Reports

Implement:

* loading states
* error states
* caching
* invalidation
* optimistic updates only where safe

After a successful payment, invalidate/refetch relevant fee/payment/receipt
queries.

---

# 32. Forms

Use:

React Hook Form
+
Zod

Every important form must have:

* Client validation
* Server validation handling
* Field-level errors
* Submission state
* Success feedback
* Error feedback

Never rely exclusively on client-side validation.

---

# 33. Loading States

Every API-dependent page must have a deliberate loading state.

Use:

* Skeletons
* Spinners for short actions
* Progress indicators for uploads/generation

Avoid blank screens.

---

# 34. Error Handling

Provide user-friendly errors.

Examples:

Network error:

"Unable to connect to the server. Please try again."

Payment pending:

"Your payment is being verified. Please check your payment history shortly."

Unauthorized:

"You don't have permission to access this page."

Do not expose:

* stack traces
* SQL errors
* internal exception messages
* API keys
* Supabase secrets

---

# 35. Empty States

Every major data page must have a useful empty state.

Examples:

"No students found."

"No overdue fees."

"No payments yet."

"No attendance records available."

Do not show broken tables when there is no data.

---

# 36. Confirmation Dialogs

Require confirmation for destructive/high-impact actions:

* Deactivate student
* Deactivate course
* Cancel fee
* Refund payment
* Delete/disable account
* Import CSV
* Record large offline payment

Example:

"You are about to deactivate this student. Historical payments and
receipts will remain available."

---

# 37. Navigation Protection

Implement middleware/route protection.

Examples:

/admin/* → ADMIN

/teacher/* → TEACHER or ADMIN if explicitly allowed

/student/* → STUDENT

Do not rely only on hiding navigation items.

Backend authorization remains mandatory.

---

# 38. Security

Never place these in client-side code:

* Supabase service-role key
* Database password
* Razorpay secret
* WhatsApp access token
* SMS provider secret
* Email provider secret

Only public/publishable configuration may be exposed.

Do not put secrets in:

* NEXT_PUBLIC_ variables
* localStorage
* source code
* Git
* browser bundles

---

# 39. Environment Variables

Frontend should use only required public configuration.

Example:

NEXT_PUBLIC_API_BASE_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=

Never expose:

DATABASE_URL
DATABASE_PASSWORD
SUPABASE_SERVICE_ROLE_KEY
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
WHATSAPP_ACCESS_TOKEN
SMS_PROVIDER_API_KEY

---

# 40. Accessibility

Implement:

* semantic HTML
* keyboard navigation
* visible focus states
* labels for inputs
* accessible dialogs
* accessible buttons
* sufficient contrast
* screen-reader-friendly status messages

Do not rely on color alone to communicate payment/fee status.

---

# 41. Performance

Optimize:

* images
* dashboard queries
* table pagination
* component rendering
* bundle size

Use Next.js image optimization where appropriate.

Do not fetch thousands of students at once.

Do not poll APIs aggressively.

For asynchronous jobs, use reasonable polling intervals or a proper
backend status mechanism.

---

# 42. State Management

Do not introduce a global state library unless genuinely necessary.

Prefer:

* TanStack Query → server state
* React state → local UI state
* URL parameters → filters/search/pagination
* Auth provider/context → authentication state

If global client state becomes necessary, use a lightweight solution.

---

# 43. URL State

Admin filters should be reflected in URL query parameters where useful.

Example:

/admin/students?course=basic-computer&status=overdue&page=2

This allows:

* Refreshing without losing filters
* Browser back/forward
* Sharing filtered views
* Better debugging

---

# 44. Audit-Friendly UI

Where appropriate, display:

* Created date
* Updated date
* Updated by
* Payment timestamp
* Receipt timestamp
* Import timestamp

Do not expose sensitive internal audit information to students.

---

# 45. Mobile Student Experience

The student portal should prioritize mobile use.

The mobile navigation should provide:

Home
Fees
Receipts
Attendance
Profile

Make:

PAY NOW

highly visible when fees are outstanding.

---

# 46. Admin Tables

Admin tables must support:

* Search
* Pagination
* Sorting
* Filtering
* Column consistency
* Row actions
* Mobile-friendly fallback

On mobile, transform wide tables into cards or horizontally scrollable
sections where appropriate.

Do not squeeze 10 columns into an unreadable mobile table.

---

# 47. Notifications / Toasts

Use a consistent notification system.

Success:

"Student added successfully."

Error:

"Unable to save student."

Warning:

"Payment verification is still pending."

Never use browser alert().

---

# 48. API Error Contract

Frontend must consume the backend's standardized error format.

Do not build custom error parsing separately in every component.

Create one normalization layer.

---

# 49. Testing

Implement:

* Component tests
* Form validation tests
* Authentication tests
* Route protection tests
* API integration tests
* Payment UI tests
* CSV import UI tests
* Student CRUD tests
* Fee status tests

Critical payment scenarios:

1. Payment success
2. Payment failure
3. Payment pending
4. Duplicate callback
5. Backend verification failure
6. Receipt unavailable immediately
7. Network interruption

---

# 50. Visual Quality

The interface should feel like a real production academy management
product, not a generic dashboard template.

Use:

* strong typography
* clear hierarchy
* restrained shadows
* consistent spacing
* professional tables
* polished forms
* subtle transitions
* consistent iconography

Avoid:

* excessive cards
* random gradients
* unnecessary animations
* huge empty spaces
* decorative UI that competes with data

---

# 51. Development Rules

Claude Code must:

1. Inspect the existing repository before creating files.
2. Reuse existing working components where appropriate.
3. Follow backend.md and database.md.
4. Never invent API endpoints.
5. If an endpoint does not exist yet, create a clearly typed API abstraction
   and document the dependency rather than silently mocking production logic.
6. Never hardcode real student data.
7. Never hardcode credentials.
8. Never bypass backend authorization.
9. Never treat frontend payment state as authoritative.
10. Never use mock data in production paths.

Mocks may only exist in isolated tests/development fixtures.

---

# 52. Implementation Order

Build in this order:

PHASE 1
Frontend foundation

PHASE 2
Public website

PHASE 3
Authentication

PHASE 4
Admin shell/dashboard

PHASE 5
Student management

PHASE 6
Courses and batches

PHASE 7
Student portal

PHASE 8
Teacher portal

PHASE 9
Fees

PHASE 10
Razorpay payment UI

PHASE 11
Receipts

PHASE 12
Attendance

PHASE 13
Notifications

PHASE 14
CSV import interface

PHASE 15
ID-card generation interface

PHASE 16
Reports

PHASE 17
Responsive/accessibility hardening

PHASE 18
Testing/security/performance review

---

# 53. Anti-Loop / Debugging Rule

When an error occurs:

1. Capture the complete error.
2. Identify the failing layer.
3. Determine the root cause.
4. Make one focused correction.
5. Run the smallest relevant test.
6. If fixed, continue.
7. If not fixed, inspect the new evidence.

Never repeatedly run the same command without changing anything.

If the same error occurs twice without meaningful new diagnostic information:

STOP.

Report:

ERROR:
ROOT CAUSE:
ATTEMPTS:
CURRENT STATE:
WHAT IS REQUIRED:

Then continue working on independent parts that are not blocked.

---

# 54. Plugin / Skill Usage

Before implementing a major frontend phase, inspect available Claude Code
plugins/skills.

Prefer relevant skills for:

* Next.js
* React
* TypeScript
* UI/component architecture
* accessibility
* testing
* security
* code review
* debugging

Use:

* claude-code-setup
* everything-claude-code
* code-review
* claude-md-management

when relevant and available.

Do not blindly invoke every installed plugin.

Read the relevant skill instructions before applying them.

---

# 55. Definition of Done

Frontend is considered complete only when:

* Public website works.
* Authentication works.
* Role-based routing works.
* Admin dashboard works.
* Student management works.
* Teacher portal works.
* Student portal works.
* Courses/batches work.
* Fees work.
* Razorpay UI integrates with backend.
* Receipt access works.
* Attendance works.
* Notifications UI works.
* CSV import UI works.
* ID-card generation UI works.
* Reports work.
* Mobile layouts work.
* Accessibility issues are addressed.
* Loading/error/empty states exist.
* API errors are handled consistently.
* No secrets are exposed.
* Tests pass.
* Production build succeeds.
* No unnecessary mock data remains in production paths.

---

# 56. Claude Code Completion Report

After each phase, report:

PHASE:
STATUS:

Implemented:

* ...

API dependencies:

* ...

Tests:

* ...

Issues fixed:

* ...

Security checks:

* ...

Remaining:

* ...

Blocked by:

* ...

Next:

* ...

Do not claim a phase is complete if critical functionality is mocked,
broken, or dependent on an unimplemented backend endpoint.
