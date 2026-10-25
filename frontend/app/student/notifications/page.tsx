"use client";

import { useQuery } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api/students";
import { notificationsApi } from "@/lib/api/notifications";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDateTime } from "@/lib/utils";
import { Bell, MessageSquare } from "lucide-react";

export default function StudentNotificationsPage() {
  const { data: student } = useQuery({
    queryKey: ["student-me"],
    queryFn: () => studentsApi.me(),
  });

  const studentId = student?.id;

  const { data: notificationsData, isLoading } = useQuery({
    queryKey: ["student-notifications", studentId],
    queryFn: () => notificationsApi.list({ student_id: studentId!, page_size: 20 }),
    enabled: !!studentId,
  });

  const notifications = notificationsData?.items || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Announcements & Alerts
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Automated fee reminders, settlement receipts, and academy updates.
        </p>
      </div>

      <Card className="overflow-hidden shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4 text-blue-600" />
            Alerts Log
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={<Bell className="h-8 w-8" />}
                title="No announcements yet"
                description="Upcoming payment reminders and academy updates will be displayed here."
              />
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {notifications.map((n) => (
                <div key={n.id} className="p-4 hover:bg-slate-50/50 flex items-start gap-3">
                  <div className="rounded-lg bg-blue-50 p-2 text-blue-600 shrink-0 mt-0.5">
                    <MessageSquare className="h-4 w-4" />
                  </div>
                  <div className="flex-1 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-semibold text-slate-900 capitalize">
                        {n.template.replace(/_/g, " ")}
                      </p>
                      <Badge variant={n.status === "DELIVERED" ? "success" : "default"}>
                        {n.status}
                      </Badge>
                    </div>
                    <p className="text-slate-500 text-[11px] mt-1">
                      Sent via {n.channel} to {n.recipient} • {formatDateTime(n.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
