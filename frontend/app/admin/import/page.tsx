"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { importsApi } from "@/lib/api/imports";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { toast } from "sonner";
import {
  FileSpreadsheet,
  Upload,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  FileCheck,
} from "lucide-react";
import type { ImportErrorPolicy, ImportJob, ImportPreview } from "@/types/api";

export default function AdminCsvImportPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [uploadPercent, setUploadPercent] = useState<number | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [errorPolicy, setErrorPolicy] = useState<ImportErrorPolicy>("SKIP_ERRORS");
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [completedJob, setCompletedJob] = useState<ImportJob | null>(null);

  const previewMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return importsApi.preview(file, (percent) => setUploadPercent(percent));
    },
    onSuccess: (data) => {
      setPreview(data);
      toast.success("CSV analysed successfully. Review preview before confirmation.");
    },
    onError: (err: unknown) => {
      toast.error("Failed to parse CSV file. Please verify CSV column headers.");
    },
    onSettled: () => setUploadPercent(null),
  });

  const confirmMutation = useMutation({
    mutationFn: () => {
      if (!preview) throw new Error("No preview job");
      return importsApi.confirm(preview.job.id, {
        error_policy: errorPolicy,
        create_missing_courses: true,
      });
    },
    onSuccess: (job) => {
      setCompletedJob(job);
      setPreview(null);
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
      toast.success("Migration import executed successfully.");
    },
    onError: () => toast.error("Failed to execute CSV import."),
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      if (!selected.name.endsWith(".csv")) {
        toast.error("Please select a valid .csv file.");
        return;
      }
      setFile(selected);
      setPreview(null);
      setCompletedJob(null);
    }
  };

  const counts = preview?.job?.summary?.status_counts || {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Legacy Student Data CSV Migration
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Safely preview, validate, and migrate student cohorts from spreadsheet records.
        </p>
      </div>

      {/* Step 1 & 2: Upload CSV */}
      {!preview && !completedJob && (
        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5 text-blue-600" />
              Upload Student CSV
            </CardTitle>
            <CardDescription className="text-xs leading-relaxed">
              Required CSV headers: <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">ID No.</code>, <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">Name</code>, <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">Guardian&apos;s Name</code>, <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">Address</code>, <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">Contact No.</code>, <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">Course</code>.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-8 hover:bg-slate-50/50 transition-colors">
              <Upload className="h-10 w-10 text-slate-400 mb-2" />
              <p className="text-xs font-semibold text-slate-700">
                {file ? file.name : "Choose CSV file from your device"}
              </p>
              <p className="text-[11px] text-slate-400 mt-1">UTF-8 encoded comma-separated file</p>
              <label className="mt-4">
                <Button variant="outline" size="sm" type="button" className="pointer-events-none">
                  Browse Files
                </Button>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </label>
            </div>

            {uploadPercent !== null && (
              <div className="space-y-1">
                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 transition-all"
                    style={{ width: `${uploadPercent}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 text-center">Analysing CSV: {uploadPercent}%</p>
              </div>
            )}
          </CardContent>
          <CardFooter className="flex justify-end pt-0">
            <Button
              variant="primary"
              disabled={!file}
              isLoading={previewMutation.isPending}
              onClick={() => previewMutation.mutate()}
              className="gap-2"
            >
              Preview & Validate Rows
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardFooter>
        </Card>
      )}

      {/* Step 3, 4, 5: Preview Summary & Warnings */}
      {preview && (
        <div className="space-y-6">
          <Card>
            <CardHeader className="border-b border-slate-100 pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Pre-Import Summary</CardTitle>
                  <CardDescription className="text-xs">
                    File: {preview.job.filename} (SHA-256 verified)
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => {
                    setPreview(null);
                    setFile(null);
                  }}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1" />
                  Upload Different File
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
                <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium">Total Rows</span>
                  <p className="text-xl font-bold text-slate-900 mt-1">{preview.job.total_rows}</p>
                </div>
                <div className="rounded-lg bg-emerald-50 p-3 border border-emerald-200">
                  <span className="text-[11px] text-emerald-700 font-medium">Valid</span>
                  <p className="text-xl font-bold text-emerald-700 mt-1">{counts.VALID ?? 0}</p>
                </div>
                <div className="rounded-lg bg-amber-50 p-3 border border-amber-200">
                  <span className="text-[11px] text-amber-700 font-medium">Warnings</span>
                  <p className="text-xl font-bold text-amber-700 mt-1">{counts.WARNING ?? 0}</p>
                </div>
                <div className="rounded-lg bg-blue-50 p-3 border border-blue-200">
                  <span className="text-[11px] text-blue-700 font-medium">Already Exists</span>
                  <p className="text-xl font-bold text-blue-700 mt-1">{counts.EXISTS ?? 0}</p>
                </div>
                <div className="rounded-lg bg-rose-50 p-3 border border-rose-200">
                  <span className="text-[11px] text-rose-700 font-medium">Errors</span>
                  <p className="text-xl font-bold text-rose-700 mt-1">{counts.ERROR ?? 0}</p>
                </div>
              </div>

              {/* Policy selector */}
              <div className="mt-6 rounded-xl border border-slate-200 p-4 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h4 className="text-xs font-bold text-slate-900">Import Policy</h4>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    How the backend should treat invalid or error rows.
                  </p>
                </div>
                <select
                  value={errorPolicy}
                  onChange={(e) => setErrorPolicy(e.target.value as ImportErrorPolicy)}
                  className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
                >
                  <option value="SKIP_ERRORS">SKIP_ERRORS (Import valid, skip problem rows)</option>
                  <option value="STRICT">STRICT (Rollback if any row contains error)</option>
                </select>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end pt-2 border-t border-slate-100">
              <Button
                variant="primary"
                onClick={() => setConfirmModalOpen(true)}
                className="gap-2 text-xs"
              >
                Proceed with Confirmation
                <ArrowRight className="h-4 w-4" />
              </Button>
            </CardFooter>
          </Card>

          {/* Problem rows preview table */}
          {preview.problem_rows.length > 0 && (
            <Card className="overflow-hidden">
              <CardHeader className="pb-3 border-b border-slate-100">
                <CardTitle className="text-sm flex items-center gap-2 text-amber-800">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  Rows Requiring Attention ({preview.problem_rows.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto max-h-72">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                      <tr>
                        <th className="py-2.5 px-4">Row #</th>
                        <th className="py-2.5 px-4">Status</th>
                        <th className="py-2.5 px-4">Issue Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {preview.problem_rows.map((row) => (
                        <tr key={row.id}>
                          <td className="py-2.5 px-4 font-mono font-semibold text-slate-900">
                            {row.row_number}
                          </td>
                          <td className="py-2.5 px-4">
                            <Badge
                              variant={
                                row.status === "ERROR"
                                  ? "danger"
                                  : row.status === "WARNING"
                                  ? "warning"
                                  : "default"
                              }
                            >
                              {row.status}
                            </Badge>
                          </td>
                          <td className="py-2.5 px-4 text-slate-600">
                            {row.messages?.map((m, i) => (
                              <p key={i} className="text-[11px]">
                                {m.message || String(m.code)}
                              </p>
                            ))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Step 7: Completed Report */}
      {completedJob && (
        <Card className="border-emerald-200 bg-emerald-50/50 p-6 text-center max-w-xl mx-auto animate-fade-in">
          <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-600 mb-3" />
          <h3 className="text-lg font-bold text-slate-900">Import Job Completed</h3>
          <p className="text-xs text-slate-600 mt-1">
            Student cohort migrated into Postgres database with duplicate protection.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 max-w-sm mx-auto text-xs">
            <div className="bg-white p-3 rounded-lg border border-slate-200 text-left">
              <span className="text-slate-500">Imported Students:</span>
              <p className="font-bold text-emerald-600 text-base">
                {String(completedJob.summary?.imported ?? 0)}
              </p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 text-left">
              <span className="text-slate-500">Skipped (Existing):</span>
              <p className="font-bold text-slate-700 text-base">
                {String(completedJob.summary?.skipped_existing ?? 0)}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="mt-6"
            onClick={() => setCompletedJob(null)}
          >
            Import Another Batch
          </Button>
        </Card>
      )}

      {/* Confirmation Dialog (spec §36) */}
      <ConfirmDialog
        open={confirmModalOpen}
        onOpenChange={setConfirmModalOpen}
        title="Execute Database CSV Import"
        description={`This will write the valid student records into the academy database using policy "${errorPolicy}". Existing student ID numbers will be preserved.`}
        confirmLabel="Import Now"
        variant="primary"
        isLoading={confirmMutation.isPending}
        onConfirm={async () => {
          await confirmMutation.mutateAsync();
          setConfirmModalOpen(false);
        }}
      />
    </div>
  );
}
