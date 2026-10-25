"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { batchesApi } from "@/lib/api/batches";
import { attendanceApi } from "@/lib/api/attendance";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { CalendarCheck, Users } from "lucide-react";

export default function AdminAttendancePage() {
  const [selectedBatchId, setSelectedBatchId] = useState<string>("");
  const [selectedDate, setSelectedDate] = useState<string>("");

  useEffect(() => {
    setSelectedDate(new Date().toISOString().split("T")[0]);
  }, []);

  const { data: batchesData } = useQuery({
    queryKey: ["admin-batches-list"],
    queryFn: () => batchesApi.list({ active: true }),
  });

  const batches = batchesData?.items || [];
  const activeBatchId = selectedBatchId || batches[0]?.id;

  const { data: roster, isLoading: rosterLoading } = useQuery({
    queryKey: ["batch-roster", activeBatchId, selectedDate],
    queryFn: () => attendanceApi.getBatchRoster(activeBatchId, selectedDate),
    enabled: !!activeBatchId,
  });

  const { data: reportRows, isLoading: reportLoading } = useQuery({
    queryKey: ["batch-report", activeBatchId],
    queryFn: () => attendanceApi.getBatchReport(activeBatchId),
    enabled: !!activeBatchId,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Attendance Overview
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Review daily classroom attendance registers and aggregate batch reports.
        </p>
      </div>

      {/* Selectors Toolbar */}
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
                  {b.name} ({b.course_name || "General"})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">
              Attendance Date
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
            />
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Day's Roster */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-3 border-b border-slate-100">
            <CardTitle className="text-base flex items-center justify-between">
              <span>Day Register ({formatDate(selectedDate)})</span>
              <CalendarCheck className="h-4 w-4 text-blue-600" />
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {rosterLoading ? (
              <div className="p-6 space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !roster || roster.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={<Users className="h-8 w-8" />}
                  title="No students on roster"
                  description="No students assigned to this batch or no register found."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-4">Student</th>
                      <th className="py-2.5 px-4">Status</th>
                      <th className="py-2.5 px-4">Remarks</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {roster.map((entry) => (
                      <tr key={entry.student_id}>
                        <td className="py-3 px-4">
                          <p className="font-semibold text-slate-900">{entry.name}</p>
                          <p className="font-mono text-[10px] text-slate-400">ID: {entry.id_no}</p>
                        </td>
                        <td className="py-3 px-4">
                          {entry.status ? (
                            <Badge
                              variant={
                                entry.status === "PRESENT"
                                  ? "success"
                                  : entry.status === "ABSENT"
                                  ? "danger"
                                  : "warning"
                              }
                            >
                              {entry.status}
                            </Badge>
                          ) : (
                            <span className="text-slate-400 text-xs">Unmarked</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-500">{entry.remarks || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Aggregate Batch Attendance Report */}
        <Card className="overflow-hidden">
          <CardHeader className="pb-3 border-b border-slate-100">
            <CardTitle className="text-base">Batch Attendance Rate</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {reportLoading ? (
              <div className="p-6 space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !reportRows || reportRows.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={<CalendarCheck className="h-8 w-8" />}
                  title="No report records"
                  description="Attendance statistics will compile as daily classes are marked."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-4">Student</th>
                      <th className="py-2.5 px-4">Present</th>
                      <th className="py-2.5 px-4">Absent</th>
                      <th className="py-2.5 px-4">Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {reportRows.map((row) => (
                      <tr key={row.student_id}>
                        <td className="py-3 px-4 font-semibold text-slate-900">{row.name}</td>
                        <td className="py-3 px-4 text-emerald-600 font-medium">{row.present}</td>
                        <td className="py-3 px-4 text-rose-600 font-medium">{row.absent}</td>
                        <td className="py-3 px-4 font-bold text-slate-900">
                          {row.percentage !== null && row.percentage !== undefined
                            ? `${Math.round(row.percentage)}%`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
