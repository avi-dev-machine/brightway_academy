"use client";

import { useQuery } from "@tanstack/react-query";
import { studentsApi } from "@/lib/api/students";
import { idCardsApi } from "@/lib/api/id-cards";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/ui/page";
import { formatDate } from "@/lib/utils";
import {
  Download,
  IdCard,
  CheckCircle2,
  Clock,
} from "lucide-react";

export default function StudentProfilePage() {
  const { data: student, isLoading } = useQuery({
    queryKey: ["student-me"],
    queryFn: () => studentsApi.me(),
  });

  return (
    <div className="space-y-8">
      <PageHeader
        title="Academic Record"
        description="Official registered student dossier, program enrollment, and identity credentials."
      />

      {isLoading ? (
        <div className="rounded-lg border border-rule bg-white p-6 space-y-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : !student ? (
        <div className="rounded-lg border border-rule bg-white p-12 text-center text-xs text-slate-500">
          Unable to retrieve student profile.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Academic Dossier (2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Primary Identification Section */}
            <div className="rounded-lg border border-rule bg-white overflow-hidden">
              <div className="flex items-center justify-between p-5 border-b border-rule">
                <div>
                  <h3 className="text-sm font-semibold text-ink">Student Identification</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Primary academy registration data</p>
                </div>
                <Badge variant={student.status === "active" ? "success" : "default"}>
                  {student.status === "active" ? "Active Student" : "Completed / Inactive"}
                </Badge>
              </div>

              <div className="p-5">
                <div className="flex items-start gap-5 pb-6 border-b border-rule">
                  <div className="h-20 w-20 rounded-md border border-rule bg-slate-50 flex items-center justify-center overflow-hidden shrink-0">
                    {student.has_photo ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={studentsApi.photoUrl(student.id, student.updated_at)}
                        alt={student.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <span className="text-2xl font-serif text-slate-400">
                        {student.name.charAt(0)}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1 min-w-0">
                    <h2 className="text-lg font-semibold text-ink tracking-tight">{student.name}</h2>
                    <p className="font-mono text-xs text-slate-600">ID: {student.id_no}</p>
                    <p className="text-xs text-slate-500">
                      {student.course_name || student.legacy_course || "Foundation Program"}
                    </p>
                  </div>
                </div>

                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 pt-5 text-xs">
                  <div>
                    <dt className="text-slate-500">Program Classification</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {student.program === "CERTIFICATE" ? "Formal Diploma Track" : "Skill Training"}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-500">Admission Date</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatDate(student.admission_date)}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-500">Monthly Tuition Rate</dt>
                    <dd className="mt-1 font-medium text-ink tabular">
                      {student.monthly_fee_paise != null
                        ? `₹${(student.monthly_fee_paise / 100).toLocaleString("en-IN")}/month`
                        : "Fixed schedule"}
                    </dd>
                  </div>

                  <div>
                    <dt className="text-slate-500">Portal Credentials</dt>
                    <dd className="mt-1 font-mono text-slate-600">
                      Active · Passcode verified
                    </dd>
                  </div>
                </dl>
              </div>
            </div>

            {/* Guardian & Contact Record */}
            <div className="rounded-lg border border-rule bg-white overflow-hidden">
              <div className="p-5 border-b border-rule">
                <h3 className="text-sm font-semibold text-ink">Contact & Residence</h3>
                <p className="text-xs text-slate-500 mt-0.5">Emergency details and correspondence address</p>
              </div>

              <div className="p-5 text-xs space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-1">
                  <span className="text-slate-500">Guardian Name</span>
                  <span className="sm:col-span-2 font-medium text-ink">
                    {student.guardian_name || "—"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-1">
                  <span className="text-slate-500">Registered Phone</span>
                  <span className="sm:col-span-2 font-mono text-ink">
                    {student.contact || "—"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-1">
                  <span className="text-slate-500">Residential Address</span>
                  <span className="sm:col-span-2 text-ink leading-relaxed">
                    {student.address || "No address on file"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Identity Card Credential (1 col) */}
          <div className="space-y-6">
            <div className="rounded-lg border border-rule bg-white p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-rule">
                <div>
                  <h3 className="text-sm font-semibold text-ink">Student Identity Card</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Official printable card with barcode</p>
                </div>
                <IdCard className="h-4 w-4 text-slate-400" />
              </div>

              <div className="py-2 space-y-3 text-xs">
                {student.has_id_card ? (
                  <div className="flex items-start gap-2.5 text-emerald-800 bg-emerald-50/60 p-3 rounded-md border border-emerald-200">
                    <CheckCircle2 className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-emerald-950">ID Card Generated</p>
                      <p className="text-[11px] text-emerald-800 mt-0.5">
                        Your digital ID card has been issued by administration. You can download and print it.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-2.5 text-slate-600 bg-slate-50 p-3 rounded-md border border-rule">
                    <Clock className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-ink">Issuance in Progress</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Your card will be available once student photograph and details are validated.
                      </p>
                    </div>
                  </div>
                )}

                <div className="pt-2">
                  {student.has_id_card ? (
                    <a
                      href={idCardsApi.downloadUrl(student.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="block"
                    >
                      <Button variant="default" size="sm" className="w-full gap-2">
                        <Download className="h-3.5 w-3.5" />
                        Download ID Card PDF
                      </Button>
                    </a>
                  ) : (
                    <Button variant="outline" size="sm" disabled className="w-full">
                      Card Not Yet Issued
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
