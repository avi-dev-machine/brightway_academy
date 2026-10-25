import type {
  AcademySettings,
  AllSettings,
  AuditLog,
  AuditLogParams,
  FeeSettings,
  InviteUserRequest,
  LinkUserRequest,
  NotificationSettings,
  SetupStatus,
  SystemStatus,
  UpdateUserRequest,
  UserListParams,
  UserProfile,
  UUID,
} from "@/types/api";
import { api } from "./client";

export const adminApi = {
  getSetupStatus: () => api.get<SetupStatus>("/admin/setup"),
  completeSetup: () => api.post<SetupStatus>("/admin/setup/complete"),
  getAllSettings: () => api.get<AllSettings>("/admin/settings"),
  updateAcademySettings: (payload: AcademySettings) =>
    api.put<AcademySettings>("/admin/settings/academy", payload),
  updateFeeSettings: (payload: FeeSettings) =>
    api.put<FeeSettings>("/admin/settings/fees", payload),
  updateNotificationSettings: (payload: NotificationSettings) =>
    api.put<NotificationSettings>("/admin/settings/notifications", payload),
  getSystemStatus: () => api.get<SystemStatus>("/admin/system/status"),

  listUsers: (params: UserListParams = {}) =>
    api.list<UserProfile>("/admin/users", params),
  linkUser: (payload: LinkUserRequest) => api.post<UserProfile>("/admin/users/link", payload),
  inviteUser: (payload: InviteUserRequest) =>
    api.post<UserProfile>("/admin/users/invite", payload),
  updateUser: (userId: UUID, payload: UpdateUserRequest) =>
    api.patch<UserProfile>(`/admin/users/${userId}`, payload),

  listAuditLogs: (params: AuditLogParams = {}) =>
    api.list<AuditLog>("/admin/audit-logs", params),
};
