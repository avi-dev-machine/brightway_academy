import type { LoginRequest, MeOut } from "@/types/api";
import { apiRequest } from "./client";

/**
 * Auth calls go to the Next.js BFF (`/api/auth/*`), which talks to the backend and stores
 * tokens in httpOnly cookies. Tokens are never returned to or stored by browser code.
 */
export const authApi = {
  login: (payload: LoginRequest) =>
    apiRequest<{ user: MeOut }>("/api/auth/login", { method: "POST", body: payload, sameOrigin: true }).then(
      (r) => r.data.user,
    ),
  logout: () =>
    apiRequest<{ ok: boolean }>("/api/auth/logout", { method: "POST", sameOrigin: true }).then((r) => r.data),
  session: () =>
    apiRequest<{ user: MeOut }>("/api/auth/session", { sameOrigin: true }).then((r) => r.data.user),
};
