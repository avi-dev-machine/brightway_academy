"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/lib/api/notifications";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { formatDateTime } from "@/lib/utils";
import { toast } from "sonner";
import { Bell, RefreshCw, MessageSquare, PhoneCall } from "lucide-react";
import type { NotificationChannel, NotificationStatus } from "@/types/api";

export default function AdminNotificationsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [channelFilter, setChannelFilter] = useState<NotificationChannel | "">("");
  const [statusFilter, setStatusFilter] = useState<NotificationStatus | "">("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-notifications", page, channelFilter, statusFilter],
    queryFn: () =>
      notificationsApi.list({
        page,
        page_size: 20,
        channel: channelFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.retry(id),
    onSuccess: () => {
      toast.success("Notification requeued for delivery retry.");
      queryClient.invalidateQueries({ queryKey: ["admin-notifications"] });
    },
    onError: () => toast.error("Unable to retry notification."),
  });

  const notifications = data?.items || [];
  const meta = data?.meta;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Notification Delivery
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Delivery tracking and gateway logs for automated WhatsApp reminders and SMS confirmations.
        </p>
      </div>

      {/* Filter Toolbar */}
      <Card className="p-4 shadow-2xs">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={channelFilter}
            onChange={(e) => {
              setChannelFilter(e.target.value as NotificationChannel | "");
              setPage(1);
            }}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
          >
            <option value="">All Channels</option>
            <option value="WHATSAPP">WhatsApp</option>
            <option value="SMS">SMS</option>
            <option value="EMAIL">Email</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as NotificationStatus | "");
              setPage(1);
            }}
            className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
          >
            <option value="">All Statuses</option>
            <option value="DELIVERED">Delivered</option>
            <option value="SENT">Sent</option>
            <option value="QUEUED">Queued</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </Card>

      <Card className="overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<Bell className="h-8 w-8" />}
              title="No notifications recorded"
              description="Notifications are dispatched in background schedules for fee reminders and payment confirmations."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Channel</th>
                  <th className="py-3 px-4">Recipient</th>
                  <th className="py-3 px-4">Template</th>
                  <th className="py-3 px-4">Attempts</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {notifications.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 font-medium text-slate-800">
                        {item.channel === "WHATSAPP" ? (
                          <MessageSquare className="h-3.5 w-3.5 text-emerald-600" />
                        ) : (
                          <PhoneCall className="h-3.5 w-3.5 text-blue-600" />
                        )}
                        {item.channel}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-900">{item.recipient}</td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-600">{item.template}</td>
                    <td className="py-3 px-4 text-slate-500">
                      {item.attempts} / {item.max_attempts}
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        variant={
                          item.status === "DELIVERED" || item.status === "SENT"
                            ? "success"
                            : item.status === "FAILED"
                            ? "danger"
                            : "warning"
                        }
                      >
                        {item.status}
                      </Badge>
                      {item.last_error && (
                        <p className="text-[10px] text-rose-600 mt-0.5 truncate max-w-xs">
                          {item.last_error}
                        </p>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDateTime(item.created_at)}</td>
                    <td className="py-3 px-4 text-right">
                      {item.status === "FAILED" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs text-blue-600"
                          onClick={() => retryMutation.mutate(item.id)}
                        >
                          <RefreshCw className="h-3 w-3 mr-1" />
                          Retry
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {meta && (
          <div className="p-4 border-t border-slate-100">
            <Pagination
              page={meta.page}
              pageSize={meta.page_size}
              total={meta.total}
              totalPages={meta.total_pages}
              onPageChange={setPage}
              isLoading={isLoading}
            />
          </div>
        )}
      </Card>
    </div>
  );
}
