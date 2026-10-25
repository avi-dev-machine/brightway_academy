import { cookies } from "next/headers";
import type { MeOut, TokenOut } from "@/types/api";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

export const ACCESS_COOKIE = "bw_access_token";
export const REFRESH_COOKIE = "bw_refresh_token";
export const USER_COOKIE = "bw_user";

export interface SessionData {
  user: MeOut | null;
  accessToken: string | null;
}

export async function setAuthCookies(tokens: TokenOut, user: MeOut) {
  const cookieStore = await cookies();
  const isProd = process.env.NODE_ENV === "production";

  cookieStore.set(ACCESS_COOKIE, tokens.access_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: tokens.expires_in || 3600,
  });

  if (tokens.refresh_token) {
    cookieStore.set(REFRESH_COOKIE, tokens.refresh_token, {
      httpOnly: true,
      secure: isProd,
      sameSite: "lax",
      path: "/",
      maxAge: 30 * 24 * 3600, // 30 days
    });
  }

  cookieStore.set(USER_COOKIE, JSON.stringify(user), {
    httpOnly: false, // Accessible to client for instant UI/role hints, non-authoritative
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: 30 * 24 * 3600,
  });
}

export async function clearAuthCookies() {
  const cookieStore = await cookies();
  cookieStore.delete(ACCESS_COOKIE);
  cookieStore.delete(REFRESH_COOKIE);
  cookieStore.delete(USER_COOKIE);
}

export async function getValidAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(ACCESS_COOKIE)?.value;
  if (token) return token;

  const refreshToken = cookieStore.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) {
      await clearAuthCookies();
      return null;
    }
    const data = await res.json();
    if (!data.success || !data.data) {
      await clearAuthCookies();
      return null;
    }
    const tokens: TokenOut = data.data;

    // Fetch user profile with the new token
    const meRes = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });
    if (meRes.ok) {
      const meData = await meRes.json();
      if (meData.success && meData.data) {
        await setAuthCookies(tokens, meData.data);
      }
    }

    return tokens.access_token;
  } catch {
    return null;
  }
}

export async function getServerUser(): Promise<MeOut | null> {
  const token = await getValidAccessToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.success ? data.data : null;
  } catch {
    return null;
  }
}
