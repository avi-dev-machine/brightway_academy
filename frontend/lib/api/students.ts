import type {
  BroadcastDueNoticeRequest,
  BroadcastDueNoticeResult,
  DueFeeNoticeResult,
  Student,
  StudentCreate,
  StudentListParams,
  StudentMonthlyFee,
  StudentPhotoResult,
  StudentUpdate,
  UUID,
} from "@/types/api";
import { api, backendUrl, uploadWithProgress } from "./client";

export const studentsApi = {
  list: (params: StudentListParams) => api.list<Student>("/students", params),
  get: (id: UUID) => api.get<Student>(`/students/${id}`),
  getMonthlyFees: (id: UUID) => api.get<StudentMonthlyFee[]>(`/students/${id}/monthly-fees`),
  me: () => api.get<Student>("/students/me"),
  create: (payload: StudentCreate) => api.post<Student>("/students", payload),
  update: (id: UUID, payload: StudentUpdate) => api.patch<Student>(`/students/${id}`, payload),
  deactivate: (id: UUID) => api.post<Student>(`/students/${id}/deactivate`),
  activate: (id: UUID) => api.post<Student>(`/students/${id}/activate`),
  notifyDueFee: (id: UUID, customNote?: string) =>
    api.post<DueFeeNoticeResult>(`/students/${id}/notify-due-fee`, null, {
      query: customNote ? { custom_note: customNote } : undefined,
    }),
  notifyAllUnpaid: (payload?: BroadcastDueNoticeRequest) =>
    api.post<BroadcastDueNoticeResult>("/students/notify-all-unpaid", payload),
  uploadPhoto: (id: UUID, file: File, onProgress?: (percent: number) => void) => {
    const form = new FormData();
    form.append("photo", file);
    return uploadWithProgress<StudentPhotoResult>(`/students/${id}/photo`, form, {
      method: "PUT",
      onProgress,
    });
  },
  /** Photos live in a private bucket and are streamed through the authorised backend endpoint. */
  photoUrl: (id: UUID, version?: string) => backendUrl(`/students/${id}/photo`, { v: version }),
};

