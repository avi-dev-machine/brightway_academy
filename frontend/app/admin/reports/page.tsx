"use client";

import { Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { reportsApi } from "@/lib/api/reports";
import { coursesApi } from "@/lib/api/courses";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  BarChart3,
  Download,
  Calendar,
  FileSpreadsheet,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

/** ISO date (YYYY-MM-DD) for `days` days before now. */
function isoDaysAgo(days: number): string {
  return new Date(Date.now() - days * 24 * 3600 * 1000).toISOString().split("T")[0];
}

function AdminReportsContent() {
  // Lazy initialisers: "now" is read once on mount, not on every render.
  const [dateFrom, setDateFrom] = useState(() => isoDaysAgo(30));
  const [dateTo, setDateTo] = useState(() => isoDaysAgo(0));
  const [courseFilter, setCourseFilter] = useState<string>("");

  const { data: collections, isLoading: collectionsLoading } = useQuery({
    queryKey: ["reports-collections", dateFrom, dateTo],
    queryFn: () => reportsApi.getCollections({ date_from: dateFrom, date_to: dateTo }),
  });

  const { data: outstanding, isLoading: outstandingLoading } = useQuery({
    queryKey: ["reports-outstanding", courseFilter],
    queryFn: () =>
      reportsApi.getOutstanding({
        course_id: courseFilter || undefined,
        page_size: 25,
      }),
  });

  const { data: coursesData } = useQuery({
    queryKey: ["courses-active"],
    queryFn: () => coursesApi.list({ active: true }),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Academy Financial & Operational Reports
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time revenue collections, aging outstanding dues, and server-generated CSV exports.
          </p>
        </div>

        {/* CSV Export Quick Downloads */}
        <div className="flex flex-wrap items-center gap-2">
          <a href={reportsApi.exportStudentsUrl()} target="_blank" rel="noreferrer">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs">
              <Download className="h-3.5 w-3.5" />
              Export Students CSV
            </Button>
          </a>
          <a href={reportsApi.exportFeesUrl()} target="_blank" rel="noreferrer">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs">
              <Download className="h-3.5 w-3.5" />
              Export Fees CSV
            </Button>
          </a>
          <a
            href={reportsApi.exportPaymentsUrl({ date_from: dateFrom, date_to: dateTo })}
            target="_blank"
            rel="noreferrer"
          >
            <Button variant="outline" size="sm" className="gap-1.5 text-xs">
              <Download className="h-3.5 w-3.5" />
              Export Payments CSV
            </Button>
          </a>
        </div>
      </div>

      {/* Date Range Selector */}
      <Card className="p-4 shadow-2xs">
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
            <Calendar className="h-4 w-4 text-slate-400" />
            Collection Date Range:
          </span>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
            />
            <span className="text-xs text-slate-400">to</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
            />
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Collections Breakdown */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-slate-100 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Fee Collections</CardTitle>
                <p className="text-xs text-slate-500 mt-0.5">
                  Total: {formatCurrency(collections?.total_paise)} ({collections?.total_count ?? 0} tx)
                </p>
              </div>
              <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
                <TrendingUp className="h-4 w-4" />
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {collectionsLoading ? (
              <div className="p-6 space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !collections?.rows || collections.rows.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={<FileSpreadsheet className="h-8 w-8" />}
                  title="No collections in this range"
                  description="Adjust the dates above to see recorded fee payments."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Date</th>
                      <th className="py-2.5 px-4">Method</th>
                      <th className="py-2.5 px-4">Tx Count</th>
                      <th className="py-2.5 px-4 text-right">Collected</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {collections.rows.map((row, idx) => (
                      <tr key={idx}>
                        <td className="py-2.5 px-4 font-mono text-slate-700">{formatDate(row.day)}</td>
                        <td className="py-2.5 px-4 text-slate-600 uppercase text-[11px]">{row.method}</td>
                        <td className="py-2.5 px-4 text-slate-500">{row.count}</td>
                        <td className="py-2.5 px-4 text-right font-bold text-slate-900">
                          {formatCurrency(row.amount_paise)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Outstanding Dues Aging */}
        <Card className="overflow-hidden">
          <CardHeader className="border-b border-slate-100 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Aging Outstanding Fees</CardTitle>
                <p className="text-xs text-slate-500 mt-0.5">Filter by course to isolate cohorts</p>
              </div>
              <select
                value={courseFilter}
                onChange={(e) => setCourseFilter(e.target.value)}
                className="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs text-slate-700 focus:outline-blue-600 max-w-[160px]"
              >
                <option value="">All Courses</option>
                {coursesData?.items?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {outstandingLoading ? (
              <div className="p-6 space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : !outstanding?.items || outstanding.items.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={<AlertTriangle className="h-8 w-8" />}
                  title="No outstanding fees"
                  description="All scheduled fees for this cohort are settled or paid."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Student</th>
                      <th className="py-2.5 px-4">Outstanding</th>
                      <th className="py-2.5 px-4">Overdue</th>
                      <th className="py-2.5 px-4">Oldest Due</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {outstanding.items.map((row) => (
                      <tr key={row.student_id}>
                        <td className="py-2.5 px-4">
                          <p className="font-semibold text-slate-900">{row.name}</p>
                          <p className="font-mono text-[10px] text-slate-400">ID: {row.id_no}</p>
                        </td>
                        <td className="py-2.5 px-4 font-bold text-slate-900">
                          {formatCurrency(row.outstanding_paise)}
                        </td>
                        <td className="py-2.5 px-4 font-bold text-rose-600">
                          {formatCurrency(row.overdue_paise)}
                        </td>
                        <td className="py-2.5 px-4 text-slate-500">{formatDate(row.oldest_due_date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// The default date range depends on "now", which must be read at request time rather
// than baked into the prerendered page, so the content renders inside <Suspense>.
export default function AdminReportsPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <AdminReportsContent />
    </Suspense>
  );
}
