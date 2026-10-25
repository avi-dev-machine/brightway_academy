"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { teachersApi } from "@/lib/api/teachers";
import { batchesApi } from "@/lib/api/batches";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CalendarCheck,
  Layers,
  Users,
  Clock,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export default function TeacherDashboardPage() {
  const { data: teacher, isLoading: teacherLoading } = useQuery({
    queryKey: ["teacher-me"],
    queryFn: () => teachersApi.me(),
  });

  const { data: batchesData, isLoading: batchesLoading } = useQuery({
    queryKey: ["teacher-batches"],
    queryFn: () => batchesApi.list({ teacher_id: teacher?.id, active: true }),
    enabled: !!teacher?.id,
  });

  const batches = batchesData?.items || [];
  const totalStudents = batches.reduce((sum, b) => sum + (b.student_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-emerald-900 via-teal-900 to-slate-900 p-6 sm:p-8 text-white shadow-md">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-emerald-200 mb-2">
              <Sparkles className="h-3 w-3" />
              Faculty Portal
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Hello, {teacherLoading ? "Instructor" : teacher?.name}!
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-emerald-200">
              Manage your assigned student cohorts and daily attendance.
            </p>
          </div>

          <Link href="/teacher/attendance">
            <Button variant="accent" size="sm" className="gap-2 text-xs font-semibold">
              <CalendarCheck className="h-4 w-4" />
              Take Today&apos;s Attendance
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Assigned Batches</span>
            <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
              <Layers className="h-4 w-4" />
            </div>
          </div>
          {batchesLoading ? (
            <Skeleton className="mt-2 h-7 w-12" />
          ) : (
            <p className="mt-2 text-2xl font-bold text-slate-900">{batches.length}</p>
          )}
          <p className="mt-1 text-[11px] text-slate-400">Active cohorts</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Students</span>
            <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
              <Users className="h-4 w-4" />
            </div>
          </div>
          {batchesLoading ? (
            <Skeleton className="mt-2 h-7 w-12" />
          ) : (
            <p className="mt-2 text-2xl font-bold text-slate-900">{totalStudents}</p>
          )}
          <p className="mt-1 text-[11px] text-slate-400">Under your instruction</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Today&apos;s Classes</span>
            <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-2xl font-bold text-slate-900">{batches.length}</p>
          <p className="mt-1 text-[11px] text-slate-400">Scheduled classroom sessions</p>
        </Card>
      </div>

      {/* Assigned Batches List */}
      <Card className="overflow-hidden shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base">My Active Batches</CardTitle>
          <CardDescription className="text-xs">
            Review timings and launch one-click attendance check-ins
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {batchesLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : batches.length === 0 ? (
            <p className="p-8 text-center text-xs text-slate-500">
              No batches currently assigned. The administrator will assign your cohort schedules.
            </p>
          ) : (
            <div className="divide-y divide-slate-100 text-xs">
              {batches.map((batch) => (
                <div
                  key={batch.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 gap-4 hover:bg-slate-50/50"
                >
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">{batch.name}</h3>
                    <p className="text-slate-500 mt-0.5">
                      Course:{" "}
                      <span className="font-medium text-slate-700">
                        {batch.course_name || "General IT"}
                      </span>{" "}
                      • Schedule:{" "}
                      <span className="font-mono text-slate-700">
                        {batch.schedule || "Regular timings"}
                      </span>
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant="default" className="text-[10px]">
                        {batch.student_count ?? 0} Students
                      </Badge>
                      <Badge variant="success" className="text-[10px]">
                        Active
                      </Badge>
                    </div>
                  </div>

                  <Link href={`/teacher/attendance?batch_id=${batch.id}`}>
                    <Button variant="primary" size="sm" className="gap-1.5 text-xs w-full sm:w-auto">
                      <CalendarCheck className="h-3.5 w-3.5" />
                      Mark Attendance
                      <ArrowRight className="h-3.5 w-3.5 ml-1" />
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
