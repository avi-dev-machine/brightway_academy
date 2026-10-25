"use client";

import { useQuery } from "@tanstack/react-query";
import { teachersApi } from "@/lib/api/teachers";
import { batchesApi } from "@/lib/api/batches";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import Link from "next/link";
import { Layers, CalendarCheck, Users, Clock } from "lucide-react";

export default function TeacherBatchesPage() {
  const { data: teacher } = useQuery({
    queryKey: ["teacher-me"],
    queryFn: () => teachersApi.me(),
  });

  const { data: batchesData, isLoading } = useQuery({
    queryKey: ["teacher-batches"],
    queryFn: () => batchesApi.list({ teacher_id: teacher?.id, active: true }),
    enabled: !!teacher?.id,
  });

  const batches = batchesData?.items || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          My Teaching Batches
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Student cohorts and schedules assigned to your instruction.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {isLoading ? (
          <div className="col-span-2 space-y-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : batches.length === 0 ? (
          <div className="col-span-2">
            <EmptyState
              icon={<Layers className="h-8 w-8" />}
              title="No assigned batches"
              description="Contact the academy administrator to have student cohorts assigned to your profile."
            />
          </div>
        ) : (
          batches.map((batch) => (
            <Card key={batch.id} className="shadow-2xs flex flex-col justify-between">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Badge variant="info" className="text-[10px]">
                    {batch.course_name || "General Program"}
                  </Badge>
                  <Badge variant="success" className="text-[10px]">
                    Active Cohort
                  </Badge>
                </div>
                <CardTitle className="text-base mt-2">{batch.name}</CardTitle>
                <div className="mt-3 space-y-1.5 text-xs text-slate-600">
                  <p className="flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5 text-slate-400" />
                    Schedule: <span className="font-mono text-slate-900">{batch.schedule || "Regular"}</span>
                  </p>
                  <p className="flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5 text-slate-400" />
                    Enrolled Students: <span className="font-bold text-slate-900">{batch.student_count ?? 0}</span>
                  </p>
                </div>
              </CardHeader>
              <CardContent className="pt-2 border-t border-slate-100 flex justify-end">
                <Link href={`/teacher/attendance?batch_id=${batch.id}`}>
                  <Button variant="primary" size="sm" className="gap-1.5 text-xs">
                    <CalendarCheck className="h-3.5 w-3.5" />
                    Open Attendance Register
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
