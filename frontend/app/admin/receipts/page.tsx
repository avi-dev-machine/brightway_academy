"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { receiptsApi } from "@/lib/api/receipts";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import { FileText, Download } from "lucide-react";

export default function AdminReceiptsPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-receipts", page],
    queryFn: () => receiptsApi.list({ page, page_size: 20 }),
  });

  const receipts = data?.items || [];
  const meta = data?.meta;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Payment Receipts
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Immutable historical audit receipts generated upon successful settlements.
        </p>
      </div>

      <Card className="overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : receipts.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<FileText className="h-8 w-8" />}
              title="No receipts recorded"
              description="Receipts will appear here when online or offline fee payments are settled."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Receipt Number</th>
                  <th className="py-3 px-4">Issued Timestamp</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4 text-right">PDF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {receipts.map((receipt) => (
                  <tr key={receipt.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-mono font-bold text-blue-600">
                      {receipt.receipt_number}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {formatDateTime(receipt.issued_at)}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      {formatCurrency(receipt.amount_paise)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <a
                        href={receiptsApi.downloadUrl(receipt.id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5">
                          <Download className="h-3.5 w-3.5" />
                          Download PDF
                        </Button>
                      </a>
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
