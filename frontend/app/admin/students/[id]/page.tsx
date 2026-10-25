"use client";

import { Suspense, use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { studentsApi } from "@/lib/api/students";
import { feesApi } from "@/lib/api/fees";
import { paymentsApi } from "@/lib/api/payments";
import { receiptsApi } from "@/lib/api/receipts";
import { attendanceApi } from "@/lib/api/attendance";
import { idCardsApi } from "@/lib/api/id-cards";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { formatCurrency, formatDate, formatDateTime, formatStatus } from "@/lib/utils";
import { toast } from "sonner";
import {
  ArrowLeft,
  Upload,
  CreditCard,
  FileText,
  CalendarCheck,
  IdCard as IdCardIcon,
  Phone,
  MapPin,
  Calendar,
  Download,
  AlertCircle,
  Clock,
  Sparkles,
  Copy,
  Check,
  KeyRound,
  FileSpreadsheet,
  Pencil,
  MessageSquare,
} from "lucide-react";
import { StudentEditDialog } from "@/components/students/student-edit-dialog";
import { WhatsAppNoticeDialog } from "@/components/students/whatsapp-notice-dialog";
import type { OfflineMethod, StudentMonthlyFee } from "@/types/api";


function ProfileSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

// The student id is only known at request time. Reading `params` inside <Suspense> lets
// the admin shell prerender while this part streams in (Cache Components).
export default function StudentProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<ProfileSkeleton />}>
      <StudentProfileFromParams params={params} />
    </Suspense>
  );
}

function StudentProfileFromParams({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <StudentProfile studentId={id} />;
}

function StudentProfile({ studentId }: { studentId: string }) {
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<
    "overview" | "fees" | "payments" | "receipts" | "attendance" | "id-card"
  >("overview");

  // Modals state
  const [offlineFeeId, setOfflineFeeId] = useState<string | null>(null);
  const [offlineAmount, setOfflineAmount] = useState<string>("");
  const [offlineMethod, setOfflineMethod] = useState<OfflineMethod>("CASH");
  const [offlineRef, setOfflineRef] = useState<string>("");

  const [concessionFeeId, setConcessionFeeId] = useState<string | null>(null);
  const [concessionAmount, setConcessionAmount] = useState<string>("");
  const [concessionReason, setConcessionReason] = useState<string>("");

  const [cancelFeeId, setCancelFeeId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState<string>("");

  // Upload state
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  // Edit & WhatsApp Dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [whatsAppNoticeOpen, setWhatsAppNoticeOpen] = useState(false);

  // Queries
  const { data: student, isLoading: studentLoading } = useQuery({
    queryKey: ["student", studentId],
    queryFn: () => studentsApi.get(studentId),
  });

  const { data: feeSummary } = useQuery({
    queryKey: ["student-fee-summary", studentId],
    queryFn: () => feesApi.summary(studentId),
  });

  const { data: feesData } = useQuery({
    queryKey: ["student-fees", studentId],
    queryFn: () => feesApi.list({ student_id: studentId, page_size: 50 }),
    enabled: activeTab === "fees" || activeTab === "overview",
  });

  const { data: paymentsData } = useQuery({
    queryKey: ["student-payments", studentId],
    queryFn: () => paymentsApi.list({ student_id: studentId, page_size: 50 }),
    enabled: activeTab === "payments",
  });

  const { data: receiptsData } = useQuery({
    queryKey: ["student-receipts", studentId],
    queryFn: () => receiptsApi.list({ student_id: studentId, page_size: 50 }),
    enabled: activeTab === "receipts",
  });

  const { data: attendanceData } = useQuery({
    queryKey: ["student-attendance", studentId],
    queryFn: () => attendanceApi.getStudentAttendance(studentId),
    enabled: activeTab === "attendance",
  });

  const { data: idCardHistory } = useQuery({
    queryKey: ["student-id-card-history", studentId],
    queryFn: () => idCardsApi.history(studentId),
    enabled: activeTab === "id-card",
  });

  const { data: legacyMonthlyFees, isLoading: legacyFeesLoading } = useQuery({
    queryKey: ["student-monthly-fees", studentId],
    queryFn: () => studentsApi.getMonthlyFees(studentId),
    enabled: activeTab === "fees" || activeTab === "overview",
  });

  const [copiedPasscode, setCopiedPasscode] = useState(false);
  const handleCopyPasscode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedPasscode(true);
    toast.success("Student passcode copied!");
    setTimeout(() => setCopiedPasscode(false), 2000);
  };

  // Mutations
  const offlinePaymentMutation = useMutation({
    mutationFn: () => {
      const paise = Math.round(parseFloat(offlineAmount) * 100);
      return feesApi.recordOfflinePayment(offlineFeeId!, {
        amount_paise: paise,
        method: offlineMethod,
        reference: offlineRef || undefined,
      });
    },
    onSuccess: () => {
      toast.success("Offline payment recorded successfully.");
      setOfflineFeeId(null);
      setOfflineAmount("");
      queryClient.invalidateQueries({ queryKey: ["student-fees", studentId] });
      queryClient.invalidateQueries({ queryKey: ["student-fee-summary", studentId] });
    },
    onError: () => toast.error("Failed to record offline payment."),
  });

  const concessionMutation = useMutation({
    mutationFn: () => {
      const paise = Math.round(parseFloat(concessionAmount) * 100);
      return feesApi.applyConcession(concessionFeeId!, {
        amount_paise: paise,
        reason: concessionReason,
      });
    },
    onSuccess: () => {
      toast.success("Concession applied.");
      setConcessionFeeId(null);
      setConcessionAmount("");
      setConcessionReason("");
      queryClient.invalidateQueries({ queryKey: ["student-fees", studentId] });
      queryClient.invalidateQueries({ queryKey: ["student-fee-summary", studentId] });
    },
    onError: () => toast.error("Failed to apply fee concession."),
  });

  const cancelFeeMutation = useMutation({
    mutationFn: () => feesApi.cancel(cancelFeeId!, { reason: cancelReason }),
    onSuccess: () => {
      toast.success("Fee record cancelled.");
      setCancelFeeId(null);
      setCancelReason("");
      queryClient.invalidateQueries({ queryKey: ["student-fees", studentId] });
      queryClient.invalidateQueries({ queryKey: ["student-fee-summary", studentId] });
    },
    onError: () => toast.error("Failed to cancel fee record."),
  });

  const generateIdCardMutation = useMutation({
    mutationFn: () => idCardsApi.generate(studentId),
    onSuccess: () => {
      toast.success("ID Card generated successfully.");
      queryClient.invalidateQueries({ queryKey: ["student", studentId] });
      queryClient.invalidateQueries({ queryKey: ["student-id-card-history", studentId] });
    },
    onError: () => toast.error("Failed to generate ID card."),
  });

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (max 5MB) and mime
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Photo size must be less than 5MB");
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Only JPG, PNG, and WebP images are allowed.");
      return;
    }

    try {
      setUploadProgress(10);
      await studentsApi.uploadPhoto(studentId, file, (percent) => setUploadProgress(percent));
      toast.success("Student photo updated.");
      queryClient.invalidateQueries({ queryKey: ["student", studentId] });
    } catch {
      toast.error("Failed to upload photo.");
    } finally {
      setUploadProgress(null);
    }
  };

  if (studentLoading) {
    return <ProfileSkeleton />;
  }

  if (!student) {
    return (
      <EmptyState
        title="Student record not found"
        action={
          <Link href="/admin/students">
            <Button variant="outline" size="sm">
              Back to Students
            </Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/admin/students"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Students List
        </Link>
      </div>

      {/* Top Banner / Student Profile Header */}
      <Card className="overflow-hidden shadow-2xs">
        <div className="bg-gradient-to-r from-blue-900 via-slate-800 to-slate-900 p-6 text-white">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              {/* Photo / Avatar */}
              <div className="relative group shrink-0">
                <div className="h-20 w-20 rounded-xl bg-white/10 border-2 border-white/20 flex items-center justify-center overflow-hidden">
                  {student.has_photo ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={studentsApi.photoUrl(student.id, student.updated_at)}
                      alt={student.name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="text-2xl font-bold text-white/80">
                      {student.name.charAt(0)}
                    </span>
                  )}
                </div>
                {/* Upload overlay */}
                <label className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer text-white text-[10px]">
                  <Upload className="h-4 w-4 mb-0.5" />
                  Upload
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={handlePhotoUpload}
                  />
                </label>
              </div>

              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-xl font-bold">{student.name}</h1>
                  <Badge variant={student.status === "active" ? "success" : "default"}>
                    {student.status}
                  </Badge>
                </div>
                <p className="font-mono text-xs text-blue-200 mt-0.5">
                  ID: {student.id_no}
                </p>
                <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-300">
                  <span className="flex items-center gap-1">
                    <Phone className="h-3.5 w-3.5 text-blue-300" />
                    {student.contact || "No contact"}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5 text-blue-300" />
                    {student.address || "No address"}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5 text-blue-300" />
                    Enrolled {formatDate(student.admission_date)}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="bg-emerald-600/90 text-white border-emerald-400 hover:bg-emerald-700 text-xs gap-1.5 font-semibold"
                onClick={() => setWhatsAppNoticeOpen(true)}
                title="Send Fee Payment Notice to WhatsApp"
              >
                <MessageSquare className="h-3.5 w-3.5" />
                Notify WhatsApp
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="bg-white/20 text-white border-white/30 hover:bg-white/30 text-xs gap-1.5 font-semibold"
                onClick={() => setEditDialogOpen(true)}
                title="Edit student details, reassign ID, program, fees, or passcode"
              >
                <Pencil className="h-3.5 w-3.5" />
                Edit Details
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 text-white border-white/20 hover:bg-white/20 text-xs gap-1.5"
                isLoading={generateIdCardMutation.isPending}
                onClick={() => generateIdCardMutation.mutate()}
              >
                <IdCardIcon className="h-3.5 w-3.5" />
                Generate ID Card
              </Button>
            </div>
          </div>


          {uploadProgress !== null && (
            <div className="mt-4">
              <div className="h-1.5 w-full bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-400 transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-[10px] text-blue-200 mt-1">Uploading: {uploadProgress}%</p>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-white px-6 overflow-x-auto text-xs font-medium text-slate-600">
          {[
            { id: "overview", label: "Overview", icon: Clock },
            { id: "fees", label: "Fees & Dues", icon: CreditCard },
            { id: "payments", label: "Payments", icon: CreditCard },
            { id: "receipts", label: "Receipts", icon: FileText },
            { id: "attendance", label: "Attendance", icon: CalendarCheck },
            { id: "id-card", label: "ID Card", icon: IdCardIcon },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`flex items-center gap-2 border-b-2 py-3 px-4 transition-colors cursor-pointer whitespace-nowrap ${
                  active
                    ? "border-blue-600 text-blue-600 font-semibold"
                    : "border-transparent text-slate-500 hover:text-slate-900"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </Card>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Student Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">Full Name</span>
                <span className="font-semibold text-slate-900">{student.name}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">ID Number</span>
                <span className="font-mono text-slate-900">
                  {student.id_no || (
                    <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-[11px] font-medium border border-amber-200">
                      Awaiting ID Assignment
                    </span>
                  )}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">Academic Program</span>
                <span>
                  {student.program === "CERTIFICATE" ? (
                    <Badge variant="success">Certificate Program</Badge>
                  ) : student.program === "NON_CERTIFICATE" ? (
                    <Badge variant="info">Non-Certificate Program</Badge>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">Student Passcode</span>
                <div>
                  {student.initial_passcode ? (
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200 text-xs">
                        {student.initial_passcode}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopyPasscode(student.initial_passcode!)}
                        className="text-slate-400 hover:text-indigo-600 transition-colors p-1"
                        title="Copy student passcode"
                      >
                        {copiedPasscode ? (
                          <Check className="h-3.5 w-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  ) : (
                    <span className="text-slate-400 italic">Not generated (needs ID)</span>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">Standard Monthly Rate</span>
                <span className="font-semibold text-slate-900 font-mono">
                  {student.monthly_fee_paise
                    ? `${formatCurrency(student.monthly_fee_paise)} / month`
                    : "—"}
                </span>
              </div>
              {student.fee_notes && (
                <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                  <span className="text-slate-500">Fee Record Notes</span>
                  <span className="text-amber-800 bg-amber-50 p-2 rounded border border-amber-200 text-[11px] leading-relaxed">
                    {student.fee_notes}
                  </span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">Guardian&apos;s Name</span>
                <span className="text-slate-900">{student.guardian_name || "—"}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">Contact Number</span>
                <span className="font-mono text-slate-900">{student.contact || "—"}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 py-2 border-b border-slate-100">
                <span className="text-slate-500">Course</span>
                <span className="text-slate-900 font-medium">
                  {student.course_name || student.legacy_course || "—"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 py-2">
                <span className="text-slate-500">Residential Address</span>
                <span className="text-slate-900">{student.address || "—"}</span>
              </div>
            </CardContent>
          </Card>

          {/* Quick Fee Summary Box */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Fee Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Total Fees:</span>
                <span className="font-semibold text-slate-900">
                  {formatCurrency(feeSummary?.total_amount_paise)}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Total Paid:</span>
                <span className="font-semibold text-emerald-600">
                  {formatCurrency(feeSummary?.total_paid_paise)}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Concessions:</span>
                <span className="font-semibold text-slate-700">
                  {formatCurrency(feeSummary?.total_concession_paise)}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-100">
                <span className="text-slate-500">Outstanding:</span>
                <span className="font-bold text-slate-900">
                  {formatCurrency(feeSummary?.total_outstanding_paise)}
                </span>
              </div>
              {feeSummary && feeSummary.overdue_paise > 0 && (
                <div className="flex justify-between py-1.5 bg-rose-50 p-2 rounded-lg text-rose-700">
                  <span className="font-medium">Overdue Amount:</span>
                  <span className="font-bold">
                    {formatCurrency(feeSummary.overdue_paise)}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Fees & Dues */}
      {activeTab === "fees" && (
        <div className="space-y-6">
          <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle className="text-base">Assigned Fees & Payment Dues</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {feesData?.items?.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={<CreditCard className="h-8 w-8" />}
                  title="No fees scheduled"
                  description="No fee plan or manual fees have been assigned to this student."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 text-[10px] font-semibold uppercase">
                    <tr>
                      <th className="py-2.5 px-4">Title</th>
                      <th className="py-2.5 px-4">Due Date</th>
                      <th className="py-2.5 px-4">Amount</th>
                      <th className="py-2.5 px-4">Concession</th>
                      <th className="py-2.5 px-4">Paid</th>
                      <th className="py-2.5 px-4">Balance</th>
                      <th className="py-2.5 px-4">Status</th>
                      <th className="py-2.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {feesData?.items?.map((fee) => (
                      <tr key={fee.id} className="hover:bg-slate-50/50">
                        <td className="py-3 px-4 font-semibold text-slate-900">{fee.title}</td>
                        <td className="py-3 px-4 text-slate-600">{formatDate(fee.due_date)}</td>
                        <td className="py-3 px-4 text-slate-900">{formatCurrency(fee.amount_paise)}</td>
                        <td className="py-3 px-4 text-slate-500">
                          {fee.concession_paise > 0 ? formatCurrency(fee.concession_paise) : "—"}
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
                          <div className="flex items-center justify-end gap-1">
                            {fee.balance_paise > 0 && fee.status !== "CANCELLED" && (
                              <>
                                <Button
                                  variant="primary"
                                  size="sm"
                                  className="h-7 text-[11px] px-2"
                                  onClick={() => {
                                    setOfflineFeeId(fee.id);
                                    setOfflineAmount((fee.balance_paise / 100).toFixed(2));
                                  }}
                                >
                                  Collect
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-7 text-[11px] px-2"
                                  onClick={() => {
                                    setConcessionFeeId(fee.id);
                                    setConcessionAmount("0");
                                  }}
                                >
                                  Discount
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 text-[11px] text-rose-600 hover:bg-rose-50"
                                  onClick={() => setCancelFeeId(fee.id)}
                                >
                                  Cancel
                                </Button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Monthly Historical Fee Ledger */}
        {legacyMonthlyFees && legacyMonthlyFees.length > 0 && (
          <Card className="mt-6 overflow-hidden border border-slate-200">
            <CardHeader className="bg-slate-50 border-b border-slate-200 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="h-4 w-4 text-indigo-600" />
                  <CardTitle className="text-sm font-bold text-slate-900">
                    Monthly Fee Ledger ({legacyMonthlyFees.length} Recorded Months)
                  </CardTitle>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    {legacyMonthlyFees.filter((f) => f.status === "PAID").length} Paid
                  </span>
                  <span className="text-amber-700 font-semibold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    {legacyMonthlyFees.filter((f) => f.status === "PENDING").length} Pending
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto max-h-96">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 text-[10px] font-semibold uppercase sticky top-0">
                    <tr>
                      <th className="py-2.5 px-4">Period</th>
                      <th className="py-2.5 px-4">Status</th>
                      <th className="py-2.5 px-4">Amount</th>
                      <th className="py-2.5 px-4">Paid On</th>
                      <th className="py-2.5 px-4">Notes / Remarks</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {legacyMonthlyFees.map((entry) => (
                      <tr key={entry.id} className="hover:bg-slate-50/70">
                        <td className="py-2.5 px-4 font-semibold text-slate-900">
                          {entry.period_label}
                        </td>
                        <td className="py-2.5 px-4">
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
                        <td className="py-2.5 px-4 font-mono font-medium text-slate-900">
                          {entry.amount_paise ? formatCurrency(entry.amount_paise) : "—"}
                        </td>
                        <td className="py-2.5 px-4 text-slate-600">
                          {entry.paid_on ? formatDate(entry.paid_on) : "—"}
                        </td>
                        <td className="py-2.5 px-4 text-slate-600 text-[11px]">
                          {entry.note || entry.raw_entry || "—"}
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

      {/* Tab 3: Payments */}
      {activeTab === "payments" && (
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle className="text-base">Payment Transactions</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {paymentsData?.items?.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={<CreditCard className="h-8 w-8" />}
                  title="No payments recorded"
                  description="No online or offline payments have been recorded for this student."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 text-[10px] font-semibold uppercase">
                    <tr>
                      <th className="py-2.5 px-4">Date</th>
                      <th className="py-2.5 px-4">Amount</th>
                      <th className="py-2.5 px-4">Provider</th>
                      <th className="py-2.5 px-4">Method</th>
                      <th className="py-2.5 px-4">Reference</th>
                      <th className="py-2.5 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {paymentsData?.items?.map((p) => (
                      <tr key={p.id}>
                        <td className="py-3 px-4 text-slate-700">{formatDateTime(p.paid_at || p.created_at)}</td>
                        <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(p.amount_paise)}</td>
                        <td className="py-3 px-4 font-mono text-slate-600">{p.provider}</td>
                        <td className="py-3 px-4 text-slate-600 uppercase text-[11px]">{p.method || "—"}</td>
                        <td className="py-3 px-4 font-mono text-slate-500">{p.reference || p.provider_payment_id || "—"}</td>
                        <td className="py-3 px-4">
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
      )}

      {/* Tab 4: Receipts */}
      {activeTab === "receipts" && (
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle className="text-base">Official Payment Receipts</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {receiptsData?.items?.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={<FileText className="h-8 w-8" />}
                  title="No receipts issued"
                  description="Receipts are generated automatically upon successful payment settlement."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 text-[10px] font-semibold uppercase">
                    <tr>
                      <th className="py-2.5 px-4">Receipt No.</th>
                      <th className="py-2.5 px-4">Issue Date</th>
                      <th className="py-2.5 px-4">Amount</th>
                      <th className="py-2.5 px-4 text-right">Download</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {receiptsData?.items?.map((r) => (
                      <tr key={r.id}>
                        <td className="py-3 px-4 font-mono font-bold text-blue-600">{r.receipt_number}</td>
                        <td className="py-3 px-4 text-slate-600">{formatDateTime(r.issued_at)}</td>
                        <td className="py-3 px-4 font-semibold text-slate-900">{formatCurrency(r.amount_paise)}</td>
                        <td className="py-3 px-4 text-right">
                          <a href={receiptsApi.downloadUrl(r.id)} target="_blank" rel="noreferrer">
                            <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5">
                              <Download className="h-3.5 w-3.5" />
                              PDF
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
      )}

      {/* Tab 5: Attendance */}
      {activeTab === "attendance" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card className="p-4 text-center">
              <span className="text-xs text-slate-500">Attendance Rate</span>
              <p className="text-2xl font-bold text-blue-600 mt-1">
                {attendanceData?.summary?.percentage !== null && attendanceData?.summary?.percentage !== undefined
                  ? `${Math.round(attendanceData.summary.percentage)}%`
                  : "—"}
              </p>
            </Card>
            <Card className="p-4 text-center">
              <span className="text-xs text-slate-500">Total Classes</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {attendanceData?.summary?.total ?? 0}
              </p>
            </Card>
            <Card className="p-4 text-center">
              <span className="text-xs text-slate-500">Present</span>
              <p className="text-2xl font-bold text-emerald-600 mt-1">
                {attendanceData?.summary?.present ?? 0}
              </p>
            </Card>
            <Card className="p-4 text-center">
              <span className="text-xs text-slate-500">Absent</span>
              <p className="text-2xl font-bold text-rose-600 mt-1">
                {attendanceData?.summary?.absent ?? 0}
              </p>
            </Card>
          </div>

          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle className="text-base">Attendance Log</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {attendanceData?.records?.length === 0 ? (
                <div className="p-8">
                  <EmptyState
                    icon={<CalendarCheck className="h-8 w-8" />}
                    title="No attendance records"
                    description="No attendance checks recorded for this student."
                  />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-y border-slate-200 text-slate-600 text-[10px] font-semibold uppercase">
                      <tr>
                        <th className="py-2.5 px-4">Date</th>
                        <th className="py-2.5 px-4">Status</th>
                        <th className="py-2.5 px-4">Remarks</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {attendanceData?.records?.map((record) => (
                        <tr key={record.id}>
                          <td className="py-2.5 px-4 text-slate-900">{formatDate(record.attendance_date)}</td>
                          <td className="py-2.5 px-4">
                            <Badge
                              variant={
                                record.status === "PRESENT"
                                  ? "success"
                                  : record.status === "ABSENT"
                                  ? "danger"
                                  : "warning"
                              }
                            >
                              {record.status}
                            </Badge>
                          </td>
                          <td className="py-2.5 px-4 text-slate-500">{record.remarks || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 6: ID Card */}
      {activeTab === "id-card" && (
        <Card className="p-6">
          <div className="flex flex-col sm:flex-row items-start justify-between gap-6">
            <div>
              <h3 className="text-base font-bold text-slate-900">Student Identity Card</h3>
              <p className="text-xs text-slate-500 mt-1">
                Official academy ID card for campus access and exam attendance.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button
                  variant="primary"
                  size="sm"
                  className="gap-1.5 text-xs"
                  isLoading={generateIdCardMutation.isPending}
                  onClick={() => generateIdCardMutation.mutate()}
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Generate / Regenerate ID Card
                </Button>
                {student.has_id_card && (
                  <a href={idCardsApi.downloadUrl(student.id)} target="_blank" rel="noreferrer">
                    <Button variant="outline" size="sm" className="gap-1.5 text-xs">
                      <Download className="h-3.5 w-3.5" />
                      Download PDF
                    </Button>
                  </a>
                )}
              </div>
            </div>

            {/* Preview Card Mock / Status */}
            <div className="w-full sm:w-72 h-44 rounded-xl border border-slate-200 bg-slate-50 p-4 flex flex-col justify-between shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-blue-600 uppercase">Brightway Academy</span>
                <Badge variant={student.has_id_card ? "success" : "default"} className="text-[9px]">
                  {student.has_id_card ? "CARD ISSUED" : "NOT ISSUED"}
                </Badge>
              </div>
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-lg bg-slate-200 overflow-hidden shrink-0">
                  {student.has_photo ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={studentsApi.photoUrl(student.id, student.updated_at)}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center font-bold text-xs text-slate-500">
                      {student.name.charAt(0)}
                    </div>
                  )}
                </div>
                <div className="truncate">
                  <p className="text-xs font-bold text-slate-900 truncate">{student.name}</p>
                  <p className="font-mono text-[10px] text-slate-500">{student.id_no}</p>
                  <p className="text-[10px] text-slate-600 truncate">{student.course_name || "General IT"}</p>
                </div>
              </div>
              <p className="text-[9px] text-slate-400">Valid student identity credential</p>
            </div>
          </div>
        </Card>
      )}

      {/* Collect Offline Payment Modal */}
      <Dialog open={!!offlineFeeId} onOpenChange={(open) => !open && setOfflineFeeId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Record Offline Payment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Amount Collected (INR ₹) *
              </label>
              <Input
                type="number"
                step="0.01"
                value={offlineAmount}
                onChange={(e) => setOfflineAmount(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Payment Method *
              </label>
              <select
                value={offlineMethod}
                onChange={(e) => setOfflineMethod(e.target.value as OfflineMethod)}
                className="w-full h-9.5 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
              >
                <option value="CASH">Cash</option>
                <option value="UPI">UPI / QR Code</option>
                <option value="BANK_TRANSFER">Bank Transfer / NEFT</option>
                <option value="CHEQUE">Cheque</option>
                <option value="CARD">Debit / Credit Card (POS)</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Transaction / Reference No. (optional)
              </label>
              <Input
                placeholder="e.g. UPI Ref / Cheque No."
                value={offlineRef}
                onChange={(e) => setOfflineRef(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="pt-3">
            <Button variant="outline" onClick={() => setOfflineFeeId(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={offlinePaymentMutation.isPending}
              onClick={() => offlinePaymentMutation.mutate()}
            >
              Record Payment & Issue Receipt
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Concession Modal */}
      <Dialog open={!!concessionFeeId} onOpenChange={(open) => !open && setConcessionFeeId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Apply Fee Concession</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Concession Amount (INR ₹) *
              </label>
              <Input
                type="number"
                step="0.01"
                value={concessionAmount}
                onChange={(e) => setConcessionAmount(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Reason / Approval Notes *
              </label>
              <Input
                placeholder="e.g. Merit discount / Principal approval"
                value={concessionReason}
                onChange={(e) => setConcessionReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="pt-3">
            <Button variant="outline" onClick={() => setConcessionFeeId(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              isLoading={concessionMutation.isPending}
              onClick={() => concessionMutation.mutate()}
            >
              Apply Concession
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cancel Fee Dialog */}
      <Dialog open={!!cancelFeeId} onOpenChange={(open) => !open && setCancelFeeId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Cancel Fee Item</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Cancellation Reason *
              </label>
              <Input
                placeholder="e.g. Duplicate assignment / Course change"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="pt-3">
            <Button variant="outline" onClick={() => setCancelFeeId(null)}>
              Abort
            </Button>
            <Button
              variant="destructive"
              isLoading={cancelFeeMutation.isPending}
              onClick={() => cancelFeeMutation.mutate()}
            >
              Confirm Cancellation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Student Dialog */}
      <StudentEditDialog
        student={student}
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
      />

      {/* WhatsApp Due Notice Dialog */}
      <WhatsAppNoticeDialog
        student={student}
        open={whatsAppNoticeOpen}
        onOpenChange={setWhatsAppNoticeOpen}
      />
    </div>
  );
}

