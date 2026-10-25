"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api/students";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Send,
  Users,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import type { BroadcastDueNoticeResult } from "@/types/api";

interface BroadcastNoticesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  unpaidCountEstimate?: number;
  defaultProgram?: "ALL" | "CERTIFICATE" | "NON_CERTIFICATE";
}

export function BroadcastNoticesDialog({
  open,
  onOpenChange,
  unpaidCountEstimate = 0,
  defaultProgram,
}: BroadcastNoticesDialogProps) {
  const queryClient = useQueryClient();
  const [programFilter, setProgramFilter] = useState<
    "CERTIFICATE" | "NON_CERTIFICATE" | ""
  >(defaultProgram === "CERTIFICATE" || defaultProgram === "NON_CERTIFICATE" ? defaultProgram : "");
  const [customNote, setCustomNote] = useState("");
  const [result, setResult] = useState<BroadcastDueNoticeResult | null>(null);

  const broadcastMutation = useMutation({
    mutationFn: async () => {
      return studentsApi.notifyAllUnpaid({
        program: programFilter || undefined,
        custom_note: customNote.trim() || undefined,
      });
    },
    onSuccess: (data) => {
      setResult(data);
      toast.success(data.message);
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-stats"] });
      queryClient.invalidateQueries({ queryKey: ["admin-outstanding-fees"] });
    },
    onError: (err: unknown) => {
      const msg =
        err instanceof Error ? err.message : "Failed to broadcast fee notices.";
      toast.error(msg);
    },
  });

  const handleClose = () => {
    setResult(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto p-6">
        <DialogHeader className="pb-3 border-b border-rule">
          <DialogTitle className="text-base font-semibold text-ink flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-700" />
            Notify All Unpaid Students
          </DialogTitle>
          <p className="text-xs text-slate-500 mt-0.5">
            Batch-dispatch fee statements to active students with pending balances.
          </p>
        </DialogHeader>

        {!result ? (
          <div className="space-y-4 py-2">
            {/* Target Audience Note */}
            <div className="rounded-md border border-rule bg-paper p-4 text-xs">
              <p className="font-semibold text-ink">Broadcast Criteria</p>
              <p className="mt-1 text-slate-600 leading-relaxed">
                This process selects all active students with unsettled monthly dues or past-due fee schedules, builds an itemized notice, and enqueues a WhatsApp reminder for each student with a valid phone number.
              </p>
              {unpaidCountEstimate > 0 && (
                <p className="mt-2 text-slate-500 font-mono text-[11px]">
                  Estimated recipients: {unpaidCountEstimate} students
                </p>
              )}
            </div>

            {/* Program Filter & Custom Remarks */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-ink mb-1.5">
                  Program Category
                </label>
                <select
                  value={programFilter}
                  onChange={(e) =>
                    setProgramFilter(
                      e.target.value as "CERTIFICATE" | "NON_CERTIFICATE" | ""
                    )
                  }
                  className="select text-xs"
                >
                  <option value="">All Programs (Diploma &amp; Skill Tracks)</option>
                  <option value="CERTIFICATE">Certificate / Diploma Track Only</option>
                  <option value="NON_CERTIFICATE">Non-Certificate Track Only</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink mb-1.5">
                  Custom Notice Remarks (Optional)
                </label>
                <Input
                  placeholder="e.g. Please clear dues before next exam cycle"
                  value={customNote}
                  onChange={(e) => setCustomNote(e.target.value)}
                  className="text-xs"
                />
              </div>
            </div>

            {/* Template Preview */}
            <div className="rounded-md border border-rule bg-slate-50 p-4 font-mono text-xs text-slate-700 space-y-1">
              <p className="text-[11px] font-sans font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Standard Template Outline
              </p>
              <p>Dear [Student Name],</p>
              <p>This is a formal fee reminder from Brightway Computer Academy.</p>
              <p>• Student ID: [ID No]</p>
              <p>• Course: [Enrolled Course]</p>
              <p>• Due Period: [Unpaid Months List]</p>
              <p>• Total Outstanding: [₹ Due Amount]</p>
              {customNote.trim() && <p className="text-blue-700">Remarks: {customNote.trim()}</p>}
              <p className="text-slate-400">Kindly settle dues at the academy desk or student portal.</p>
            </div>
          </div>
        ) : (
          /* Broadcast Execution Results Summary */
          <div className="space-y-4 py-2 text-xs">
            <div className="rounded-md border border-emerald-200 bg-emerald-50/60 p-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-700 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-emerald-950">
                    Broadcast Completed
                  </h4>
                  <p className="mt-1 text-emerald-900 leading-relaxed">
                    {result.message}
                  </p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-3 border-t border-emerald-200/80 pt-3 text-center">
                <div>
                  <span className="text-[10px] text-emerald-800 uppercase font-medium">Unpaid Found</span>
                  <p className="text-lg font-bold text-emerald-950 tabular mt-0.5">
                    {result.total_unpaid}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-emerald-800 uppercase font-medium">Notices Queued</span>
                  <p className="text-lg font-bold text-emerald-700 tabular mt-0.5">
                    {result.queued_count}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-emerald-800 uppercase font-medium">Skipped (No Phone)</span>
                  <p className="text-lg font-bold text-slate-600 tabular mt-0.5">
                    {result.skipped_no_contact}
                  </p>
                </div>
              </div>
            </div>

            {/* List of Notified Students */}
            {result.notified_students && result.notified_students.length > 0 && (
              <div>
                <h4 className="font-semibold text-ink mb-2">
                  Queued Student Notices ({result.notified_students.length})
                </h4>
                <div className="max-h-56 overflow-y-auto rounded-md border border-rule">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Contact</th>
                        <th className="num">Due Amount</th>
                        <th className="text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.notified_students.map((item) => (
                        <tr key={item.student_id}>
                          <td className="font-medium text-ink">{item.student_name}</td>
                          <td className="font-mono text-xs text-slate-500">{item.contact || "—"}</td>
                          <td className="num font-semibold text-rose-700">{item.amount_formatted}</td>
                          <td className="text-right">
                            {item.whatsapp_url ? (
                              <a
                                href={item.whatsapp_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[11px] text-blue-700 hover:underline"
                              >
                                Web chat
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            ) : (
                              <Badge variant="outline">Queued</Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        <DialogFooter className="pt-3 border-t border-rule flex flex-col sm:flex-row items-center justify-between gap-2">
          {!result ? (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="default"
                size="sm"
                isLoading={broadcastMutation.isPending}
                onClick={() => broadcastMutation.mutate()}
                className="gap-1.5"
              >
                <Send className="h-3.5 w-3.5" />
                Dispatch Broadcast Notices
              </Button>
            </>
          ) : (
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={handleClose}
              className="ml-auto"
            >
              Done
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
