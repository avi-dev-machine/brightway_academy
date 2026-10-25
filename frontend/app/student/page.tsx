"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { studentsApi } from "@/lib/api/students";
import { feesApi } from "@/lib/api/fees";
import { attendanceApi } from "@/lib/api/attendance";
import { paymentsApi } from "@/lib/api/payments";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, MetricStrip, Metric, SectionHeading } from "@/components/ui/page";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  CreditCard,
  FileText,
  CalendarCheck,
  User,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export default function StudentDashboardPage() {
  const { data: student, isLoading: studentLoading } = useQuery({
    queryKey: ["student-me"],
    queryFn: () => studentsApi.me(),
  });

  const studentId = student?.id;

  const { data: feeSummary, isLoading: summaryLoading } = useQuery({
    queryKey: ["student-fee-summary", studentId],
    queryFn: () => feesApi.summary(studentId!),
    enabled: !!studentId,
  });

  const { data: attendance, isLoading: attendanceLoading } = useQuery({
    queryKey: ["student-attendance", studentId],
    queryFn: () => attendanceApi.getStudentAttendance(studentId!),
    enabled: !!studentId,
  });

  const { data: recentPayments, isLoading: paymentsLoading } = useQuery({
    queryKey: ["student-recent-payments", studentId],
    queryFn: () => paymentsApi.list({ student_id: studentId!, page_size: 4 }),
  });

  const courseTitle = student?.course_name || student?.legacy_course || "Enrolled Course";
  const hasOverdue = (feeSummary?.overdue_paise ?? 0) > 0;

  return (
    <div className="space-y-8">
      {/* Student Page Header */}
      <PageHeader
        title={studentLoading ? <Skeleton className="h-8 w-48" /> : student?.name || "Student Portal"}
        description={
          studentLoading ? (
            <Skeleton className="h-4 w-72 mt-1" />
          ) : (
            <span>
              {courseTitle} · Student ID:{" "}
              <span className="font-mono text-ink font-medium">{student?.id_no}</span>
            </span>
          )
        }
        actions={
          <div className="flex items-center gap-2">
            <Link href="/student/fees">
              <Button variant="default" size="sm" className="gap-1.5">
                <CreditCard className="h-3.5 w-3.5" />
                Pay fees online
              </Button>
            </Link>
            <Link href="/student/profile">
              <Button variant="outline" size="sm" className="gap-1.5">
                <User className="h-3.5 w-3.5 text-slate-500" />
                Academic record
              </Button>
            </Link>
          </div>
        }
      />

      {/* Primary Key Metrics */}
      <MetricStrip>
        <Metric
          label="Fee balance"
          tone={hasOverdue ? "danger" : "default"}
          value={
            summaryLoading ? (
              <Skeleton className="h-7 w-28" />
            ) : (
              formatCurrency(feeSummary?.total_outstanding_paise)
            )
          }
          detail={
            summaryLoading ? null : hasOverdue ? (
              <span className="text-rose-700 font-medium">
                {formatCurrency(feeSummary?.overdue_paise)} overdue
              </span>
            ) : (
              "All scheduled dues up to date"
            )
          }
        />

        <Metric
          label="Attendance rate"
          value={
            attendanceLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : attendance?.summary?.percentage !== null && attendance?.summary?.percentage !== undefined ? (
              `${Math.round(attendance.summary.percentage)}%`
            ) : (
              "—"
            )
          }
          detail={
            attendanceLoading ? null : (
              <span>
                {attendance?.summary?.present ?? 0} present · {attendance?.summary?.absent ?? 0} absent
              </span>
            )
          }
        />

        <Metric
          label="Enrolled program"
          value={
            studentLoading ? (
              <Skeleton className="h-7 w-24" />
            ) : student?.program === "CERTIFICATE" ? (
              "Diploma"
            ) : (
              "Foundation"
            )
          }
          detail={student?.admission_date ? `Admitted ${formatDate(student.admission_date)}` : "Active enrollment"}
        />

        <Metric
          label="Identity credentials"
          value={
            studentLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : student?.has_id_card ? (
              "Issued"
            ) : (
              "Pending"
            )
          }
          detail={student?.has_id_card ? "Digital card verified" : "Awaiting admin issuance"}
        />
      </MetricStrip>

      {/* Main Content Workspace: Fees & Attendance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Fees & Settlement (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-lg border border-rule bg-white p-6 space-y-4">
            <SectionHeading
              title="Tuition & scheduled dues"
              description="Review your pending fee installments and make instant digital settlements."
              action={
                <Link
                  href="/student/fees"
                  className="text-xs text-blue-700 hover:underline font-medium inline-flex items-center gap-1"
                >
                  Fee details
                  <ArrowRight className="h-3 w-3" />
                </Link>
              }
            />

            {summaryLoading ? (
              <div className="space-y-2 pt-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <div className="pt-2">
                <div className="flex items-center justify-between py-3 border-b border-rule">
                  <div>
                    <p className="text-sm font-medium text-ink">Total outstanding balance</p>
                    <p className="text-xs text-slate-500">Scheduled course installments remaining</p>
                  </div>
                  <p className="text-lg font-semibold text-ink tabular">
                    {formatCurrency(feeSummary?.total_outstanding_paise)}
                  </p>
                </div>

                {hasOverdue && (
                  <div className="flex items-center justify-between py-3 border-b border-rule bg-rose-50/50 -mx-6 px-6">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-rose-700" />
                      <div>
                        <p className="text-sm font-medium text-rose-900">Overdue installment notice</p>
                        <p className="text-xs text-rose-700">Please settle immediately to avoid enrollment hold</p>
                      </div>
                    </div>
                    <p className="text-base font-semibold text-rose-700 tabular">
                      {formatCurrency(feeSummary?.overdue_paise)}
                    </p>
                  </div>
                )}

                <div className="pt-4 flex items-center justify-between">
                  <div className="text-xs text-slate-500">
                    Supports UPI (GPay, PhonePe, Paytm), NetBanking, and RuPay cards.
                  </div>
                  <Link href="/student/fees">
                    <Button variant="default" size="sm">
                      Settle fee dues
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* Recent Payment Ledger */}
          <div className="rounded-lg border border-rule bg-white overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-rule">
              <div>
                <h3 className="text-sm font-semibold text-ink">Payment history</h3>
                <p className="text-xs text-slate-500 mt-0.5">Most recent verified fee settlements</p>
              </div>
              <Link
                href="/student/receipts"
                className="text-xs text-blue-700 hover:underline font-medium inline-flex items-center gap-1"
              >
                All receipts
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            {paymentsLoading ? (
              <div className="p-6 space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : !recentPayments?.items || recentPayments.items.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                No payment transactions recorded yet.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Reference</th>
                    <th>Method</th>
                    <th className="num">Amount</th>
                    <th className="text-right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentPayments.items.map((p) => (
                    <tr key={p.id}>
                      <td className="text-slate-600">
                        {formatDate(p.paid_at || p.created_at)}
                      </td>
                      <td className="font-mono text-xs text-slate-500">
                        {p.reference || p.provider_payment_id || "Direct"}
                      </td>
                      <td className="text-slate-600">
                        {p.method || p.provider}
                      </td>
                      <td className="num font-medium text-ink">
                        {formatCurrency(p.amount_paise)}
                      </td>
                      <td className="text-right">
                        <Badge variant={p.status === "SUCCESS" ? "success" : "default"}>
                          {p.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Column: Attendance & Quick Navigation (1 col) */}
        <div className="space-y-6">
          {/* Attendance Card */}
          <div className="rounded-lg border border-rule bg-white p-5 space-y-4">
            <div className="flex items-baseline justify-between border-b border-rule pb-3">
              <div>
                <h3 className="text-sm font-semibold text-ink">Attendance summary</h3>
                <p className="text-xs text-slate-500 mt-0.5">Classroom check-in participation</p>
              </div>
              <CalendarCheck className="h-4 w-4 text-slate-400" />
            </div>

            {attendanceLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <div className="space-y-3">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-slate-500">Present sessions:</span>
                  <span className="text-sm font-semibold text-emerald-700 tabular">
                    {attendance?.summary?.present ?? 0}
                  </span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-slate-500">Absences:</span>
                  <span className="text-sm font-semibold text-rose-700 tabular">
                    {attendance?.summary?.absent ?? 0}
                  </span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-slate-500">Overall attendance:</span>
                  <span className="text-sm font-bold text-ink tabular">
                    {attendance?.summary?.percentage !== null && attendance?.summary?.percentage !== undefined
                      ? `${Math.round(attendance.summary.percentage)}%`
                      : "—"}
                  </span>
                </div>

                <div className="pt-2 border-t border-rule">
                  <Link href="/student/attendance" className="block">
                    <Button variant="outline" size="sm" className="w-full justify-between text-xs">
                      Full attendance calendar
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </div>

          {/* Academic Portal Shortcuts */}
          <div className="rounded-lg border border-rule bg-white p-5 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Workspace actions
            </h3>
            <div className="space-y-2">
              <Link
                href="/student/receipts"
                className="flex items-center justify-between p-2.5 rounded-md border border-rule hover:border-slate-400 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <FileText className="h-4 w-4 text-slate-400" />
                  <span className="text-xs font-medium text-ink">Download tax receipts</span>
                </div>
                <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
              </Link>

              <Link
                href="/student/profile"
                className="flex items-center justify-between p-2.5 rounded-md border border-rule hover:border-slate-400 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <User className="h-4 w-4 text-slate-400" />
                  <span className="text-xs font-medium text-ink">Official student ID card</span>
                </div>
                <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
