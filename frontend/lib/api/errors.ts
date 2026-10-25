import type { ApiErrorBody } from "@/types/api";

/**
 * The single error-normalization layer for the whole frontend (spec §34, §48).
 * Every failure (backend envelope, proxy failure, network, timeout) becomes an ApiError
 * with a user-safe `message`. Components never parse raw responses themselves.
 */

export const ERROR_MESSAGES = {
  network: "Unable to connect to the server. Please try again.",
  timeout: "The server took too long to respond. Please try again.",
  unauthorized: "Your session has expired. Please sign in again.",
  forbidden: "You don't have permission to access this page.",
  notFound: "The requested record could not be found.",
  rateLimited: "Too many attempts. Please wait a minute and try again.",
  server: "Something went wrong on our side. Please try again shortly.",
  unavailable: "This service is temporarily unavailable. Please try again later.",
  validation: "Please check the highlighted fields.",
  paymentPending: "Your payment is being verified. Please check your payment history shortly.",
} as const;

export interface FieldErrorDetail {
  field: string;
  message: string;
  type?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: unknown;
  /** Field-level validation errors keyed by form field name (e.g. "name", "records.0.status"). */
  readonly fieldErrors: Record<string, string>;

  constructor(opts: {
    status: number;
    code: string;
    message: string;
    requestId?: string | null;
    details?: unknown;
  }) {
    super(opts.message);
    this.name = "ApiError";
    this.status = opts.status;
    this.code = opts.code;
    this.requestId = opts.requestId ?? null;
    this.details = opts.details;
    this.fieldErrors = extractFieldErrors(opts.details);
  }

  get isUnauthorized() {
    return this.status === 401;
  }
  get isForbidden() {
    return this.status === 403;
  }
  get isNotFound() {
    return this.status === 404;
  }
  get isValidation() {
    return this.status === 422 || this.code === "VALIDATION_ERROR";
  }
  get isNetwork() {
    return this.code === "NETWORK_ERROR" || this.code === "TIMEOUT";
  }
}

/** Backend validation details look like `[{field: "body.name", message, type}]`. */
export function extractFieldErrors(details: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!Array.isArray(details)) return out;
  for (const item of details) {
    if (!item || typeof item !== "object") continue;
    const { field, message } = item as Partial<FieldErrorDetail>;
    if (typeof field !== "string" || typeof message !== "string") continue;
    const key = field.replace(/^(body|query|path)\./, "");
    if (key && !(key in out)) out[key] = cleanValidationMessage(message);
  }
  return out;
}

function cleanValidationMessage(message: string): string {
  // Pydantic prefixes custom errors with "Value error, ".
  return message.replace(/^Value error,\s*/i, "");
}

/** Message shown to users for a given status when the backend message is not safe/available. */
export function fallbackMessage(status: number, code?: string): string {
  if (code === "NETWORK_ERROR" || code === "BACKEND_UNAVAILABLE") return ERROR_MESSAGES.network;
  if (code === "TIMEOUT") return ERROR_MESSAGES.timeout;
  if (status === 401) return ERROR_MESSAGES.unauthorized;
  if (status === 403) return ERROR_MESSAGES.forbidden;
  if (status === 404) return ERROR_MESSAGES.notFound;
  if (status === 422) return ERROR_MESSAGES.validation;
  if (status === 429) return ERROR_MESSAGES.rateLimited;
  if (status === 503) return ERROR_MESSAGES.unavailable;
  if (status >= 500) return ERROR_MESSAGES.server;
  return "The request could not be completed.";
}

/**
 * Build an ApiError from a backend error body. Backend 4xx messages are curated domain
 * messages ("Student was not found.") and safe to display; 5xx messages are replaced with
 * a generic message so internal details never reach the UI.
 */
export function errorFromBody(status: number, body: Partial<ApiErrorBody> | null | undefined) {
  const code = body?.code || httpCode(status);
  const safeBackendMessage =
    status < 500 && status !== 401 && typeof body?.message === "string" && body.message.trim()
      ? body.message
      : null;
  return new ApiError({
    status,
    code,
    message: safeBackendMessage ?? fallbackMessage(status, code),
    requestId: body?.request_id ?? null,
    details: body?.details,
  });
}

function httpCode(status: number): string {
  if (status === 401) return "UNAUTHORIZED";
  if (status === 403) return "FORBIDDEN";
  if (status === 404) return "NOT_FOUND";
  if (status === 422) return "VALIDATION_ERROR";
  if (status === 429) return "RATE_LIMITED";
  if (status >= 500) return "SERVER_ERROR";
  return "HTTP_ERROR";
}

/** Normalise anything thrown into an ApiError. */
export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof DOMException && (error.name === "TimeoutError" || error.name === "AbortError")) {
    return new ApiError({ status: 0, code: "TIMEOUT", message: ERROR_MESSAGES.timeout });
  }
  if (error instanceof TypeError) {
    // fetch() rejects with TypeError on network failure.
    return new ApiError({ status: 0, code: "NETWORK_ERROR", message: ERROR_MESSAGES.network });
  }
  return new ApiError({ status: 0, code: "UNKNOWN_ERROR", message: ERROR_MESSAGES.server });
}

/** Convenience for UI: always returns a displayable string. */
export function getErrorMessage(error: unknown): string {
  return normalizeError(error).message;
}
