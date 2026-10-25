import { type NextRequest, NextResponse } from "next/server";
import { ACCESS_COOKIE, USER_COOKIE } from "@/lib/auth/server-session";
import type { Role } from "@/types/api";

interface CachedUser {
  role: Role;
}

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Only check protected routes and login
  const isProtected =
    pathname.startsWith("/admin") ||
    pathname.startsWith("/teacher") ||
    pathname.startsWith("/student");
  const isLogin = pathname === "/login";

  if (!isProtected && !isLogin) {
    return NextResponse.next();
  }

  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  const userJson = request.cookies.get(USER_COOKIE)?.value;

  let userRole: Role | null = null;
  if (userJson) {
    try {
      const parsed: CachedUser = JSON.parse(userJson);
      userRole = parsed.role;
    } catch {
      userRole = null;
    }
  }

  const isAuthenticated = !!token && !!userRole;

  // If on /login and already logged in, redirect to their home portal
  if (isLogin && isAuthenticated && userRole) {
    const destination =
      userRole === "ADMIN" ? "/admin" : userRole === "TEACHER" ? "/teacher" : "/student";
    return NextResponse.redirect(new URL(destination, request.url));
  }

  // If on protected page and not logged in, redirect to /login
  if (isProtected && !isAuthenticated) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // If on protected page, check role match
  if (isProtected && userRole) {
    if (pathname.startsWith("/admin") && userRole !== "ADMIN") {
      const target = userRole === "TEACHER" ? "/teacher" : "/student";
      return NextResponse.redirect(new URL(target, request.url));
    }
    if (pathname.startsWith("/teacher") && userRole !== "TEACHER" && userRole !== "ADMIN") {
      return NextResponse.redirect(new URL("/student", request.url));
    }
    if (pathname.startsWith("/student") && userRole !== "STUDENT" && userRole !== "ADMIN") {
      return NextResponse.redirect(new URL("/teacher", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/teacher/:path*",
    "/student/:path*",
    "/login",
  ],
};
