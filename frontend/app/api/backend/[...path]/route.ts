import { type NextRequest, NextResponse } from "next/server";
import { getValidAccessToken } from "@/lib/auth/server-session";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const backendPath = path.join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${API_BASE_URL}/api/v1/${backendPath}${search}`;

  const token = await getValidAccessToken();

  const reqHeaders = new Headers();
  // Pass allowed incoming headers
  const allowedHeaders = ["content-type", "accept", "idempotency-key", "cache-control"];
  request.headers.forEach((value, key) => {
    if (allowedHeaders.includes(key.toLowerCase())) {
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
