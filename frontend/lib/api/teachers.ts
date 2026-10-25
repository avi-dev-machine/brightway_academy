import type { Teacher, TeacherCreate, TeacherListParams, TeacherUpdate, UUID } from "@/types/api";
import { api } from "./client";

export const teachersApi = {
  list: (params: TeacherListParams = {}) => api.list<Teacher>("/teachers", params),
  get: (id: UUID) => api.get<Teacher>(`/teachers/${id}`),
  me: () => api.get<Teacher>("/teachers/me"),
  create: (payload: TeacherCreate) => api.post<Teacher>("/teachers", payload),
  update: (id: UUID, payload: TeacherUpdate) => api.patch<Teacher>(`/teachers/${id}`, payload),
};
