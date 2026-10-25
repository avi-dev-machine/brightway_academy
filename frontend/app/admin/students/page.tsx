"use client";

import { useState, Suspense } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { studentsApi } from "@/lib/api/students";
import { coursesApi } from "@/lib/api/courses";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/ui/pagination";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
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
  Search,
  UserPlus,
  Users,
  Eye,
  UserX,
  UserCheck,
  Image as ImageIcon,
  CreditCard,
  Copy,
  Check,
  Calendar,
  KeyRound,
  FileSpreadsheet,
  Pencil,
  MessageSquare,
  Send,
} from "lucide-react";
import { StudentEditDialog } from "@/components/students/student-edit-dialog";
import { WhatsAppNoticeDialog } from "@/components/students/whatsapp-notice-dialog";
import { BroadcastNoticesDialog } from "@/components/students/broadcast-notices-dialog";
import type { Student, StudentMonthlyFee, StudentStatus } from "@/types/api";


const createStudentSchema = z.object({
  id_no: z.string().optional(),
  name: z.string().min(2, "Full name is required"),
  guardian_name: z.string().optional(),
  contact: z.string().optional(),
  address: z.string().optional(),
  course_id: z.string().optional(),
  admission_date: z.string().optional(),
});

type CreateStudentForm = z.infer<typeof createStudentSchema>;

function StudentsManagementContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  // Read URL search params
  const page = parseInt(searchParams.get("page") || "1", 10);
  const q = searchParams.get("q") || "";
  const statusParam = (searchParams.get("status") as StudentStatus) || undefined;
  const courseId = searchParams.get("course_id") || undefined;
  const programParam = searchParams.get("program") || undefined;
  const hasIdParam = searchParams.get("has_id") || undefined;
  const feeStatusParam = (searchParams.get("fee_status") as "UNPAID" | "PAID") || undefined;

  const [searchInput, setSearchInput] = useState(q);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [deactivateStudent, setDeactivateStudent] = useState<Student | null>(null);
  const [feeHistoryStudent, setFeeHistoryStudent] = useState<Student | null>(null);
  const [editStudent, setEditStudent] = useState<Student | null>(null);
  const [whatsAppStudent, setWhatsAppStudent] = useState<Student | null>(null);
  const [broadcastOpen, setBroadcastOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);


  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    toast.success(`${label} copied to clipboard!`);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Update URL params
  const updateFilters = (updates: Record<string, string | undefined>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, val]) => {
      if (val === undefined || val === "") {
        params.delete(key);
      } else {
        params.set(key, val);
      }
    });
    router.push(`/admin/students?${params.toString()}`);
  };

  // Queries
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-students", page, q, statusParam, courseId, programParam, hasIdParam, feeStatusParam],
    queryFn: () =>
      studentsApi.list({
        page,
        page_size: 15,
        q: q || undefined,
        status: statusParam,
        course_id: courseId,
        program: programParam,
        has_id: hasIdParam === "true" ? true : hasIdParam === "false" ? false : undefined,
        fee_status: feeStatusParam,
      }),
  });

  const { data: coursesData } = useQuery({
    queryKey: ["courses-list-active"],
    queryFn: () => coursesApi.list({ active: true }),
  });

  const { data: monthlyFeesData, isLoading: monthlyFeesLoading } = useQuery({
    queryKey: ["student-monthly-fees", feeHistoryStudent?.id],
    queryFn: () => studentsApi.getMonthlyFees(feeHistoryStudent!.id),
    enabled: !!feeHistoryStudent,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload: CreateStudentForm) =>
      studentsApi.create({
        ...payload,
        course_id: payload.course_id || undefined,
        id_no: payload.id_no || undefined,
      }),
    onSuccess: (newStudent) => {
      toast.success(`Student ${newStudent.name} created successfully.`);
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
      setAddModalOpen(false);
      reset();
    },
    onError: () => toast.error("Unable to create student. Please check input values."),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => studentsApi.deactivate(id),
    onSuccess: (updated) => {
      toast.success(`Student ${updated.name} deactivated.`);
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
    },
    onError: () => toast.error("Failed to deactivate student."),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => studentsApi.activate(id),
    onSuccess: (updated) => {
      toast.success(`Student ${updated.name} activated.`);
      queryClient.invalidateQueries({ queryKey: ["admin-students"] });
    },
    onError: () => toast.error("Failed to activate student."),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateStudentForm>({
    resolver: zodResolver(createStudentSchema),
  });

  const onSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilters({ q: searchInput, page: "1" });
  };

  const students = data?.items || [];
  const meta = data?.meta;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Student Management
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            View, search, enroll, and manage academy student profiles, universal passcodes, and fee ledgers.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setBroadcastOpen(true)}
            className="gap-2 bg-emerald-50 border-emerald-300 text-emerald-800 hover:bg-emerald-100 font-bold shadow-2xs text-xs"
            title="Broadcast fee reminder to all students with pending dues via WhatsApp"
          >
            <Send className="h-3.5 w-3.5 text-emerald-600" />
            Notify All Unpaid Students (WhatsApp)
          </Button>
          <Button
            variant="primary"
            size="sm"
            className="gap-2 text-xs"
            onClick={() => setAddModalOpen(true)}
          >
            <UserPlus className="h-4 w-4" />
            Enroll New Student
          </Button>
        </div>
      </div>


      {/* Filter Toolbar */}
      <Card className="p-4 shadow-2xs">
        <div className="flex flex-col lg:flex-row gap-3 items-center justify-between">
          <form onSubmit={onSearchSubmit} className="relative w-full lg:w-72">
            <Input
              placeholder="Search name, ID, or phone..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9 h-9 text-xs"
            />
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          </form>

          <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
            {/* Program Filter */}
            <select
              value={programParam || ""}
              onChange={(e) => updateFilters({ program: e.target.value || undefined, page: "1" })}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600 font-medium"
            >
              <option value="">All Programs</option>
              <option value="CERTIFICATE">Certificate Program</option>
              <option value="NON_CERTIFICATE">Non-Certificate Program</option>
            </select>

            {/* ID Status Filter */}
            <select
              value={hasIdParam || ""}
              onChange={(e) => updateFilters({ has_id: e.target.value || undefined, page: "1" })}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600 font-medium"
            >
              <option value="">All ID Records</option>
              <option value="true">Has Student ID</option>
              <option value="false">Awaiting ID Assignment</option>
            </select>

            {/* Status filter */}
            <select
              value={statusParam || ""}
              onChange={(e) => updateFilters({ status: e.target.value || undefined, page: "1" })}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>

            {/* Fee Status filter */}
            <select
              value={feeStatusParam || ""}
              onChange={(e) => updateFilters({ fee_status: e.target.value || undefined, page: "1" })}
              className={`h-9 rounded-lg border px-3 text-xs font-semibold focus:outline-blue-600 ${
                feeStatusParam === "UNPAID"
                  ? "border-rose-400 bg-rose-50 text-rose-800"
                  : feeStatusParam === "PAID"
                  ? "border-emerald-400 bg-emerald-50 text-emerald-800"
                  : "border-slate-300 bg-white text-slate-700"
              }`}
            >
              <option value="">All Fee Statuses</option>
              <option value="UNPAID">Unpaid / Due Fees</option>
              <option value="PAID">Oct 2026 Paid</option>
            </select>

            {/* Course filter */}
            <select
              value={courseId || ""}
              onChange={(e) => updateFilters({ course_id: e.target.value || undefined, page: "1" })}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600 max-w-[180px]"
            >
              <option value="">All Courses</option>
              {coursesData?.items?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Students Table */}
      <Card className="overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-rose-600">
            Error loading students list. Please try again.
          </div>
        ) : students.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<Users className="h-8 w-8" />}
              title="No students found"
              description={
                q || statusParam || courseId || programParam || hasIdParam || feeStatusParam
                  ? "No students match your active filters."
                  : "No students enrolled yet. Add your first student or import from CSV."
              }
              action={
                q || statusParam || courseId || programParam || hasIdParam || feeStatusParam ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSearchInput("");
                      updateFilters({
                        q: undefined,
                        status: undefined,
                        course_id: undefined,
                        program: undefined,
                        has_id: undefined,
                        fee_status: undefined,
                        page: "1",
                      });
                    }}
                  >
                    Clear Filters
                  </Button>
                ) : (
                  <Button variant="primary" size="sm" onClick={() => setAddModalOpen(true)}>
                    Enroll Student
                  </Button>
                )
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">Student & ID</th>
                  <th className="py-3 px-4">Program</th>
                  <th className="py-3 px-4">Passcode</th>
                  <th className="py-3 px-4">Oct 2026 Status & Due Months</th>
                  <th className="py-3 px-4">Monthly Rate</th>
                  <th className="py-3 px-4">Course</th>
                  <th className="py-3 px-4">Contact</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {students.map((student) => (
                  <tr key={student.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        {student.has_photo ? (
                          <div className="h-8 w-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                            <ImageIcon className="h-4 w-4" />
                          </div>
                        ) : (
                          <div className="h-8 w-8 rounded-full bg-slate-100 text-slate-600 border border-slate-200 flex items-center justify-center font-bold text-[10px] shrink-0">
                            {student.name.charAt(0)}
                          </div>
                        )}
                        <div>
                          <div className="font-semibold text-slate-900 leading-tight">
                            {student.name}
                          </div>
                          <div className="mt-0.5">
                            {student.id_no ? (
                              <span className="font-mono text-[11px] font-semibold text-blue-800 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-100">
                                {student.id_no}
                              </span>
                            ) : (
                              <span className="inline-flex items-center text-[10px] font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                                Awaiting ID
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {student.program === "CERTIFICATE" ? (
                        <span className="inline-block text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                          Certificate
                        </span>
                      ) : student.program === "NON_CERTIFICATE" ? (
                        <span className="inline-block text-[10px] font-bold text-sky-800 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded-full">
                          Non-Certificate
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {student.initial_passcode ? (
                        <button
                          type="button"
                          onClick={() => copyToClipboard(student.initial_passcode!, `Passcode for ${student.name}`)}
                          className="inline-flex items-center gap-1.5 font-mono text-[11px] font-semibold text-indigo-700 bg-indigo-50/80 hover:bg-indigo-100 px-2 py-1 rounded border border-indigo-200/70 transition-colors cursor-pointer group"
                          title="Click to copy student passcode"
                        >
                          <KeyRound className="h-3 w-3 text-indigo-500" />
                          <span>{student.initial_passcode}</span>
                          {copiedId === student.initial_passcode ? (
                            <Check className="h-3 w-3 text-emerald-600" />
                          ) : (
                            <Copy className="h-3 w-3 text-indigo-400 group-hover:text-indigo-600" />
                          )}
                        </button>
                      ) : (
                        <span className="text-slate-400 text-[11px] italic">Not set</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="space-y-1">
                        <div>
                          {student.current_month_status === "PAID" ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                              <Check className="h-3 w-3 text-emerald-600" />
                              Oct 2026: Paid
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-800 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full">
                              <span className="h-1.5 w-1.5 rounded-full bg-rose-600"></span>
                              Oct 2026: Unpaid
                            </span>
                          )}
                        </div>
                        {student.unpaid_months && student.unpaid_months.length > 0 ? (
                          <div className="text-[11px] leading-tight max-w-[200px]">
                            <span className="font-semibold text-rose-700">
                              Due ({student.due_months_count}):
                            </span>{" "}
                            <span className="font-mono text-slate-700 text-[10px]">
                              {student.unpaid_months.slice(0, 3).join(", ")}
                              {student.unpaid_months.length > 3 && (
                                <span className="text-slate-500 font-sans font-medium">
                                  {" "}
                                  +{student.unpaid_months.length - 3} more
                                </span>
                              )}
                            </span>
                          </div>
                        ) : (
                          <div className="text-[10px] text-emerald-600 font-medium flex items-center gap-1">
                            <Check className="h-3 w-3" /> All clear
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">
                      {student.monthly_fee_paise ? (
                        <span className="font-semibold text-slate-900">
                          {formatCurrency(student.monthly_fee_paise)}
                          <span className="text-[10px] text-slate-500 font-normal">/mo</span>
                        </span>
                      ) : student.fee_notes ? (
                        <span className="text-[11px] text-slate-600" title={student.fee_notes}>
                          {student.fee_notes.length > 25
                            ? `${student.fee_notes.slice(0, 25)}...`
                            : student.fee_notes}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-700 max-w-[150px] truncate">
                      {student.course_name || student.legacy_course || "—"}
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-mono text-[11px]">
                      {student.contact || "—"}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={student.status === "active" ? "success" : "default"}>
                        {student.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {/* Notify on WhatsApp button */}
                        <Button
                          variant="outline"
                          size="sm"
                          className={`h-7 px-2 text-xs font-semibold ${
                            student.current_month_status === "UNPAID" ||
                            (student.due_months_count && student.due_months_count > 0)
                              ? "text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 border-emerald-300 bg-emerald-50/60"
                              : "text-slate-600 hover:text-emerald-700 hover:bg-slate-50 border-slate-200"
                          }`}
                          onClick={() => setWhatsAppStudent(student)}
                          title="Send Fee Payment Notice to WhatsApp"
                        >
                          <MessageSquare className="h-3.5 w-3.5 mr-1 text-emerald-600" />
                          Notify
                        </Button>

                        {/* Edit Student Details button */}
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-blue-700 hover:text-blue-800 hover:bg-blue-50 border-blue-200 text-xs font-semibold"
                          onClick={() => setEditStudent(student)}
                          title="Edit student details, reassign ID, program, fees, or passcode"
                        >
                          <Pencil className="h-3.5 w-3.5 mr-1" />
                          Edit
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 border-indigo-200 text-xs"
                          onClick={() => setFeeHistoryStudent(student)}
                          title="View complete monthly fee ledger"
                        >
                          <CreditCard className="h-3.5 w-3.5 mr-1" />
                          Ledger
                        </Button>

                        <Link href={`/admin/students/${student.id}`}>
                          <Button variant="ghost" size="sm" className="h-7 px-2 text-slate-600 hover:text-slate-900">
                            <Eye className="h-3.5 w-3.5 mr-1" />
                            Profile
                          </Button>
                        </Link>

                        {student.status === "active" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                            onClick={() => setDeactivateStudent(student)}
                            title="Deactivate student"
                          >
                            <UserX className="h-3.5 w-3.5" />
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                            onClick={() => activateMutation.mutate(student.id)}
                            title="Activate student"
                          >
                            <UserCheck className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
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
              onPageChange={(newPage) => updateFilters({ page: String(newPage) })}
              isLoading={isLoading}
            />
          </div>
        )}
      </Card>

      {/* Fee History / Ledger Modal */}
      <Dialog open={!!feeHistoryStudent} onOpenChange={(open) => !open && setFeeHistoryStudent(null)}>
        <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col p-6">
          <DialogHeader className="pb-3 border-b border-slate-100">
            <div className="flex items-start justify-between">
              <div>
                <DialogTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-indigo-600" />
                  Monthly Fee Ledger: {feeHistoryStudent?.name}
                </DialogTitle>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-600">
                  {feeHistoryStudent?.id_no ? (
                    <span className="font-mono font-semibold bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200">
                      ID: {feeHistoryStudent.id_no}
                    </span>
                  ) : (
                    <span className="font-semibold bg-amber-50 text-amber-700 px-2 py-0.5 rounded border border-amber-200">
                      Awaiting ID
                    </span>
                  )}
                  <span>
                    Program:{" "}
                    <strong className="text-slate-800">
                      {feeHistoryStudent?.program === "CERTIFICATE"
                        ? "Certificate"
                        : "Non-Certificate"}
                    </strong>
                  </span>
                  {feeHistoryStudent?.initial_passcode && (
                    <span className="flex items-center gap-1 font-mono text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                      <KeyRound className="h-3 w-3" /> Passcode: {feeHistoryStudent.initial_passcode}
                    </span>
                  )}
                  {feeHistoryStudent?.monthly_fee_paise && (
                    <span>
                      Standard Rate:{" "}
                      <strong className="text-emerald-700 font-mono">
                        {formatCurrency(feeHistoryStudent.monthly_fee_paise)}/mo
                      </strong>
                    </span>
                  )}
                </div>
              </div>
            </div>
          </DialogHeader>

          {feeHistoryStudent?.fee_notes && (
            <div className="mt-3 rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-900 leading-relaxed">
              <span className="font-bold">Fee Record Notes:</span> {feeHistoryStudent.fee_notes}
            </div>
          )}

          <div className="flex-1 overflow-y-auto mt-4 pr-1">
            {monthlyFeesLoading ? (
              <div className="space-y-2 py-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-9 w-full" />
                ))}
              </div>
            ) : !monthlyFeesData || monthlyFeesData.length === 0 ? (
              <div className="py-12 text-center">
                <FileSpreadsheet className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                <h4 className="font-medium text-slate-700 text-sm">No monthly fee records</h4>
                <p className="text-xs text-slate-400 mt-1">
                  This student does not have any legacy month-by-month fee entries recorded yet.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Stats row */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-center">
                    <span className="text-[11px] text-slate-500 font-medium">Total Months</span>
                    <p className="text-lg font-bold text-slate-800">{monthlyFeesData.length}</p>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2.5 text-center">
                    <span className="text-[11px] text-emerald-700 font-medium">Paid Months</span>
                    <p className="text-lg font-bold text-emerald-700">
                      {monthlyFeesData.filter((f) => f.status === "PAID").length}
                    </p>
                  </div>
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-center">
                    <span className="text-[11px] text-amber-700 font-medium">Pending Months</span>
                    <p className="text-lg font-bold text-amber-700">
                      {monthlyFeesData.filter((f) => f.status === "PENDING").length}
                    </p>
                  </div>
                </div>

                {/* Ledger Table */}
                <div className="rounded-lg border border-slate-200 overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px]">
                      <tr>
                        <th className="py-2.5 px-3">Month / Period</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Amount</th>
                        <th className="py-2.5 px-3">Paid Date</th>
                        <th className="py-2.5 px-3">Record Details / Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {monthlyFeesData.map((entry) => {
                        const isCurrentMonth = entry.period === "2026-10-01" || entry.period_label.toLowerCase().includes("oct");
                        return (
                        <tr key={entry.id} className={isCurrentMonth ? "bg-blue-50/40 hover:bg-blue-50/70" : "hover:bg-slate-50/70"}>
                          <td className="py-2.5 px-3 font-semibold text-slate-900">
                            <div className="flex items-center gap-1.5">
                              <span>{entry.period_label}</span>
                              {isCurrentMonth && (
                                <span className="text-[9px] font-bold uppercase bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                  Current Month
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                                entry.status === "PAID"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : entry.status === "PENDING"
                                  ? "bg-amber-100 text-amber-800"
                                  : entry.status === "CLOSED"
                                  ? "bg-slate-100 text-slate-600"
                                  : "bg-blue-100 text-blue-800"
                              }`}
                            >
                              {entry.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-900 font-medium">
                            {entry.amount_paise ? formatCurrency(entry.amount_paise) : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-slate-600">
                            {entry.paid_on ? formatDate(entry.paid_on) : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-slate-600 text-[11px]">
                            {entry.note || entry.raw_entry || "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="pt-3 border-t border-slate-100 mt-2">
            <Button variant="outline" size="sm" onClick={() => setFeeHistoryStudent(null)}>
              Close Ledger
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Student Modal */}
      <Dialog open={addModalOpen} onOpenChange={setAddModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Enroll New Student</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((d) => createMutation.mutate(d))} className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Student Full Name *
              </label>
              <Input placeholder="e.g. Amit Kumar" error={errors.name?.message} {...register("name")} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  ID No. (optional)
                </label>
                <Input placeholder="Auto-generated if empty" {...register("id_no")} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Admission Date
                </label>
                <Input type="date" {...register("admission_date")} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Guardian&apos;s Name
                </label>
                <Input placeholder="Father / Mother" {...register("guardian_name")} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Contact Number
                </label>
                <Input placeholder="10-digit mobile" {...register("contact")} />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Course</label>
              <select
                {...register("course_id")}
                className="w-full h-9.5 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
              >
                <option value="">Select Enrolled Course</option>
                {coursesData?.items?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Address</label>
              <Input placeholder="City, Area, Address" {...register("address")} />
            </div>

            <DialogFooter className="pt-3">
              <Button variant="outline" type="button" onClick={() => setAddModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" isLoading={isSubmitting || createMutation.isPending}>
                Create Student Record
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Deactivate Confirmation (spec §36) */}
      <ConfirmDialog
        open={!!deactivateStudent}
        onOpenChange={(open) => !open && setDeactivateStudent(null)}
        title="Deactivate Student Record"
        description={`You are about to deactivate ${deactivateStudent?.name}. Historical payments, receipts, and attendance will remain available, but they will be marked inactive.`}
        confirmLabel="Deactivate"
        onConfirm={async () => {
          if (deactivateStudent) {
            await deactivateMutation.mutateAsync(deactivateStudent.id);
            setDeactivateStudent(null);
          }
        }}
        isLoading={deactivateMutation.isPending}
      />

      {/* Edit Student Dialog */}
      <StudentEditDialog
        student={editStudent}
        open={!!editStudent}
        onOpenChange={(open) => !open && setEditStudent(null)}
      />

      {/* WhatsApp Individual Notice Dialog */}
      <WhatsAppNoticeDialog
        student={whatsAppStudent}
        open={!!whatsAppStudent}
        onOpenChange={(open) => !open && setWhatsAppStudent(null)}
      />

      {/* Broadcast Due Notices to All Unpaid Students Dialog */}
      <BroadcastNoticesDialog
        open={broadcastOpen}
        onOpenChange={setBroadcastOpen}
        unpaidCountEstimate={
          students.filter(
            (s) => s.current_month_status === "UNPAID" || (s.due_months_count || 0) > 0
          ).length
        }
      />
    </div>
  );
}


export default function StudentsManagementPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-6">
          <div className="h-8 w-48 animate-pulse rounded bg-slate-200" />
          <div className="h-64 animate-pulse rounded bg-slate-100" />
        </div>
      }
    >
      <StudentsManagementContent />
    </Suspense>
  );
}
