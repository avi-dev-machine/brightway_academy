"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { reportsApi } from "@/lib/api/reports";
import { adminApi } from "@/lib/api/admin";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, MetricStrip, Metric } from "@/components/ui/page";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  Users,
  CreditCard,
  CalendarCheck,
  UserPlus,
  Send,
  Download,
  AlertCircle,
  ArrowRight,
  RotateCw,
  MessageSquare,
  FileText,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { BroadcastNoticesDialog } from "@/components/students/broadcast-notices-dialog";
import {
  WhatsAppNoticeDialog,
  type WhatsAppNoticeStudent,
} from "@/components/students/whatsapp-notice-dialog";
import type { OutstandingRow } from "@/types/api";

export default function AdminDashboardPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "defaulters" | "reports">("overview");
  const [broadcastOpen, setBroadcastOpen] = useState(false);
  const [whatsappStudent, setWhatsappStudent] = useState<WhatsAppNoticeStudent | null>(null);

  const {
    data: stats,
    isLoading: statsLoading,
    refetch: refetchStats,
    isFetching: isRefreshing,
  } = useQuery({
    queryKey: ["admin-dashboard-stats"],
    queryFn: () => reportsApi.getDashboardStats(),
  });

  const { data: setup } = useQuery({
    queryKey: ["admin-setup-status"],
    queryFn: () => adminApi.getSetupStatus(),
  });

  const { data: outstandingData, isLoading: outstandingLoading } = useQuery({
    queryKey: ["admin-outstanding-fees"],
    queryFn: () => reportsApi.getOutstanding({ page: 1, page_size: 20 }),
  });

  const chartData =
    stats?.students_by_course?.map((item) => ({
      name: item.course_name || "General",
      count: item.count,
    })) || [];

  const handleOpenNotice = (row: OutstandingRow) => {
    setWhatsappStudent({
      id: row.student_id,
      name: row.name,
      id_no: row.id_no,
      contact: row.contact,
      course_name: row.course_name,
      total_due_paise: row.outstanding_paise || row.overdue_paise,
      outstanding_paise: row.outstanding_paise,
      overdue_paise: row.overdue_paise,
    });
  };

  const overdueCount = stats?.fees_overdue_count ?? 0;
  const overduePaise = stats?.fees_overdue_paise ?? 0;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <PageHeader
        title="Academy Overview"
        description="Daily enrollment, fee collections, and student operations across the institution."
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchStats()}
              disabled={isRefreshing}
              className="gap-1.5"
            >
              <RotateCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              Sync
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setBroadcastOpen(true)}
              className="gap-1.5"
            >
              <Send className="h-3.5 w-3.5 text-slate-500" />
              Notify unpaid students
              {overdueCount > 0 && (
                <span className="ml-1 rounded-sm bg-rose-50 px-1.5 py-px text-[11px] font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                  {overdueCount}
                </span>
              )}
            </Button>

            <Link href="/admin/students">
              <Button variant="default" size="sm" className="gap-1.5">
                <UserPlus className="h-3.5 w-3.5" />
                Add student
              </Button>
            </Link>
          </>
        }
      />

      {/* Setup notification banner if incomplete */}
      {setup && !setup.setup_completed && (
        <div className="flex items-start justify-between gap-4 rounded-md border border-amber-200 bg-amber-50/60 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
            <div className="text-xs">
              <p className="font-semibold text-amber-900">Setup incomplete</p>
              <p className="mt-0.5 text-amber-800">
                Configure your academy profile, course fees, and receipt numbering to finalize system setup.
              </p>
            </div>
          </div>
          <Link href="/admin/settings">
            <Button variant="outline" size="sm" className="shrink-0 text-xs bg-white">
              Open settings
            </Button>
          </Link>
        </div>
      )}

      {/* Primary Metric Strip */}
      <MetricStrip>
        <Metric
          label="Total enrollment"
          value={
            statsLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : (
              (stats?.students_total ?? 0).toLocaleString("en-IN")
            )
          }
          detail={
            statsLoading ? null : (
              <span>
                <span className="text-emerald-700 font-medium">{stats?.students_active ?? 0}</span> active ·{" "}
                {stats?.students_inactive ?? 0} completed
              </span>
            )
          }
        />

        <Metric
          label="Collections this month"
          value={
            statsLoading ? (
              <Skeleton className="h-7 w-28" />
            ) : (
              formatCurrency(stats?.collected_this_month_paise)
            )
          }
          detail={
            statsLoading ? null : (
              <span>
                Today: {formatCurrency(stats?.collected_today_paise)} ({stats?.payments_today ?? 0} tx)
              </span>
            )
          }
        />

        <Metric
          label="Total outstanding"
          value={
            statsLoading ? (
              <Skeleton className="h-7 w-28" />
            ) : (
              formatCurrency(stats?.fees_outstanding_paise)
            )
          }
          detail="Scheduled installment balances"
        />

        <Metric
          label="Overdue fees"
          tone={overdueCount > 0 ? "danger" : "default"}
          value={
            statsLoading ? (
              <Skeleton className="h-7 w-28" />
            ) : (
              formatCurrency(overduePaise)
            )
          }
          detail={
            statsLoading ? null : (
              <span>
                {overdueCount} {overdueCount === 1 ? "student" : "students"} overdue
              </span>
            )
          }
        />
      </MetricStrip>

      {/* Tabs */}
      <div className="border-b border-rule">
        <nav className="flex gap-6" aria-label="Dashboard views">
          <button
            type="button"
            onClick={() => setActiveTab("overview")}
            className={`pb-3 text-sm font-medium transition-colors border-b-2 -mb-px cursor-pointer ${
              activeTab === "overview"
                ? "border-ink text-ink"
                : "border-transparent text-slate-500 hover:text-ink"
            }`}
          >
            Analytics & operations
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("defaulters")}
            className={`flex items-center gap-2 pb-3 text-sm font-medium transition-colors border-b-2 -mb-px cursor-pointer ${
              activeTab === "defaulters"
                ? "border-ink text-ink"
                : "border-transparent text-slate-500 hover:text-ink"
            }`}
          >
            <span>Outstanding dues</span>
            {overdueCount > 0 && (
              <span className="rounded-sm bg-rose-50 px-1.5 py-px text-[11px] font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                {overdueCount}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("reports")}
            className={`pb-3 text-sm font-medium transition-colors border-b-2 -mb-px cursor-pointer ${
              activeTab === "reports"
                ? "border-ink text-ink"
                : "border-transparent text-slate-500 hover:text-ink"
            }`}
          >
            Data exports
          </button>
        </nav>
      </div>

      {/* TAB 1: Overview & Analytics */}
      {activeTab === "overview" && (
        <div className="space-y-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart: Students by course */}
            <div className="rounded-lg border border-rule bg-white p-5 lg:col-span-2">
              <div className="flex items-baseline justify-between pb-4 border-b border-rule">
                <div>
                  <h3 className="text-sm font-semibold text-ink">Enrollment by course</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Active students across programs</p>
                </div>
                <Link
                  href="/admin/courses"
                  className="text-xs text-slate-500 hover:text-ink inline-flex items-center gap-1 font-medium"
                >
                  Manage courses
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>

              <div className="h-64 w-full pt-6">
                {statsLoading ? (
                  <Skeleton className="h-full w-full" />
                ) : chartData.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-xs text-slate-400">
                    No course enrollment records.
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 8, right: 12, left: -20, bottom: 24 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="var(--color-rule)" vertical={false} />
                      <XAxis
                        dataKey="name"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        interval={0}
                        angle={-15}
                        textAnchor="end"
                        stroke="#64748b"
                      />
                      <YAxis
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                        stroke="#64748b"
                        allowDecimals={false}
                      />
                      <Tooltip
                        cursor={{ fill: "oklch(0.975 0.005 260)" }}
                        contentStyle={{
                          backgroundColor: "#ffffff",
                          border: "1px solid var(--color-rule)",
                          borderRadius: "4px",
                          fontSize: "12px",
                          padding: "6px 10px",
                          boxShadow: "none",
                        }}
                      />
                      <Bar
                        dataKey="count"
                        fill="oklch(0.475 0.185 264)"
                        radius={[2, 2, 0, 0]}
                        maxBarSize={48}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            {/* Attendance Snapshot */}
            <div className="rounded-lg border border-rule bg-white p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-baseline justify-between pb-4 border-b border-rule">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">Today&apos;s attendance</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Roster check-ins recorded today</p>
                  </div>
                  <CalendarCheck className="h-4 w-4 text-slate-400" />
                </div>

                <div className="space-y-4 pt-5">
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs text-slate-500">Students marked:</span>
                    <span className="text-lg font-semibold text-ink tabular">
                      {stats?.attendance_today_marked ?? 0}
                    </span>
                  </div>

                  <div className="flex items-baseline justify-between">
                    <span className="text-xs text-slate-500">Present in class:</span>
                    <span className="text-lg font-semibold text-emerald-700 tabular">
                      {stats?.attendance_today_attended ?? 0}
                    </span>
                  </div>

                  {stats && stats.attendance_today_marked > 0 && (
                    <div className="pt-2">
                      <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                        <span>Attendance rate</span>
                        <span className="font-medium text-ink tabular">
                          {Math.round(
                            (stats.attendance_today_attended / stats.attendance_today_marked) * 100
                          )}
                          %
                        </span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full bg-emerald-600 transition-all duration-300"
                          style={{
                            width: `${Math.min(
                              100,
                              Math.round(
                                (stats.attendance_today_attended / stats.attendance_today_marked) * 100
                              )
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-6 border-t border-rule mt-6">
                <Link href="/admin/attendance" className="block">
                  <Button variant="outline" size="sm" className="w-full justify-between text-xs">
                    Open attendance roster
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>

          {/* Quick operations hub */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
              Direct access
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Link
                href="/admin/students"
                className="group rounded-md border border-rule bg-white p-3.5 transition-colors hover:border-slate-400"
              >
                <div className="flex items-center gap-2 text-ink text-xs font-medium">
                  <Users className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                  <span>Student directory</span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">Search and edit records</p>
              </Link>

              <Link
                href="/admin/fees"
                className="group rounded-md border border-rule bg-white p-3.5 transition-colors hover:border-slate-400"
              >
                <div className="flex items-center gap-2 text-ink text-xs font-medium">
                  <CreditCard className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                  <span>Fee collection</span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">Record cash, UPI or gateway</p>
              </Link>

              <Link
                href="/admin/receipts"
                className="group rounded-md border border-rule bg-white p-3.5 transition-colors hover:border-slate-400"
              >
                <div className="flex items-center gap-2 text-ink text-xs font-medium">
                  <FileText className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                  <span>Receipts ledger</span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">Official numbered receipts</p>
              </Link>

              <Link
                href="/admin/import"
                className="group rounded-md border border-rule bg-white p-3.5 transition-colors hover:border-slate-400"
              >
                <div className="flex items-center gap-2 text-ink text-xs font-medium">
                  <Download className="h-4 w-4 text-slate-400 group-hover:text-blue-600" />
                  <span>CSV bulk import</span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">Upload batch student files</p>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Defaulters & Outstanding Dues Roster */}
      {activeTab === "defaulters" && (
        <div className="rounded-lg border border-rule bg-white overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 border-b border-rule">
            <div>
              <h3 className="text-sm font-semibold text-ink">Students with outstanding fees</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Send an individual WhatsApp fee reminder or broadcast to all unpaid accounts.
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setBroadcastOpen(true)}
              className="gap-1.5 shrink-0"
            >
              <Send className="h-3.5 w-3.5 text-slate-500" />
              Broadcast to all ({overdueCount})
            </Button>
          </div>

          {outstandingLoading ? (
            <div className="p-6 space-y-3">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : !outstandingData || outstandingData.items.length === 0 ? (
            <div className="py-16 text-center text-xs text-slate-500">
              <p className="font-semibold text-ink text-sm">No outstanding dues</p>
              <p className="mt-1 text-slate-500">All registered student accounts are settled.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Name</th>
                    <th>Course</th>
                    <th>Contact</th>
                    <th>Oldest due</th>
                    <th className="num">Outstanding</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {outstandingData.items.map((row) => (
                    <tr key={row.student_id}>
                      <td className="font-mono text-xs text-slate-600">{row.id_no}</td>
                      <td className="font-medium text-ink">
                        <Link
                          href={`/admin/students/${row.student_id}`}
                          className="hover:underline hover:text-blue-700"
                        >
                          {row.name}
                        </Link>
                      </td>
                      <td className="text-slate-600">{row.course_name || "General"}</td>
                      <td className="font-mono text-xs text-slate-600">
                        {row.contact || <span className="text-slate-400 italic">No phone</span>}
                      </td>
                      <td className="text-slate-600">
                        {row.oldest_due_date ? formatDate(row.oldest_due_date) : "Immediate"}
                      </td>
                      <td className="num font-semibold text-rose-700">
                        {formatCurrency(row.outstanding_paise || row.overdue_paise)}
                      </td>
                      <td className="text-right whitespace-nowrap">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenNotice(row)}
                          className="h-7 px-2.5 text-xs gap-1.5"
                        >
                          <MessageSquare className="h-3 w-3 text-slate-500" />
                          Notice
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Data Exports */}
      {activeTab === "reports" && (
        <div className="rounded-lg border border-rule bg-white p-6 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-ink">Official data exports</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Download clean CSV ledgers for external accounting, audits, and compliance records.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="rounded-md border border-rule p-4 flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-ink">Enrolled students ledger</p>
                <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                  Full student master records: student ID, guardian, course, admission date, and current fee status.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-rule">
                <a href={reportsApi.exportStudentsUrl()} download="students_ledger.csv">
                  <Button variant="outline" size="sm" className="w-full text-xs gap-1.5">
                    <Download className="h-3.5 w-3.5" />
                    Download students CSV
                  </Button>
                </a>
              </div>
            </div>

            <div className="rounded-md border border-rule p-4 flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-ink">Fee schedules & dues</p>
                <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                  Itemized dues, installment schedules, concessions, and outstanding balances.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-rule">
                <a href={reportsApi.exportFeesUrl()} download="fee_schedules.csv">
                  <Button variant="outline" size="sm" className="w-full text-xs gap-1.5">
                    <Download className="h-3.5 w-3.5" />
                    Download fees CSV
                  </Button>
                </a>
              </div>
            </div>

            <div className="rounded-md border border-rule p-4 flex flex-col justify-between">
              <div>
                <p className="text-xs font-semibold text-ink">Payment transactions log</p>
                <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                  Complete settlement ledger: Cash, UPI, and Razorpay transactions with receipt numbers.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-rule">
                <a href={reportsApi.exportPaymentsUrl()} download="payments_log.csv">
                  <Button variant="outline" size="sm" className="w-full text-xs gap-1.5">
                    <Download className="h-3.5 w-3.5" />
                    Download payments CSV
                  </Button>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Master WhatsApp Broadcast Dialog */}
      <BroadcastNoticesDialog
        open={broadcastOpen}
        onOpenChange={setBroadcastOpen}
        defaultProgram="ALL"
      />

      {/* Individual WhatsApp Notice Modal */}
      <WhatsAppNoticeDialog
        student={whatsappStudent}
        open={!!whatsappStudent}
        onOpenChange={(open) => {
          if (!open) setWhatsappStudent(null);
        }}
      />
    </div>
  );
}
