import type { Course, CourseCreate, CourseListParams, CourseUpdate, UUID } from "@/types/api";
import { api } from "./client";

export const coursesApi = {
  list: (params: CourseListParams = {}) => api.list<Course>("/courses", params),
  get: (id: UUID) => api.get<Course>(`/courses/${id}`),
  create: (payload: CourseCreate) => api.post<Course>("/courses", payload),
  /** Courses are never deleted (historical records depend on them); use `active: false`. */
  update: (id: UUID, payload: CourseUpdate) => api.patch<Course>(`/courses/${id}`, payload),
};
