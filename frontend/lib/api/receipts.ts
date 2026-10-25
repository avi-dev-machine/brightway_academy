import type { Receipt, ReceiptListParams, UUID } from "@/types/api";
import { api, backendUrl } from "./client";

export const receiptsApi = {
  list: (params: ReceiptListParams = {}) => api.list<Receipt>("/receipts", params),
  get: (id: UUID) => api.get<Receipt>(`/receipts/${id}`),
  downloadUrl: (id: UUID) => backendUrl(`/receipts/${id}/download`),
};
