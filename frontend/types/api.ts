/**
 * Types mirroring the FastAPI backend's OpenAPI schemas (backend/app/schemas, app/models).
 * Money is always integer paise. Dates are ISO strings ("YYYY-MM-DD" / RFC 3339).
 * Keep this file in sync with the backend; do not add fields the backend does not return.
 */

export type UUID = string;
export type ISODate = string;
export type ISODateTime = string;

/* ----------------------------------------------------------------- envelope */

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ApiSuccess<T> {
  success: true;
  data: T;
  meta?: PageMeta | Record<string, unknown> | null;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  request_id?: string | null;
  details?: unknown;
}

export interface ApiFailure {
  success: false;
  error: ApiErrorBody;
}

export type ApiEnvelope<T> = ApiSuccess<T> | ApiFailure;

export interface Paginated<T> {
  items: T[];
  meta: PageMeta;
}

export interface PageParams {
  page?: number;
  page_size?: number;
}

/* --------------------------------------------------------------------- auth */

export type Role = "ADMIN" | "TEACHER" | "STUDENT";

export interface TokenOut {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in: number;
  user_id: UUID;
}

export interface MeOut {
  user_id: UUID;
  email: string | null;
  role: Role;
  student_id: UUID | null;
  teacher_id: UUID | null;
  display_name: string | null;
}

export interface LoginRequest {
  identifier?: string;
  email?: string;
  password: string;
}

/* ----------------------------------------------------------------- students */

export type StudentStatus = "active" | "inactive";

export interface Student {
  id: UUID;
  id_no: string | null;
  name: string;
  guardian_name: string | null;
  address: string | null;
  contact: string | null;
  contact_e164: string | null;
  course_id: UUID | null;
  course_name?: string | null;
  legacy_course: string | null;
  admission_date: ISODate | null;
  status: StudentStatus;
  program?: "CERTIFICATE" | "NON_CERTIFICATE" | null;
  monthly_fee_paise?: number | null;
  fee_notes?: string | null;
  initial_passcode?: string | null;
  issues?: string[] | null;
  import_job_id: UUID | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  has_photo: boolean;
  has_id_card: boolean;
  current_month_status?: "PAID" | "UNPAID" | null;
  unpaid_months?: string[] | null;
  due_months_count?: number;
  total_due_paise?: number;
}

export interface StudentMonthlyFee {
  id: UUID;
  student_id: UUID;
  period: ISODate;
  period_label: string;
  amount_paise: number | null;
  status: "PAID" | "PENDING" | "CLOSED" | "ABSENT";
  paid_on: ISODate | null;
  raw_entry: string | null;
  note: string | null;
  pending_paise: number | null;
  created_at: ISODateTime;
}

export interface StudentCreate {
  id_no?: string | null;
  name: string;
  guardian_name?: string | null;
  address?: string | null;
  contact?: string | null;
  course_id?: UUID | null;
  admission_date?: ISODate | null;
}

export interface StudentUpdate {
  id_no?: string | null;
  name?: string;
  guardian_name?: string | null;
  address?: string | null;
  contact?: string | null;
  course_id?: UUID | null;
  admission_date?: ISODate | null;
  status?: StudentStatus | null;
  program?: "CERTIFICATE" | "NON_CERTIFICATE" | null;
  monthly_fee_paise?: number | null;
  fee_notes?: string | null;
  initial_passcode?: string | null;
}

export interface DueFeeNoticeResult {
  student_id: UUID;
  student_name: string;
  contact?: string | null;
  contact_e164?: string | null;
  amount_paise: number;
  amount_formatted: string;
  unpaid_months: string[];
  message_text: string;
  whatsapp_url?: string | null;
  queued: boolean;
  notification_id?: UUID | null;
}

export interface BroadcastDueNoticeRequest {
  program?: "CERTIFICATE" | "NON_CERTIFICATE" | null;
  course_id?: UUID | null;
  custom_note?: string | null;
}

export interface BroadcastDueNoticeResult {
  total_unpaid: number;
  queued_count: number;
  skipped_no_contact: number;
  message: string;
  notified_students: DueFeeNoticeResult[];
}

export interface StudentListParams extends PageParams {
  q?: string;
  course_id?: UUID;
  batch_id?: UUID;
  status?: StudentStatus;
  program?: string;
  has_id?: boolean;
  fee_status?: "UNPAID" | "PAID";
}

export interface StudentPhotoResult {
  student: Student;
  id_card_generated: boolean;
  id_card_error?: string | null;
}


/* ------------------------------------------------------------------ courses */

export interface Course {
  id: UUID;
  code: string;
  name: string;
  description: string | null;
  duration_months: number | null;
  default_fee_paise: number | null;
  active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface CourseCreate {
  code: string;
  name: string;
  description?: string | null;
  duration_months?: number | null;
  default_fee_paise?: number | null;
}

export type CourseUpdate = Partial<Omit<CourseCreate, "code">> & { active?: boolean | null };

export interface CourseListParams extends PageParams {
  active?: boolean;
  q?: string;
}

/* ------------------------------------------------------------------ batches */

export interface Batch {
  id: UUID;
  course_id: UUID;
  course_name?: string | null;
  name: string;
  teacher_id: UUID | null;
  teacher_name?: string | null;
  start_date: ISODate | null;
  end_date: ISODate | null;
  schedule: string | null;
  capacity: number | null;
  active: boolean;
  student_count?: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface BatchCreate {
  course_id: UUID;
  name: string;
  teacher_id?: UUID | null;
  start_date?: ISODate | null;
  end_date?: ISODate | null;
  schedule?: string | null;
  capacity?: number | null;
}

export type BatchUpdate = Partial<Omit<BatchCreate, "course_id">> & { active?: boolean | null };

export interface BatchListParams extends PageParams {
  course_id?: UUID;
  teacher_id?: UUID;
  active?: boolean;
}

export interface BatchAssignmentResult {
  added: UUID[];
  already_assigned: UUID[];
}

/* ----------------------------------------------------------------- teachers */

export interface Teacher {
  id: UUID;
  name: string;
  phone: string | null;
  email: string | null;
  active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface TeacherCreate {
  name: string;
  phone?: string | null;
  email?: string | null;
}

export type TeacherUpdate = Partial<TeacherCreate> & { active?: boolean | null };

export interface TeacherListParams extends PageParams {
  active?: boolean;
  q?: string;
}

/* --------------------------------------------------------------------- fees */

export type FeeStatus = "PENDING" | "PARTIALLY_PAID" | "PAID" | "OVERDUE" | "CANCELLED";
export type FeeType = "MONTHLY" | "INSTALLMENT" | "ONE_TIME";

export interface Fee {
  id: UUID;
  student_id: UUID;
  fee_plan_id: UUID | null;
  fee_type: FeeType;
  title: string;
  installment_no: number | null;
  amount_paise: number;
  concession_paise: number;
  paid_paise: number;
  due_date: ISODate;
  status: FeeStatus;
  concession_reason: string | null;
  cancellation_reason: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  balance_paise: number;
}

export interface FeeListParams extends PageParams {
  student_id?: UUID;
  status?: FeeStatus;
}

export interface FeeCreate {
  student_id: UUID;
  title: string;
  amount_paise: number;
  due_date: ISODate;
  fee_type?: FeeType;
}

export interface FeeSummary {
  student_id: UUID;
  total_amount_paise: number;
  total_concession_paise: number;
  total_paid_paise: number;
  total_outstanding_paise: number;
  overdue_count: number;
  overdue_paise: number;
}

export interface FeePlan {
  id: UUID;
  name: string;
  course_id: UUID | null;
  plan_type: FeeType;
  amount_paise: number;
  installment_count: number;
  active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface FeePlanCreate {
  name: string;
  course_id?: UUID | null;
  plan_type: FeeType;
  amount_paise: number;
  installment_count?: number;
}

export interface FeePlanUpdate {
  name?: string | null;
  active?: boolean | null;
}

export interface AssignPlanRequest {
  fee_plan_id: UUID;
  start_date: ISODate;
}

export interface ConcessionRequest {
  amount_paise: number;
  reason: string;
}

export interface CancelFeeRequest {
  reason: string;
}

export type OfflineMethod = "CASH" | "UPI" | "BANK_TRANSFER" | "CHEQUE" | "CARD" | "OTHER";

export interface OfflinePaymentRequest {
  amount_paise: number;
  method: OfflineMethod;
  reference?: string | null;
  notes?: string | null;
  paid_on?: ISODate | null;
  idempotency_key?: string | null;
}

/* ----------------------------------------------------------------- payments */

export type PaymentStatus = "CREATED" | "PENDING" | "SUCCESS" | "FAILED" | "REFUNDED";
export type PaymentProviderName = "RAZORPAY" | "MOCK" | "OFFLINE";

export interface Payment {
  id: UUID;
  fee_id: UUID;
  student_id: UUID;
  amount_paise: number;
  currency: string;
  provider: PaymentProviderName;
  method: string | null;
  status: PaymentStatus;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  reference: string | null;
  notes: string | null;
  failure_reason: string | null;
  requires_review: boolean;
  review_reason: string | null;
  paid_at: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface PaymentListParams extends PageParams {
  student_id?: UUID;
  fee_id?: UUID;
  status?: PaymentStatus;
}

export interface PaymentConfig {
  provider: string;
  key_id: string;
  currency: string;
}

export interface CreateOrderRequest {
  fee_id: UUID;
  amount_paise?: number | null;
}

export interface CheckoutOrder {
  payment_id: UUID;
  provider: string;
  provider_order_id: string;
  amount_paise: number;
  currency: string;
  key_id: string;
  fee_title: string;
  student_name: string;
  contact: string | null;
}

export interface VerifyPaymentRequest {
  provider_order_id: string;
  provider_payment_id: string;
  signature: string;
}

/** Settlement outcomes from backend PaymentService.Outcome. */
export type PaymentOutcome =
  | "SUCCEEDED"
  | "ALREADY_PROCESSED"
  | "PENDING"
  | "FAILED"
  | "REFUNDED"
  | "AMOUNT_MISMATCH"
  | "ORDER_MISMATCH"
  | "REVIEW_REQUIRED"
  | "IGNORED";

export interface PaymentResult {
  payment: Payment;
  receipt: Receipt | null;
  outcome: PaymentOutcome | string;
}

/* ----------------------------------------------------------------- receipts */

export interface Receipt {
  id: UUID;
  receipt_number: string;
  payment_id: UUID;
  student_id: UUID;
  fee_id: UUID;
  amount_paise: number;
  issued_at: ISODateTime;
  created_at: ISODateTime;
  has_pdf: boolean;
}

export interface ReceiptListParams extends PageParams {
  student_id?: UUID;
}

/* --------------------------------------------------------------- attendance */

export type AttendanceStatus = "PRESENT" | "ABSENT" | "LATE" | "EXCUSED";

export interface AttendanceEntry {
  student_id: UUID;
  status: AttendanceStatus;
  remarks?: string | null;
}

export interface MarkAttendanceRequest {
  attendance_date: ISODate;
  records: AttendanceEntry[];
}

export interface AttendanceRecord {
  id: UUID;
  batch_id: UUID;
  student_id: UUID;
  attendance_date: ISODate;
  status: AttendanceStatus;
  remarks: string | null;
  marked_by: UUID | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface RosterEntry {
  student_id: UUID;
  id_no: string;
  name: string;
  status: AttendanceStatus | null;
  remarks: string | null;
}

export interface AttendanceSummary {
  student_id: UUID;
  date_from: ISODate;
  date_to: ISODate;
  present: number;
  late: number;
  absent: number;
  excused: number;
  total: number;
  percentage: number | null;
}

export interface StudentAttendance {
  summary: AttendanceSummary;
  records: AttendanceRecord[];
}

export interface BatchReportRow {
  student_id: UUID;
  id_no: string;
  name: string;
  present: number;
  late: number;
  absent: number;
  excused: number;
  percentage: number | null;
}

export interface DateRange {
  date_from?: ISODate;
  date_to?: ISODate;
}

/* ------------------------------------------------------------ notifications */

export type NotificationChannel = "WHATSAPP" | "SMS" | "EMAIL";
export type NotificationStatus = "QUEUED" | "SENDING" | "SENT" | "DELIVERED" | "FAILED";

export interface Notification {
  id: UUID;
  student_id: UUID | null;
  fee_id: UUID | null;
  payment_id: UUID | null;
  channel: NotificationChannel;
  recipient: string;
  template: string;
  payload: Record<string, unknown>;
  status: NotificationStatus;
  provider_message_id: string | null;
  attempts: number;
  max_attempts: number;
  next_attempt_at: ISODateTime;
  last_error: string | null;
  dedupe_key: string | null;
  sent_at: ISODateTime | null;
  delivered_at: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface NotificationListParams extends PageParams {
  status?: NotificationStatus;
  channel?: NotificationChannel;
  student_id?: UUID;
}

/* ------------------------------------------------------------------ imports */

export type ImportJobStatus = "PREVIEWED" | "COMPLETED" | "FAILED";
export type ImportErrorPolicy = "STRICT" | "SKIP_ERRORS";
export type ImportRowStatus = "VALID" | "WARNING" | "ERROR" | "DUPLICATE" | "EXISTS";
export type ImportRowOutcome = "IMPORTED" | "SKIPPED";

/** Preview summary keys written by backend csv_import_service. Confirm adds result keys. */
export interface ImportSummary {
  total_rows?: number;
  status_counts?: Partial<Record<ImportRowStatus, number>>;
  importable_rows?: number;
  blank_rows_ignored?: number;
  extra_columns?: string[];
  unmapped_courses?: { course: string; rows: number }[];
  previously_imported_job_id?: string | null;
  imported?: number;
  skipped_existing?: number;
  skipped_duplicates?: number;
  skipped_errors?: number;
  [key: string]: unknown;
}

export interface ImportJob {
  id: UUID;
  filename: string;
  file_sha256: string;
  status: ImportJobStatus;
  total_rows: number;
  summary: ImportSummary;
  error_policy: ImportErrorPolicy | null;
  created_by: UUID | null;
  confirmed_by: UUID | null;
  confirmed_at: ISODateTime | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface ImportMessage {
  level?: "warning" | "error" | string;
  code?: string;
  message?: string;
  [key: string]: unknown;
}

export interface ImportRow {
  id: UUID;
  job_id: UUID;
  row_number: number;
  raw: Record<string, unknown>;
  normalized: Record<string, unknown> | null;
  status: ImportRowStatus;
  messages: ImportMessage[];
  outcome: ImportRowOutcome | null;
  student_id: UUID | null;
}

export interface ImportPreview {
  job: ImportJob;
  problem_rows: ImportRow[];
}

export interface ImportConfirmRequest {
  error_policy?: ImportErrorPolicy;
  course_mapping?: Record<string, UUID>;
  create_missing_courses?: boolean;
}

/* ----------------------------------------------------------------- id cards */

export interface IdCardLayout {
  width_mm: number;
  height_mm: number;
  background_color?: string;
  elements: Record<string, unknown>[];
}

export interface IdCardTemplate {
  id: UUID;
  name: string;
  layout: IdCardLayout;
  is_default: boolean;
  active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface TemplateCreate {
  name: string;
  layout: IdCardLayout;
  is_default?: boolean;
}

export interface TemplateUpdate {
  name?: string | null;
  layout?: IdCardLayout | null;
  is_default?: boolean | null;
  active?: boolean | null;
}

export interface GenerateIdCardRequest {
  template_id?: UUID | null;
}

export interface IdCard {
  id: UUID;
  student_id: UUID;
  template_id: UUID;
  generated_by: UUID | null;
  generated_at: ISODateTime;
}

/* ------------------------------------------------------------------ reports */

export interface CourseCount {
  course_id: UUID | null;
  course_name: string;
  count: number;
}

export interface DashboardStats {
  students_active: number;
  students_inactive: number;
  students_total: number;
  students_by_course: CourseCount[];
  fees_outstanding_paise: number;
  fees_overdue_paise: number;
  fees_overdue_count: number;
  collected_today_paise: number;
  payments_today: number;
  collected_this_month_paise: number;
  attendance_today_marked: number;
  attendance_today_attended: number;
}

export interface CollectionRow {
  day: ISODate;
  provider: string;
  method: string;
  count: number;
  amount_paise: number;
}

export interface CollectionReport {
  date_from: ISODate;
  date_to: ISODate;
  rows: CollectionRow[];
  total_count: number;
  total_paise: number;
}

export interface OutstandingRow {
  student_id: UUID;
  id_no: string;
  name: string;
  contact: string | null;
  course_name: string | null;
  outstanding_paise: number;
  overdue_paise: number;
  oldest_due_date: ISODate;
}

/* -------------------------------------------------------------------- admin */

export interface AcademySettings {
  name?: string;
  address?: string;
  phone?: string;
  email?: string;
  student_id_prefix?: string;
  receipt_prefix?: string;
}

export interface FeeSettings {
  reminder_offsets_days?: number[];
}

export interface NotificationSettings {
  channels?: NotificationChannel[];
  fee_reminders_enabled?: boolean;
  payment_confirmations_enabled?: boolean;
}

export interface SetupState {
  completed?: boolean;
  completed_at?: ISODateTime | null;
}

export interface AllSettings {
  academy: AcademySettings;
  fees: FeeSettings;
  notifications: NotificationSettings;
  setup: SetupState;
}

export interface SetupStatus {
  academy_configured: boolean;
  admin_exists: boolean;
  students_count: number;
  completed_imports: number;
  default_id_card_template: boolean;
  fee_plans_count: number;
  notification_channels_available: string[];
  setup_completed: boolean;
  completed_at: ISODateTime | null;
}

export interface SystemStatus {
  app_env: string;
  payment_provider: string;
  razorpay_webhook_configured: boolean;
  storage_backend: string;
  supabase_admin_configured: boolean;
  notification_channels: string[];
  notification_providers: Record<string, string>;
  whatsapp_provider: string;
  whatsapp_configured: boolean;
  sms_configured: boolean;
}

export interface UserProfile {
  user_id: UUID;
  email: string | null;
  role: Role;
  student_id: UUID | null;
  teacher_id: UUID | null;
  active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface UserListParams extends PageParams {
  role?: Role;
  active?: boolean;
}

export interface InviteUserRequest {
  email: string;
  role: Role;
  student_id?: UUID | null;
  teacher_id?: UUID | null;
}

export interface LinkUserRequest {
  user_id?: UUID | null;
  email?: string | null;
  role: Role;
  student_id?: UUID | null;
  teacher_id?: UUID | null;
}

export interface UpdateUserRequest {
  active?: boolean | null;
  role?: Role | null;
  student_id?: UUID | null;
  teacher_id?: UUID | null;
}

export interface AuditLog {
  id: UUID;
  actor_user_id: UUID | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  request_id: string | null;
  created_at: ISODateTime;
}

export interface AuditLogParams extends PageParams {
  entity_type?: string;
  entity_id?: string;
  actor_user_id?: UUID;
  action?: string;
}

export interface MessageOut {
  message: string;
}
