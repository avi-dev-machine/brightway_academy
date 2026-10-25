import { NextResponse } from "next/server";
import { setAuthCookies } from "@/lib/auth/server-session";
import type { LoginRequest, MeOut, TokenOut } from "@/types/api";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const body: LoginRequest = await request.json();

    const loginRes = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const loginJson = await loginRes.json();
    if (!loginRes.ok || !loginJson.success) {
      return NextResponse.json(
        loginJson,
        { status: loginRes.status || 400 },
      );
    }

    const tokens: TokenOut = loginJson.data;

    // Get the user profile using the access token
    const meRes = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });
    const meJson = await meRes.json();

    if (!meRes.ok || !meJson.success) {
      return NextResponse.json(
        { success: false, error: { code: "AUTH_PROFILE_FAILED", message: "Failed to retrieve user profile." } },
        { status: 500 },
      );
    }

    const user: MeOut = meJson.data;
    await setAuthCookies(tokens, user);

    return NextResponse.json({
      success: true,
      data: { user },
    });
  } catch {
    return NextResponse.json(
      {
        success: false,
        error: { code: "SERVER_ERROR", message: "Unable to process sign in request." },
      },
      { status: 500 },
    );
  }
}
