import type {
  AssignPlanRequest,
  CancelFeeRequest,
  ConcessionRequest,
  Fee,
  FeeCreate,
  FeeListParams,
  FeePlan,
  FeePlanCreate,
  FeePlanUpdate,
  FeeSummary,
  OfflinePaymentRequest,
  PaymentResult,
  UUID,
} from "@/types/api";
import { api } from "./client";

export const feesApi = {
  list: (params: FeeListParams) => api.list<Fee>("/fees", params),
  get: (id: UUID) => api.get<Fee>(`/fees/${id}`),
  create: (payload: FeeCreate) => api.post<Fee>("/fees", payload),
  summary: (studentId: UUID) => api.get<FeeSummary>(`/fees/students/${studentId}/summary`),
  applyConcession: (id: UUID, payload: ConcessionRequest) =>
    api.post<Fee>(`/fees/${id}/concessions`, payload),
  cancel: (id: UUID, payload: CancelFeeRequest) => api.post<Fee>(`/fees/${id}/cancel`, payload),
  /** Records a cash/UPI/cheque payment. The backend writes the audit record and receipt. */
  recordOfflinePayment: (id: UUID, payload: OfflinePaymentRequest) =>
    api.post<PaymentResult>(`/fees/${id}/offline-payments`, payload),

  plans: (params: { active?: boolean; course_id?: UUID } = {}) => api.get<FeePlan[]>("/fees/plans", params),
  createPlan: (payload: FeePlanCreate) => api.post<FeePlan>("/fees/plans", payload),
  updatePlan: (id: UUID, payload: FeePlanUpdate) => api.patch<FeePlan>(`/fees/plans/${id}`, payload),
  assignPlan: (studentId: UUID, payload: AssignPlanRequest) =>
    api.post<Fee[]>(`/fees/students/${studentId}/assign-plan`, payload),
};
