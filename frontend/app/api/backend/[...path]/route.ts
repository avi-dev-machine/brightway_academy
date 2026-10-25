import { type NextRequest, NextResponse } from "next/server";
import { getValidAccessToken } from "@/lib/auth/server-session";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

const SAFE_SEGMENT_RE = /^[a-zA-Z0-9_.-]+$/;
const SAFE_IDEMPOTENCY_RE = /^[a-zA-Z0-9_.:-]{1,128}$/;

async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  if (!Array.isArray(path) || path.length === 0) {
    return NextResponse.json(
      { success: false, error: { code: "INVALID_PATH", message: "Invalid API route path." } },
      { status: 400 },
    );
  }

  // Defend against path traversal: every path segment must be strictly alphanumeric/dash/dot/underscore
  for (const segment of path) {
    if (!SAFE_SEGMENT_RE.test(segment) || segment === "." || segment === "..") {
      return NextResponse.json(
        { success: false, error: { code: "INVALID_PATH", message: "Disallowed path characters detected." } },
        { status: 400 },
      );
    }
  }

  const backendPath = path.join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${API_BASE_URL}/api/v1/${backendPath}${search}`;

  // SSRF defense: ensure target URL strictly matches backend origin
  try {
    const targetObj = new URL(targetUrl);
    const baseObj = new URL(API_BASE_URL);
    if (targetObj.origin !== baseObj.origin || !targetObj.pathname.startsWith("/api/v1/")) {
      return NextResponse.json(
        { success: false, error: { code: "FORBIDDEN_TARGET", message: "Target URL disallowed." } },
        { status: 403 },
      );
    }
  } catch {
    return NextResponse.json(
      { success: false, error: { code: "MALFORMED_URL", message: "Malformed backend URL." } },
      { status: 400 },
    );
  }

  const token = await getValidAccessToken();

  const reqHeaders = new Headers();
  // Pass allowed incoming headers
  const allowedHeaders = ["content-type", "accept", "idempotency-key", "cache-control"];
  request.headers.forEach((value, key) => {
    const lowerKey = key.toLowerCase();
    if (allowedHeaders.includes(lowerKey)) {
      if (lowerKey === "idempotency-key" && !SAFE_IDEMPOTENCY_RE.test(value)) {
        return; // drop malformed idempotency keys
      }
      reqHeaders.set(key, value);
    }
  });

  if (token) {
    reqHeaders.set("Authorization", `Bearer ${token}`);
  }

  const reqInit: RequestInit = {
    method: request.method,
    headers: reqHeaders,
  };

  // Only attach body for methods that allow it
  if (["POST", "PUT", "PATCH"].includes(request.method)) {
    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("multipart/form-data")) {
      // Stream formData or arrayBuffer
      reqInit.body = await request.arrayBuffer();
    } else {
      const text = await request.text();
      if (text) {
        reqInit.body = text;
      }
    }
  }

  try {
    const backendRes = await fetch(targetUrl, reqInit);

    // Forward response headers (e.g. content-type, content-disposition for file downloads)
    const resHeaders = new Headers();
    const forwardHeaders = [
      "content-type",
      "content-disposition",
      "cache-control",
      "x-request-id",
    ];
    backendRes.headers.forEach((value, key) => {
      if (forwardHeaders.includes(key.toLowerCase())) {
        resHeaders.set(key, value);
      }
    });

    // Stream the body back
    return new NextResponse(backendRes.body, {
      status: backendRes.status,
      headers: resHeaders,
    });
  } catch (err) {
    console.error("Backend proxy error:", err);
    return NextResponse.json(
      {
        success: false,
        error: {
          code: "BACKEND_UNAVAILABLE",
          message: "Unable to connect to the backend server. Please try again.",
        },
      },
      { status: 503 },
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
