"use client";

import { useState, useEffect, Suspense } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { teachersApi } from "@/lib/api/teachers";
import { batchesApi } from "@/lib/api/batches";
import { attendanceApi } from "@/lib/api/attendance";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { formatDate } from "@/lib/utils";
import { toast } from "sonner";
import {
  CalendarCheck,
  Check,
  X,
  Clock,
  AlertCircle,
  Save,
  Users,
} from "lucide-react";
import type { AttendanceStatus, RosterEntry } from "@/types/api";

function TeacherAttendanceContent() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const [date, setDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>(
    searchParams.get("batch_id") || "",
  );

  // In-memory edits for fast marking
  const [attendanceMap, setAttendanceMap] = useState<
    Record<string, { status: AttendanceStatus; remarks: string }>
  >({});

  const { data: teacher } = useQuery({
    queryKey: ["teacher-me"],
    queryFn: () => teachersApi.me(),
  });

  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ["teacher-batches"],
    queryFn: () => batchesApi.list({ teacher_id: teacher?.id, active: true }),
    enabled: !!teacher?.id,
  });

  const batches = batchesData?.items || [];
  const activeBatchId = selectedBatchId || batches[0]?.id;

  const { data: roster, isLoading: rosterLoading } = useQuery({
    queryKey: ["batch-roster-marking", activeBatchId, date],
    queryFn: () => attendanceApi.getBatchRoster(activeBatchId, date),
    enabled: !!activeBatchId,
  });

  // Populate local state when roster loads
  useEffect(() => {
    if (roster) {
      const initial: Record<string, { status: AttendanceStatus; remarks: string }> = {};
      roster.forEach((entry: RosterEntry) => {
        initial[entry.student_id] = {
          status: entry.status || "PRESENT",
          remarks: entry.remarks || "",
        };
      });
      setAttendanceMap(initial);
    }
  }, [roster]);

  const markAllPresent = () => {
    if (!roster) return;
    const updated: Record<string, { status: AttendanceStatus; remarks: string }> = { ...attendanceMap };
    roster.forEach((entry: RosterEntry) => {
      updated[entry.student_id] = {
        status: "PRESENT",
        remarks: updated[entry.student_id]?.remarks || "",
      };
    });
    setAttendanceMap(updated);
    toast.success("Marked all students as Present.");
  };

  const markStatus = (studentId: string, status: AttendanceStatus) => {
    setAttendanceMap((prev) => ({
      ...prev,
      [studentId]: {
        status,
        remarks: prev[studentId]?.remarks || "",
      },
    }));
  };

  const updateRemarks = (studentId: string, remarks: string) => {
    setAttendanceMap((prev) => ({
      ...prev,
      [studentId]: {
        status: prev[studentId]?.status || "PRESENT",
        remarks,
      },
    }));
  };

  const submitMutation = useMutation({
    mutationFn: () => {
      if (!activeBatchId || !roster) throw new Error("No active batch");
      const records = roster.map((r) => ({
        student_id: r.student_id,
        status: attendanceMap[r.student_id]?.status || "PRESENT",
        remarks: attendanceMap[r.student_id]?.remarks || null,
      }));
      return attendanceApi.markBatch(activeBatchId, {
        attendance_date: date,
        records,
      });
    },
    onSuccess: () => {
      toast.success("Attendance saved successfully!");
      queryClient.invalidateQueries({ queryKey: ["batch-roster-marking", activeBatchId, date] });
    },
    onError: () => toast.error("Failed to save attendance."),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Class Attendance Register
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Quick 1-click roster marking for your scheduled batches.
          </p>
        </div>

        {roster && roster.length > 0 && (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={markAllPresent} className="text-xs">
              Mark All Present
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={submitMutation.isPending}
              onClick={() => submitMutation.mutate()}
              className="gap-1.5 text-xs font-semibold"
            >
              <Save className="h-4 w-4" />
              Save Attendance
            </Button>
          </div>
        )}
      </div>

      {/* Selectors Bar */}
      <Card className="p-4 shadow-2xs">
        <div className="flex flex-wrap items-center gap-4">
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">
              Select Batch
            </label>
            <select
              value={activeBatchId || ""}
              onChange={(e) => setSelectedBatchId(e.target.value)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600 min-w-[220px]"
            >
              {batches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.student_count ?? 0} students)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">
              Class Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
            />
          </div>
        </div>
      </Card>

      {/* Roster Marking Table */}
      <Card className="overflow-hidden shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base flex items-center justify-between">
            <span>Student Roster ({roster?.length ?? 0})</span>
            <span className="text-xs font-normal text-slate-500">{formatDate(date)}</span>
          </CardTitle>
          <CardDescription className="text-xs">
            Toggle Present, Absent, Late, or Excused for each student below.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {rosterLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !roster || roster.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={<Users className="h-8 w-8" />}
                title="No students on batch roster"
                description="This batch has no students enrolled yet."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Student</th>
                    <th className="py-2.5 px-4 text-center">Status Toggle</th>
                    <th className="py-2.5 px-4">Optional Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {roster.map((entry) => {
                    const currentStatus = attendanceMap[entry.student_id]?.status || "PRESENT";
                    const currentRemarks = attendanceMap[entry.student_id]?.remarks || "";

                    return (
                      <tr key={entry.student_id} className="hover:bg-slate-50/50">
                        <td className="py-3 px-4">
                          <p className="font-semibold text-slate-900">{entry.name}</p>
                          <p className="font-mono text-[10px] text-slate-400">ID: {entry.id_no}</p>
                        </td>

                        <td className="py-3 px-4">
                          {/* Fast toggle buttons */}
                          <div className="flex items-center justify-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => markStatus(entry.student_id, "PRESENT")}
                              className={`h-7 px-2.5 rounded-md text-xs font-semibold cursor-pointer transition-colors ${
                                currentStatus === "PRESENT"
                                  ? "bg-emerald-600 text-white shadow-2xs"
                                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                              }`}
                            >
                              Present
                            </button>

                            <button
                              type="button"
                              onClick={() => markStatus(entry.student_id, "ABSENT")}
                              className={`h-7 px-2.5 rounded-md text-xs font-semibold cursor-pointer transition-colors ${
                                currentStatus === "ABSENT"
                                  ? "bg-rose-600 text-white shadow-2xs"
                                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                              }`}
                            >
                              Absent
                            </button>

                            <button
                              type="button"
                              onClick={() => markStatus(entry.student_id, "LATE")}
                              className={`h-7 px-2.5 rounded-md text-xs font-semibold cursor-pointer transition-colors ${
                                currentStatus === "LATE"
                                  ? "bg-amber-600 text-white shadow-2xs"
                                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                              }`}
                            >
                              Late
                            </button>

                            <button
                              type="button"
                              onClick={() => markStatus(entry.student_id, "EXCUSED")}
                              className={`h-7 px-2.5 rounded-md text-xs font-semibold cursor-pointer transition-colors ${
                                currentStatus === "EXCUSED"
                                  ? "bg-blue-600 text-white shadow-2xs"
                                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                              }`}
                            >
                              Excused
                            </button>
                          </div>
                        </td>

                        <td className="py-3 px-4 max-w-xs">
                          <Input
                            placeholder="e.g. Arrived 15 mins late..."
                            value={currentRemarks}
                            onChange={(e) => updateRemarks(entry.student_id, e.target.value)}
                            className="h-8 text-xs bg-white"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
        {roster && roster.length > 0 && (
          <CardFooter className="flex justify-end p-4 border-t border-slate-100">
            <Button
              variant="primary"
              size="sm"
              isLoading={submitMutation.isPending}
              onClick={() => submitMutation.mutate()}
              className="gap-1.5 text-xs font-semibold"
            >
              <Save className="h-4 w-4" />
              Save Attendance
            </Button>
          </CardFooter>
        )}
      </Card>
    </div>
  );
}

export default function TeacherAttendancePage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <div className="h-8 w-48 animate-pulse rounded bg-slate-200" />
          <div className="h-64 animate-pulse rounded bg-slate-100" />
        </div>
      }
    >
      <TeacherAttendanceContent />
    </Suspense>
  );
}
