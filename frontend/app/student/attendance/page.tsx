"use client";

import { useQuery } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api/students";
import { attendanceApi } from "@/lib/api/attendance";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { CalendarCheck } from "lucide-react";

export default function StudentAttendancePage() {
  const { data: student } = useQuery({
    queryKey: ["student-me"],
    queryFn: () => studentsApi.me(),
  });

  const studentId = student?.id;

  const { data: attendance, isLoading } = useQuery({
    queryKey: ["student-attendance", studentId],
    queryFn: () => attendanceApi.getStudentAttendance(studentId!),
    enabled: !!studentId,
  });

  const summary = attendance?.summary;
  const records = attendance?.records || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Attendance Record
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Class participation rate and historical classroom check-in logs.
        </p>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <span className="text-xs text-slate-500 font-medium">Attendance Rate</span>
          {isLoading ? (
            <Skeleton className="h-8 w-16 mx-auto mt-1" />
          ) : (
            <p className="text-2xl font-extrabold text-blue-600 mt-1">
              {summary?.percentage !== null && summary?.percentage !== undefined
                ? `${Math.round(summary.percentage)}%`
                : "—"}
            </p>
          )}
        </Card>

        <Card className="p-4 text-center">
          <span className="text-xs text-slate-500 font-medium">Classes Held</span>
          {isLoading ? (
            <Skeleton className="h-8 w-12 mx-auto mt-1" />
          ) : (
            <p className="text-2xl font-extrabold text-slate-900 mt-1">
              {summary?.total ?? 0}
            </p>
          )}
        </Card>

        <Card className="p-4 text-center">
          <span className="text-xs text-slate-500 font-medium">Present Days</span>
          {isLoading ? (
            <Skeleton className="h-8 w-12 mx-auto mt-1" />
          ) : (
            <p className="text-2xl font-extrabold text-emerald-600 mt-1">
              {summary?.present ?? 0}
            </p>
          )}
        </Card>

        <Card className="p-4 text-center">
          <span className="text-xs text-slate-500 font-medium">Absences</span>
          {isLoading ? (
            <Skeleton className="h-8 w-12 mx-auto mt-1" />
          ) : (
            <p className="text-2xl font-extrabold text-rose-600 mt-1">
              {summary?.absent ?? 0}
            </p>
          )}
        </Card>
      </div>

      {/* Records Table */}
      <Card className="overflow-hidden shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base">Check-in Register</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : records.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={<CalendarCheck className="h-8 w-8" />}
                title="No attendance records found"
                description="Your teacher has not recorded attendance checks yet."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Date</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {records.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-4 font-medium text-slate-900">
                        {formatDate(r.attendance_date)}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={
                            r.status === "PRESENT"
                              ? "success"
                              : r.status === "ABSENT"
                              ? "danger"
                              : "warning"
                          }
                        >
                          {r.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-slate-500">{r.remarks || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
