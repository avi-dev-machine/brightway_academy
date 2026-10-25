import type {
  CheckoutOrder,
  CreateOrderRequest,
  Payment,
  PaymentConfig,
  PaymentListParams,
  PaymentResult,
  UUID,
  VerifyPaymentRequest,
} from "@/types/api";
import { api, newIdempotencyKey } from "./client";

export const paymentsApi = {
  getConfig: () => api.get<PaymentConfig>("/payments/config"),
  createOrder: (payload: CreateOrderRequest, idempotencyKey?: string) =>
    api.post<CheckoutOrder>("/payments/orders", payload, {
      headers: {
        "Idempotency-Key": idempotencyKey || newIdempotencyKey(),
      },
    }),
  verify: (payload: VerifyPaymentRequest) => api.post<PaymentResult>("/payments/verify", payload),
  submitUpiPayment: (feeId: UUID, payload: { reference?: string; notes?: string } = {}) =>
    api.post<PaymentResult>(`/fees/${feeId}/upi-payments`, payload),
  list: (params: PaymentListParams = {}) => api.list<Payment>("/payments", params),
  get: (id: UUID) => api.get<Payment>(`/payments/${id}`),
};
