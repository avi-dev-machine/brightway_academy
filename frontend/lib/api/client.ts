import type { ApiEnvelope, PageMeta, Paginated } from "@/types/api";
import { ApiError, ERROR_MESSAGES, errorFromBody, normalizeError } from "./errors";

/**
 * Centralised API client (spec §30).
 *
 * The browser never talks to FastAPI directly and never sees an access token: every call
 * goes to the same-origin BFF at `/api/backend/*`, which attaches the bearer token from an
 * httpOnly cookie, transparently refreshes it, and forwards to `${API_BASE_URL}/api/v1/*`.
 */

export const API_PROXY_PREFIX = "/api/backend";
const DEFAULT_TIMEOUT_MS = 30_000;

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue>;

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  query?: QueryParams | object;
  body?: unknown;
  formData?: FormData;
  headers?: Record<string, string>;
  timeoutMs?: number;
  signal?: AbortSignal;
  /** Treat `path` as a same-origin URL (e.g. `/api/auth/login`) instead of a backend path. */
  sameOrigin?: boolean;
}

export interface ApiResult<T> {
  data: T;
  meta: PageMeta | null;
}

/** Build a query string, dropping empty values. */
export function toQueryString(query?: QueryParams | object): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query as QueryParams)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

/** Same-origin URL for a backend path; use for <img src>, downloads and previews. */
export function backendUrl(path: string, query?: QueryParams): string {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${API_PROXY_PREFIX}${clean}${toQueryString(query)}`;
}

/** Notifies the auth provider when the session can no longer be refreshed. */
export const UNAUTHORIZED_EVENT = "bw:unauthorized";

function emitUnauthorized() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
}

async function parseEnvelope<T>(response: Response): Promise<ApiResult<T>> {
  const contentType = response.headers.get("content-type") ?? "";
  let payload: ApiEnvelope<T> | null = null;
  if (contentType.includes("application/json")) {
    try {
      payload = (await response.json()) as ApiEnvelope<T>;
    } catch {
      payload = null;
    }
  }

  if (!response.ok || !payload || payload.success === false) {
    const body = payload && payload.success === false ? payload.error : null;
    const error = errorFromBody(response.status || 500, body);
    if (error.isUnauthorized) emitUnauthorized();
    throw error;
  }

  const meta = isPageMeta(payload.meta) ? payload.meta : null;
  return { data: payload.data, meta };
}

function isPageMeta(meta: unknown): meta is PageMeta {
  return (
    !!meta &&
    typeof meta === "object" &&
    "total" in meta &&
    "page" in meta &&
    "page_size" in meta
  );
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
  const { method = "GET", query, body, formData, headers = {}, timeoutMs = DEFAULT_TIMEOUT_MS } = options;

  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const signal = options.signal ? AbortSignal.any([options.signal, timeoutSignal]) : timeoutSignal;

  const init: RequestInit = {
    method,
    headers: { Accept: "application/json", ...headers },
    credentials: "same-origin",
    cache: "no-store",
    signal,
  };
  if (formData) {
    init.body = formData;
  } else if (body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let response: Response;
  try {
    const url = options.sameOrigin
      ? `${path}${toQueryString(query)}`
      : backendUrl(path, query as QueryParams);
    response = await fetch(url, init);
  } catch (error) {
    // Distinguish our timeout from a caller-initiated abort.
    if (timeoutSignal.aborted) {
      throw new ApiError({ status: 0, code: "TIMEOUT", message: ERROR_MESSAGES.timeout });
    }
    throw normalizeError(error);
  }
  return parseEnvelope<T>(response);
}

/** Thin helpers so domain modules read cleanly. */
export const api = {
  get: <T>(path: string, query?: RequestOptions["query"], opts?: RequestOptions) =>
    apiRequest<T>(path, { ...opts, method: "GET", query }).then((r) => r.data),
  list: <T>(path: string, query?: RequestOptions["query"], opts?: RequestOptions) =>
    apiRequest<T[]>(path, { ...opts, method: "GET", query }).then(
      (r): Paginated<T> => ({
        items: r.data,
        meta: r.meta ?? { page: 1, page_size: r.data.length, total: r.data.length, total_pages: 1 },
      }),
    ),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    apiRequest<T>(path, { ...opts, method: "POST", body }).then((r) => r.data),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    apiRequest<T>(path, { ...opts, method: "PUT", body }).then((r) => r.data),
  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    apiRequest<T>(path, { ...opts, method: "PATCH", body }).then((r) => r.data),
  delete: <T>(path: string, opts?: RequestOptions) =>
    apiRequest<T>(path, { ...opts, method: "DELETE" }).then((r) => r.data),
};

/**
 * Multipart upload with progress (fetch() cannot report upload progress).
 * Resolves with the envelope's `data`; rejects with a normalised ApiError.
 */
export function uploadWithProgress<T>(
  path: string,
  formData: FormData,
  opts: { method?: "POST" | "PUT"; onProgress?: (percent: number) => void; timeoutMs?: number } = {},
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(opts.method ?? "POST", backendUrl(path));
    xhr.setRequestHeader("Accept", "application/json");
    xhr.timeout = opts.timeoutMs ?? 120_000;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) opts.onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      let payload: ApiEnvelope<T> | null = null;
      try {
        payload = JSON.parse(xhr.responseText) as ApiEnvelope<T>;
      } catch {
        payload = null;
      }
      if (xhr.status >= 200 && xhr.status < 300 && payload?.success) {
        resolve(payload.data);
        return;
      }
      const error = errorFromBody(xhr.status || 500, payload && !payload.success ? payload.error : null);
      if (error.isUnauthorized) emitUnauthorized();
      reject(error);
    };
    xhr.onerror = () =>
      reject(new ApiError({ status: 0, code: "NETWORK_ERROR", message: ERROR_MESSAGES.network }));
    xhr.ontimeout = () =>
      reject(new ApiError({ status: 0, code: "TIMEOUT", message: ERROR_MESSAGES.timeout }));
    xhr.send(formData);
  });
}

/** Stable idempotency key for retry-safe POSTs (payments, offline payments). */
export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
