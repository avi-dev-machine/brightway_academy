"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { feesApi } from "@/lib/api/fees";
import { coursesApi } from "@/lib/api/courses";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "sonner";
import {
  CreditCard,
  Plus,
  Layers,
  FileCheck2,
} from "lucide-react";
import Link from "next/link";
import type { Fee, FeeStatus, OfflineMethod } from "@/types/api";

export default function AdminFeesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<FeeStatus | "">("");

  // Offline Payment modal
  const [offlineFee, setOfflineFee] = useState<Fee | null>(null);
  const [offlineAmount, setOfflineAmount] = useState("");
  const [offlineMethod, setOfflineMethod] = useState<OfflineMethod>("CASH");
  const [offlineRef, setOfflineRef] = useState("");

  const { data: feesData, isLoading } = useQuery({
    queryKey: ["admin-fees", page, statusFilter],
    queryFn: () =>
      feesApi.list({
        page,
        page_size: 15,
        status: statusFilter || undefined,
      }),
  });

  const fees = feesData?.items || [];
  const meta = feesData?.meta;

  const recordOfflineMutation = useMutation({
    mutationFn: () => {
      const paise = Math.round(parseFloat(offlineAmount) * 100);
      return feesApi.recordOfflinePayment(offlineFee!.id, {
        amount_paise: paise,
        method: offlineMethod,
        reference: offlineRef || null,
      });
    },
    onSuccess: () => {
      toast.success("Payment recorded and receipt generated.");
      setOfflineFee(null);
      queryClient.invalidateQueries({ queryKey: ["admin-fees"] });
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
      queryClient.invalidateQueries({ queryKey: ["student-monthly-fees"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard"] });
    },
    onError: () => toast.error("Unable to record offline payment."),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Monthly Fee Collections & Settlements
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Monitor monthly fee dues, record offline cash/UPI collections, and generate official receipts.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/admin/students?fee_status=UNPAID">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs text-amber-700 border-amber-200 bg-amber-50/50 hover:bg-amber-100/60">
              <CreditCard className="h-3.5 w-3.5" />
              View Unpaid Student Dues
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter Toolbar */}
      <Card className="p-4 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-600">Filter Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as FeeStatus | "");
                setPage(1);
              }}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
            >
              <option value="">All Fee Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="PARTIALLY_PAID">Partially Paid</option>
              <option value="PAID">Paid</option>
              <option value="OVERDUE">Overdue</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Fees Table */}
      <Card className="overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : fees.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<CreditCard className="h-8 w-8" />}
              title="No fee records found"
              description="No fee records match the selected status filter."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Fee Item</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Total Amount</th>
                  <th className="py-3 px-4">Paid</th>
                  <th className="py-3 px-4">Balance</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {fees.map((fee) => (
                  <tr key={fee.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-semibold text-slate-900">{fee.title}</td>
                    <td className="py-3 px-4 text-slate-600">{formatDate(fee.due_date)}</td>
                    <td className="py-3 px-4 font-medium text-slate-900">
                      {formatCurrency(fee.amount_paise)}
                    </td>
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
                      {fee.balance_paise > 0 && fee.status !== "CANCELLED" && (
                        <Button
                          variant="primary"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => {
                            setOfflineFee(fee);
                            setOfflineAmount((fee.balance_paise / 100).toFixed(2));
                          }}
                        >
                          Collect
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

      {/* Collect Offline Payment Modal */}
      <Dialog open={!!offlineFee} onOpenChange={(open) => !open && setOfflineFee(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Record Payment — {offlineFee?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Amount to Collect (INR ₹) *
              </label>
              <Input
                type="number"
                step="0.01"
                value={offlineAmount}
                onChange={(e) => setOfflineAmount(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Method *</label>
              <select
                value={offlineMethod}
                onChange={(e) => setOfflineMethod(e.target.value as OfflineMethod)}
                className="w-full h-9.5 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
              >
                <option value="CASH">Cash</option>
                <option value="UPI">UPI</option>
                <option value="BANK_TRANSFER">Bank Transfer</option>
                <option value="CHEQUE">Cheque</option>
                <option value="CARD">Card (POS)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Reference / Notes (optional)
              </label>
              <Input
                placeholder="Transaction ID / Receipt Remark"
                value={offlineRef}
                onChange={(e) => setOfflineRef(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="pt-3">
            <Button variant="outline" onClick={() => setOfflineFee(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={recordOfflineMutation.isPending}
              onClick={() => recordOfflineMutation.mutate()}
            >
              Confirm Collection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
