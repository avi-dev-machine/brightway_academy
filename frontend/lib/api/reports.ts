import type {
  CollectionReport,
  DashboardStats,
  DateRange,
  OutstandingRow,
  PageParams,
  UUID,
} from "@/types/api";
import { api, backendUrl } from "./client";

export const reportsApi = {
  getDashboardStats: () => api.get<DashboardStats>("/reports/dashboard"),
  getCollections: (range: DateRange = {}) =>
    api.get<CollectionReport>("/reports/fees/collections", range),
  getOutstanding: (params: PageParams & { course_id?: UUID } = {}) =>
    api.list<OutstandingRow>("/reports/fees/outstanding", params),
  exportStudentsUrl: () => backendUrl("/reports/exports/students.csv"),
  exportFeesUrl: () => backendUrl("/reports/exports/fees.csv"),
  exportPaymentsUrl: (range: DateRange = {}) =>
    backendUrl("/reports/exports/payments.csv", range as Record<string, string>),
};
