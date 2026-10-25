"use client";

import { useQuery } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api/students";
import { receiptsApi } from "@/lib/api/receipts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import { FileText, Download } from "lucide-react";

export default function StudentReceiptsPage() {
  const { data: student } = useQuery({
    queryKey: ["student-me"],
    queryFn: () => studentsApi.me(),
  });

  const studentId = student?.id;

  const { data: receiptsData, isLoading } = useQuery({
    queryKey: ["student-receipts", studentId],
    queryFn: () => receiptsApi.list({ student_id: studentId!, page_size: 50 }),
    enabled: !!studentId,
  });

  const receipts = receiptsData?.items || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Payment Receipts
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Official immutable receipts for tuition payments. Download signed PDF copies anytime.
        </p>
      </div>

      <Card className="overflow-hidden shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base">Issued Receipts ({receipts.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : receipts.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={<FileText className="h-8 w-8" />}
                title="No receipts yet"
                description="Once an installment payment is completed and verified, your official receipt will appear here."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Receipt No.</th>
                    <th className="py-2.5 px-4">Issue Date</th>
                    <th className="py-2.5 px-4">Amount Paid</th>
                    <th className="py-2.5 px-4 text-right">Official PDF</th>
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
                      <td className="py-3 px-4 font-bold text-slate-900">
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
                            Download
                          </Button>
                        </a>
                      </td>
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
