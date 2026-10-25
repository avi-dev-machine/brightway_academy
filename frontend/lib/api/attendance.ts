import type {
  AttendanceRecord,
  BatchReportRow,
  DateRange,
  ISODate,
  MarkAttendanceRequest,
  RosterEntry,
  StudentAttendance,
  UUID,
} from "@/types/api";
import { api } from "./client";

export const attendanceApi = {
  getBatchRoster: (batchId: UUID, day?: ISODate) =>
    api.get<RosterEntry[]>(`/attendance/batches/${batchId}`, { day }),
  markBatch: (batchId: UUID, payload: MarkAttendanceRequest) =>
    api.post<AttendanceRecord[]>(`/attendance/batches/${batchId}`, payload),
  getBatchReport: (batchId: UUID, range: DateRange = {}) =>
    api.get<BatchReportRow[]>(`/attendance/batches/${batchId}/report`, range),
  getStudentAttendance: (studentId: UUID, range: DateRange = {}) =>
    api.get<StudentAttendance>(`/attendance/students/${studentId}`, range),
};
