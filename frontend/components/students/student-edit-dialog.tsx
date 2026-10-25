"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api/students";
import { coursesApi } from "@/lib/api/courses";
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
import { toast } from "sonner";
import {
  UserCheck,
  CreditCard,
  GraduationCap,
  Sparkles,
} from "lucide-react";
import type { Student, StudentUpdate } from "@/types/api";

interface StudentEditDialogProps {
  student: Student | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (updated: Student) => void;
}

export function StudentEditDialog({
  student,
  open,
  onOpenChange,
  onSuccess,
}: StudentEditDialogProps) {
  const queryClient = useQueryClient();

  const [idNo, setIdNo] = useState("");
  const [name, setName] = useState("");
  const [guardianName, setGuardianName] = useState("");
  const [contact, setContact] = useState("");
  const [address, setAddress] = useState("");
  const [courseId, setCourseId] = useState("");
  const [program, setProgram] = useState<"CERTIFICATE" | "NON_CERTIFICATE" | "">("");
  const [monthlyFeeRupees, setMonthlyFeeRupees] = useState("");
  const [feeNotes, setFeeNotes] = useState("");
  const [passcode, setPasscode] = useState("");
  const [status, setStatus] = useState<"active" | "inactive">("active");
  const [admissionDate, setAdmissionDate] = useState("");

  const { data: coursesData } = useQuery({
    queryKey: ["courses-list-active"],
    queryFn: () => coursesApi.list({ active: true }),
    enabled: open,
  });

  useEffect(() => {
    if (student) {
      setIdNo(student.id_no || "");
      setName(student.name || "");
      setGuardianName(student.guardian_name || "");
      setContact(student.contact || "");
      setAddress(student.address || "");
      setCourseId(student.course_id || "");
      setProgram(student.program || "");
      setMonthlyFeeRupees(
        student.monthly_fee_paise != null
          ? String(Math.round(student.monthly_fee_paise / 100))
          : ""
      );
      setFeeNotes(student.fee_notes || "");
      setPasscode(student.initial_passcode || "");
      setStatus(student.status || "active");
      setAdmissionDate(student.admission_date || "");
    }
  }, [student]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!student) throw new Error("No student selected");

      const payload: StudentUpdate = {
        name: name.trim(),
        id_no: idNo.trim() ? idNo.trim() : null,
        guardian_name: guardianName.trim() ? guardianName.trim() : null,
        contact: contact.trim() ? contact.trim() : null,
        address: address.trim() ? address.trim() : null,
        course_id: courseId ? courseId : null,
        program: program ? program : null,
        monthly_fee_paise:
          monthlyFeeRupees.trim() && !isNaN(Number(monthlyFeeRupees))
            ? Math.round(Number(monthlyFeeRupees) * 100)
            : null,
        fee_notes: feeNotes.trim() ? feeNotes.trim() : null,
        initial_passcode: passcode.trim() ? passcode.trim() : null,
        status,
        admission_date: admissionDate || null,
      };

      return studentsApi.update(student.id, payload);
    },
    onSuccess: (updated) => {
      toast.success("Student record updated successfully.");
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
      queryClient.invalidateQueries({ queryKey: ["student", student?.id] });
      queryClient.invalidateQueries({ queryKey: ["admin-dashboard-stats"] });
      onOpenChange(false);
      if (updated && onSuccess) {
        onSuccess(updated);
      }
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to update student details.";
      toast.error(msg);
    },
  });

  const generateQuickPasscode = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    let code = "BW-";
    for (let i = 0; i < 4; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setPasscode(code);
    toast.info(`Generated temporary passcode: ${code}`);
  };

  if (!student) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto p-6">
        <DialogHeader className="pb-3 border-b border-rule">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-base font-semibold text-ink flex items-center gap-2">
                <UserCheck className="h-4 w-4 text-blue-700" />
                Edit Student Record
              </DialogTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                Assign or modify student ID, course track, contact, fees, or portal credentials.
              </p>
            </div>
            <Badge variant={status === "active" ? "success" : "default"}>
              {status.toUpperCase()}
            </Badge>
          </div>
        </DialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateMutation.mutate();
          }}
          className="space-y-4 py-2"
        >
          {/* Section: Academic Identity */}
          <div className="rounded-md bg-paper p-4 border border-rule space-y-3">
            <h4 className="text-xs font-semibold text-ink flex items-center gap-1.5">
              <GraduationCap className="h-4 w-4 text-slate-500" />
              Academic Identity &amp; Enrolment
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Student ID */}
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Student ID Number
                </label>
                <div className="relative">
                  <Input
                    placeholder="e.g. RG240019 (leave blank for pending)"
                    value={idNo}
                    onChange={(e) => setIdNo(e.target.value)}
                    className="font-mono text-xs uppercase"
                  />
                  {idNo && (
                    <button
                      type="button"
                      onClick={() => setIdNo("")}
                      className="absolute right-2.5 top-2.5 text-[10px] text-slate-400 hover:text-rose-600"
                      title="Clear ID No."
                    >
                      Clear
                    </button>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  Admin can assign, reassign, or clear this identifier anytime.
                </p>
              </div>

              {/* Full Name */}
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Full Name <span className="text-rose-600">*</span>
                </label>
                <Input
                  placeholder="Student Full Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="text-xs"
                  required
                />
              </div>

              {/* Program Track */}
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Program Category
                </label>
                <select
                  value={program}
                  onChange={(e) =>
                    setProgram(e.target.value as "CERTIFICATE" | "NON_CERTIFICATE" | "")
                  }
                  className="select text-xs"
                >
                  <option value="">General / Unassigned</option>
                  <option value="CERTIFICATE">Certificate Track (Exam &amp; Diploma)</option>
                  <option value="NON_CERTIFICATE">Non-Certificate Skill Track</option>
                </select>
              </div>

              {/* Course */}
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Assigned Course
                </label>
                <select
                  value={courseId}
                  onChange={(e) => setCourseId(e.target.value)}
                  className="select text-xs"
                >
                  <option value="">No Course Assigned</option>
                  {coursesData?.items?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Admission Date */}
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Admission Date
                </label>
                <Input
                  type="date"
                  value={admissionDate}
                  onChange={(e) => setAdmissionDate(e.target.value)}
                  className="text-xs"
                />
              </div>

              {/* Status */}
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Enrolment Status
                </label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value as "active" | "inactive")}
                  className="select text-xs"
                >
                  <option value="active">Active (Currently Enrolled)</option>
                  <option value="inactive">Inactive / Alumni</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section: Contact & Personal Details */}
          <div className="rounded-md bg-paper p-4 border border-rule space-y-3">
            <h4 className="text-xs font-semibold text-ink">
              Contact &amp; Guardian Information
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Contact Phone / WhatsApp
                </label>
                <Input
                  placeholder="e.g. 9876543210"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  className="font-mono text-xs"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Standard 10-digit mobile number for automated WhatsApp notices.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Guardian / Father&apos;s Name
                </label>
                <Input
                  placeholder="Guardian Name"
                  value={guardianName}
                  onChange={(e) => setGuardianName(e.target.value)}
                  className="text-xs"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-ink mb-1">
                  Residential Address
                </label>
                <Input
                  placeholder="Street, Locality, City"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="text-xs"
                />
              </div>
            </div>
          </div>

          {/* Section: Fees & Login Passcode */}
          <div className="rounded-md bg-paper p-4 border border-rule space-y-3">
            <h4 className="text-xs font-semibold text-ink flex items-center gap-1.5">
              <CreditCard className="h-4 w-4 text-slate-500" />
              Fee Structure &amp; Portal Passcode
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Monthly Fee Rate (INR ₹)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-xs text-slate-400 font-medium">₹</span>
                  <Input
                    type="number"
                    min="0"
                    placeholder="400"
                    value={monthlyFeeRupees}
                    onChange={(e) => setMonthlyFeeRupees(e.target.value)}
                    className="pl-7 text-xs font-semibold"
                  />
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  Rate charged on student ledger (e.g. ₹400/month).
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-ink mb-1">
                  Portal Login Passcode
                </label>
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. BW-7X9Q"
                    value={passcode}
                    onChange={(e) => setPasscode(e.target.value)}
                    className="font-mono text-xs"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={generateQuickPasscode}
                    className="h-9 px-2.5 text-xs shrink-0 gap-1"
                    title="Generate temporary code"
                  >
                    <Sparkles className="h-3 w-3 text-slate-500" />
                    Auto
                  </Button>
                </div>
                <p className="text-[10px] text-slate-500 mt-1">
                  Passcode used by student to log into portal.
                </p>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-ink mb-1">
                  Fee Notes &amp; Concession Remarks
                </label>
                <Input
                  placeholder="e.g. ₹50 concession approved by Principal, or fee paid till Dec"
                  value={feeNotes}
                  onChange={(e) => setFeeNotes(e.target.value)}
                  className="text-xs"
                />
              </div>
            </div>
          </div>

          <DialogFooter className="pt-3 border-t border-rule flex items-center justify-between sm:justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="default"
              size="sm"
              isLoading={updateMutation.isPending}
              className="gap-1.5"
            >
              <UserCheck className="h-4 w-4" />
              Save Record Changes
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
