import type {
  Batch,
  BatchAssignmentResult,
  BatchCreate,
  BatchListParams,
  BatchUpdate,
  MessageOut,
  Student,
  UUID,
} from "@/types/api";
import { api } from "./client";

export const batchesApi = {
  list: (params: BatchListParams = {}) => api.list<Batch>("/batches", params),
  get: (id: UUID) => api.get<Batch>(`/batches/${id}`),
  create: (payload: BatchCreate) => api.post<Batch>("/batches", payload),
  update: (id: UUID, payload: BatchUpdate) => api.patch<Batch>(`/batches/${id}`, payload),
  students: (id: UUID) => api.get<Student[]>(`/batches/${id}/students`),
  addStudents: (id: UUID, studentIds: UUID[]) =>
    api.post<BatchAssignmentResult>(`/batches/${id}/students`, { student_ids: studentIds }),
  removeStudent: (id: UUID, studentId: UUID) =>
    api.delete<MessageOut>(`/batches/${id}/students/${studentId}`),
};
