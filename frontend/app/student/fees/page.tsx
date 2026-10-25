"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api/students";
import { feesApi } from "@/lib/api/fees";
import { paymentsApi } from "@/lib/api/payments";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { RazorpayCheckoutModal } from "@/components/payments/razorpay-checkout";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";
import {
  CreditCard,
  AlertCircle,
  Clock,
  CheckCircle2,
  Lock,
} from "lucide-react";
import type { Fee } from "@/types/api";

export default function StudentFeesPage() {
  const [payingFee, setPayingFee] = useState<Fee | null>(null);

  const { data: student } = useQuery({
    queryKey: ["student-me"],
    queryFn: () => studentsApi.me(),
  });

  const studentId = student?.id;

  const { data: feeSummary, isLoading: summaryLoading } = useQuery({
    queryKey: ["student-fee-summary", studentId],
    queryFn: () => feesApi.summary(studentId!),
    enabled: !!studentId,
  });

  const { data: feesData, isLoading: feesLoading } = useQuery({
    queryKey: ["student-fees", studentId],
    queryFn: () => feesApi.list({ student_id: studentId!, page_size: 50 }),
    enabled: !!studentId,
  });

  const { data: paymentsData, isLoading: paymentsLoading } = useQuery({
    queryKey: ["student-payments", studentId],
    queryFn: () => paymentsApi.list({ student_id: studentId!, page_size: 50 }),
    enabled: !!studentId,
  });

  const fees = feesData?.items || [];
  const payments = paymentsData?.items || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Fee Dues & Online Payments
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          View tuition schedules, settle dues securely online via UPI/Card, and verify digital receipts.
        </p>
      </div>

      {/* Current Month (October 2026) Status Banner */}
      <Card
        className={`p-4 border ${
          student?.current_month_status === "PAID"
            ? "border-emerald-200 bg-emerald-50/50"
            : "border-rose-200 bg-rose-50/50"
        }`}
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${
                student?.current_month_status === "PAID"
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-rose-100 text-rose-700"
              }`}
            >
              {student?.current_month_status === "PAID" ? (
                <CheckCircle2 className="h-5 w-5" />
              ) : (
                <AlertCircle className="h-5 w-5" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-slate-900">
                  October 2026 Monthly Tuition:
                </h3>
                <Badge
                  variant={
                    student?.current_month_status === "PAID" ? "success" : "danger"
                  }
                >
                  {student?.current_month_status === "PAID" ? "PAID" : "UNPAID / DUE"}
                </Badge>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                {student?.current_month_status === "PAID"
                  ? "Your October 2026 tuition is fully settled."
                  : student?.due_months_count && student.due_months_count > 1
                  ? `${student.due_months_count} total months currently due (${student.unpaid_months?.slice(0, 3).join(", ")}${student.unpaid_months && student.unpaid_months.length > 3 ? "..." : ""}). Settle recent to past below.`
                  : "October 2026 tuition fee is due. Settle online below."}
              </p>
            </div>
          </div>
          {student?.total_due_paise && student.total_due_paise > 0 ? (
            <div className="text-right">
              <span className="text-[11px] font-medium text-slate-500 block">Total Due Balance</span>
              <span className="text-lg font-bold text-rose-700 font-mono">
                {formatCurrency(student.total_due_paise)}
              </span>
            </div>
          ) : null}
        </div>
      </Card>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-5">
          <span className="text-xs font-medium text-slate-500">Total Program Fee</span>
          {summaryLoading ? (
            <Skeleton className="mt-2 h-7 w-24" />
          ) : (
            <p className="mt-2 text-2xl font-bold text-slate-900 tabular">
              {formatCurrency(feeSummary?.total_amount_paise)}
            </p>
          )}
          <p className="mt-1 text-[11px] text-slate-400">Scheduled course fee</p>
        </Card>

        <Card className="p-5">
          <span className="text-xs font-medium text-slate-500">Total Paid</span>
          {summaryLoading ? (
            <Skeleton className="mt-2 h-7 w-24" />
          ) : (
            <p className="mt-2 text-2xl font-bold text-emerald-600 tabular">
              {formatCurrency(feeSummary?.total_paid_paise)}
            </p>
          )}
          <p className="mt-1 text-[11px] text-slate-400">Settled and receipted</p>
        </Card>

        <Card className="p-5 border-blue-200 bg-blue-50/30">
          <span className="text-xs font-medium text-blue-900">Current Balance Due</span>
          {summaryLoading ? (
            <Skeleton className="mt-2 h-7 w-24" />
          ) : (
            <p className="mt-2 text-2xl font-bold text-blue-700 tabular">
              {formatCurrency(feeSummary?.total_outstanding_paise)}
            </p>
          )}
          {feeSummary && feeSummary.overdue_paise > 0 ? (
            <p className="mt-1 text-[11px] font-medium text-rose-600">
              Includes {formatCurrency(feeSummary.overdue_paise)} overdue
            </p>
          ) : (
            <p className="mt-1 text-[11px] text-blue-600">All installments on track</p>
          )}
        </Card>
      </div>

      {/* Scheduled Fee Items & Pay Now Actions */}
      <Card className="overflow-hidden shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base flex items-center justify-between">
            <span>Scheduled Monthly Fees & Dues (Recent to Past)</span>
            <Lock className="h-4 w-4 text-slate-400" />
          </CardTitle>
          <CardDescription className="text-xs">
            Pay for current October 2026 tuition and past due months directly online via UPI/Card.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {feesLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : fees.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={<CreditCard className="h-8 w-8" />}
                title="No fee items scheduled"
                description="Your fee plan has not been assigned by the administration."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Fee Item</th>
                    <th className="py-2.5 px-4">Due Date</th>
                    <th className="py-2.5 px-4">Amount</th>
                    <th className="py-2.5 px-4">Paid</th>
                    <th className="py-2.5 px-4">Balance</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4 text-right">Payment</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {fees.map((fee) => {
                    const isPayable =
                      fee.balance_paise > 0 && fee.status !== "CANCELLED";
                    const isCurrentMonth = fee.due_date.startsWith("2026-10") || fee.title.toLowerCase().includes("oct");
                    return (
                      <tr key={fee.id} className={isCurrentMonth ? "bg-blue-50/30 hover:bg-blue-50/50" : "hover:bg-slate-50/50"}>
                        <td className="py-3 px-4 font-semibold text-slate-900">
                          <div className="flex items-center gap-1.5">
                            <span>{fee.title}</span>
                            {isCurrentMonth && (
                              <span className="text-[10px] font-bold uppercase bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                Current Month
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-600">{formatDate(fee.due_date)}</td>
                        <td className="py-3 px-4 text-slate-900">{formatCurrency(fee.amount_paise)}</td>
                        <td className="py-3 px-4 text-emerald-600 font-medium">
                          {formatCurrency(fee.paid_paise)}
                        </td>
                        <td className="py-3 px-4 font-bold text-slate-900">
                          {formatCurrency(fee.balance_paise)}
                        </td>
                        <td className="py-3 px-4">
                          <Badge
                            variant={
                              fee.status === "PAID"
                                ? "success"
                                : fee.status === "OVERDUE"
                                ? "danger"
                                : fee.status === "PARTIALLY_PAID"
                                ? "warning"
                                : "default"
                            }
                          >
                            {fee.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-right">
                          {isPayable ? (
                            <Button
                              variant="accent"
                              size="sm"
                              className="h-7 text-xs font-semibold px-3 shadow-xs"
                              onClick={() => setPayingFee(fee)}
                            >
                              PAY NOW
                            </Button>
                          ) : (
                            <span className="text-xs text-emerald-600 font-medium flex items-center justify-end gap-1">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              Settled
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Previous Payments History */}
      <Card className="overflow-hidden shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base">Payment History</CardTitle>
          <CardDescription className="text-xs">
            Past transactions and settlement confirmation logs
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {paymentsLoading ? (
            <div className="p-6 space-y-2">
              {[1, 2].map((i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : payments.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              No previous transactions recorded.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Date</th>
                    <th className="py-2.5 px-4">Amount</th>
                    <th className="py-2.5 px-4">Provider</th>
                    <th className="py-2.5 px-4">Method</th>
                    <th className="py-2.5 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {payments.map((p) => (
                    <tr key={p.id}>
                      <td className="py-2.5 px-4 text-slate-600">
                        {formatDateTime(p.paid_at || p.created_at)}
                      </td>
                      <td className="py-2.5 px-4 font-bold text-slate-900">
                        {formatCurrency(p.amount_paise)}
                      </td>
                      <td className="py-2.5 px-4 font-mono text-slate-600">{p.provider}</td>
                      <td className="py-2.5 px-4 uppercase text-[11px] text-slate-600">
                        {p.method || "—"}
                      </td>
                      <td className="py-2.5 px-4">
                        <Badge variant={p.status === "SUCCESS" ? "success" : "default"}>
                          {p.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Razorpay Online Checkout Modal */}
      <RazorpayCheckoutModal
        fee={payingFee}
        open={!!payingFee}
        onOpenChange={(open) => !open && setPayingFee(null)}
      />
    </div>
  );
}
