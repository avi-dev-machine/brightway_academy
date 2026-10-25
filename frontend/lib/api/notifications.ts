import type {
  Notification,
  NotificationListParams,
  UUID,
} from "@/types/api";
import { api } from "./client";

export const notificationsApi = {
  list: (params: NotificationListParams = {}) =>
    api.list<Notification>("/notifications", params),
  retry: (id: UUID) => api.post<Notification>(`/notifications/${id}/retry`),
};
