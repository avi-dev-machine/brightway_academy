import type {
  ImportConfirmRequest,
  ImportJob,
  ImportPreview,
  ImportRow,
  ImportRowStatus,
  PageParams,
  UUID,
} from "@/types/api";
import { api, uploadWithProgress } from "./client";

export const importsApi = {
  preview: (file: File, onProgress?: (percent: number) => void) => {
    const formData = new FormData();
    formData.append("file", file);
    return uploadWithProgress<ImportPreview>("/imports/students/preview", formData, {
      method: "POST",
      onProgress,
    });
  },
  listJobs: (params: PageParams = {}) => api.list<ImportJob>("/imports", params),
  getJob: (jobId: UUID) => api.get<ImportJob>(`/imports/${jobId}`),
  listRows: (
    jobId: UUID,
    params: PageParams & { status?: ImportRowStatus } = {},
  ) => api.list<ImportRow>(`/imports/${jobId}/rows`, params),
  confirm: (jobId: UUID, payload: ImportConfirmRequest = {}) =>
    api.post<ImportJob>(`/imports/${jobId}/confirm`, payload),
};
