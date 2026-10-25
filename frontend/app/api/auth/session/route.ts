import { NextResponse } from "next/server";
import { getServerUser } from "@/lib/auth/server-session";

export async function GET() {
  const user = await getServerUser();
  if (!user) {
    return NextResponse.json(
      { success: false, error: { code: "UNAUTHORIZED", message: "Not signed in" } },
      { status: 401 },
    );
  }

  return NextResponse.json({
    success: true,
    data: { user },
  });
}
