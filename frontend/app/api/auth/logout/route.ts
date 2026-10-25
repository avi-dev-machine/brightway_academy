import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth/server-session";

export async function POST() {
  await clearAuthCookies();
  return NextResponse.json({
    success: true,
    data: { ok: true },
  });
}
