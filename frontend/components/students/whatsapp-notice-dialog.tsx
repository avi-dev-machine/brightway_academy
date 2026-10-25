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
import { formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import {
  MessageSquare,
  Send,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Copy,
} from "lucide-react";
import type { Student, DueFeeNoticeResult } from "@/types/api";

export interface WhatsAppNoticeStudent {
  id: string;
  name: string;
  id_no?: string | null;
  contact?: string | null;
  contact_e164?: string | null;
  course_name?: string | null;
  legacy_course?: string | null;
  unpaid_months?: string[];
  due_months_count?: number;
  monthly_fee_paise?: number;
  total_due_paise?: number;
  outstanding_paise?: number;
  overdue_paise?: number;
}

interface WhatsAppNoticeDialogProps {
  student: WhatsAppNoticeStudent | Student | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function WhatsAppNoticeDialog({
  student,
  open,
  onOpenChange,
}: WhatsAppNoticeDialogProps) {
  const queryClient = useQueryClient();
  const [customNote, setCustomNote] = useState("");
  const [lastResult, setLastResult] = useState<DueFeeNoticeResult | null>(null);

  const notifyMutation = useMutation({
    mutationFn: () => {
      if (!student) throw new Error("No student selected");
      return studentsApi.notifyDueFee(student.id, customNote.trim() || undefined);
    },
    onSuccess: (data) => {
      setLastResult(data);
      toast.success(`Fee notice queued for ${student?.name} via WhatsApp.`);
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-stats"] });
      queryClient.invalidateQueries({ queryKey: ["admin-outstanding-fees"] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to queue WhatsApp notification.";
      toast.error(msg);
    },
  });

  if (!student) return null;

  // Calculate default due amount if not pre-attached
  const dueMonths = student.unpaid_months || [];
  const ratePaise = student.monthly_fee_paise || 40000;
  const outstandingExtra =
    "outstanding_paise" in student && typeof student.outstanding_paise === "number"
      ? student.outstanding_paise
      : 0;
  const overdueExtra =
    "overdue_paise" in student && typeof student.overdue_paise === "number"
      ? student.overdue_paise
      : 0;
  const totalDuePaise =
    student.total_due_paise ||
    outstandingExtra ||
    overdueExtra ||
    (dueMonths.length > 0 ? dueMonths.length * ratePaise : ratePaise);
  const formattedDue = formatCurrency(totalDuePaise);

  const cleanPhone = (student.contact_e164 || student.contact || "").replace(/\D/g, "");
  const directPhone = cleanPhone.startsWith("91") ? cleanPhone : `91${cleanPhone}`;

  const previewMessage = `Dear ${student.name},

This is a formal fee reminder from Brightway Computer Academy.

• Student ID: ${student.id_no || "Pending"}
• Course: ${student.course_name || student.legacy_course || "General"}
• Due Period: ${dueMonths.length > 0 ? dueMonths.join(", ") : "Current Session"}
• Total Outstanding: ${formattedDue}
${customNote.trim() ? `\nRemarks: ${customNote.trim()}\n` : ""}
Kindly settle your outstanding dues at the academy administration desk or via the online student portal.

Brightway Computer Academy`;

  const waLink = `https://wa.me/${directPhone}?text=${encodeURIComponent(previewMessage)}`;

  const copyNotice = () => {
    navigator.clipboard.writeText(previewMessage);
    toast.success("Notice copied to clipboard.");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto p-6">
        <DialogHeader className="pb-3 border-b border-rule">
          <DialogTitle className="text-base font-semibold text-ink flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-blue-700" />
            Send Fee Reminder via WhatsApp
          </DialogTitle>
          <p className="text-xs text-slate-500 mt-0.5">
            Dispatch an official fee statement to the registered phone number.
          </p>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Student Dues Summary Box */}
          <div className="rounded-md border border-rule bg-paper p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-xs font-semibold text-ink">
                  {student.name}
                </span>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  {student.id_no && (
                    <span className="font-mono text-[11px] text-slate-700 bg-white px-1.5 py-0.5 rounded-sm border border-rule">
                      {student.id_no}
                    </span>
                  )}
                  <span className="font-mono">{student.contact || "No contact on file"}</span>
                </div>
              </div>

              <div className="sm:text-right">
                <div className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">
                  Total Due
                </div>
                <div className="text-lg font-bold text-ink tabular">
                  {formattedDue}
                </div>
                {dueMonths.length > 0 && (
                  <div className="text-[11px] text-slate-500">
                    {dueMonths.length} month(s): {dueMonths.slice(0, 2).join(", ")}
                    {dueMonths.length > 2 && ` +${dueMonths.length - 2} more`}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Optional Note */}
          <div>
            <label className="block text-xs font-medium text-ink mb-1">
              Custom Remarks (Optional)
            </label>
            <Input
              placeholder="e.g. Please settle dues before Monday practical exam"
              value={customNote}
              onChange={(e) => setCustomNote(e.target.value)}
              className="text-xs"
            />
          </div>

          {/* WhatsApp Message Live Preview */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-slate-600">
                Notice Preview
              </span>
              <button
                type="button"
                onClick={copyNotice}
                className="inline-flex items-center gap-1 text-[11px] text-blue-700 hover:underline cursor-pointer"
              >
                <Copy className="h-3 w-3" />
                Copy text
              </button>
            </div>
            <div className="rounded-md border border-rule bg-slate-50 p-4 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed">
              {previewMessage}
            </div>
          </div>

          {/* Last Result Box */}
          {lastResult && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50/60 p-3.5 text-xs text-emerald-900 flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Notification queued</span>
                <p className="mt-0.5 text-emerald-800 text-[11px]">
                  Logged in academy message registry for {lastResult.contact || student.contact}.
                </p>
              </div>
            </div>
          )}

          {!student.contact && (
            <div className="rounded-md border border-amber-200 bg-amber-50/60 p-3 text-xs text-amber-900 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-amber-700 shrink-0" />
              <span>
                No registered phone number. Update the student contact before sending.
              </span>
            </div>
          )}
        </div>

        <DialogFooter className="pt-3 border-t border-rule flex flex-col sm:flex-row items-center justify-between gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            Close
          </Button>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            {/* Direct WhatsApp Web Link */}
            <a
              href={waLink}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto"
            >
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!student.contact}
                className="w-full sm:w-auto gap-1.5 text-xs"
                title="Open directly in WhatsApp Web / App"
              >
                <ExternalLink className="h-3.5 w-3.5 text-slate-500" />
                Open WhatsApp Web
              </Button>
            </a>

            {/* Automated Dispatch */}
            <Button
              type="button"
              variant="default"
              size="sm"
              disabled={!student.contact}
              isLoading={notifyMutation.isPending}
              onClick={() => notifyMutation.mutate()}
              className="w-full sm:w-auto gap-1.5 text-xs"
            >
              <Send className="h-3.5 w-3.5" />
              Dispatch via Academy Queue
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
