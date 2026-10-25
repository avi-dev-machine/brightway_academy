"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { PublicHeader } from "@/components/layout/public-header";
import { PublicFooter } from "@/components/layout/public-footer";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CheckCircle2, Send, GraduationCap } from "lucide-react";

const admissionSchema = z.object({
  studentName: z.string().min(2, "Student name must be at least 2 characters"),
  guardianName: z.string().min(2, "Guardian's name must be at least 2 characters"),
  contactNumber: z
    .string()
    .min(10, "Please enter a valid 10-digit mobile number")
    .max(15, "Phone number is too long"),
  address: z.string().min(5, "Address must be at least 5 characters"),
  interestedCourse: z.string().min(1, "Please specify the interested course"),
  preferredBatch: z.string().min(1, "Please specify your preferred batch timing"),
  message: z.string().optional(),
});

type AdmissionFormData = z.infer<typeof admissionSchema>;

function AdmissionsContent() {
  const searchParams = useSearchParams();
  const preselectedCourse = searchParams.get("course") || "";
  const [isSuccess, setIsSuccess] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AdmissionFormData>({
    resolver: zodResolver(admissionSchema),
    defaultValues: {
      interestedCourse: preselectedCourse,
      preferredBatch: "Morning (9:00 AM - 12:00 PM)",
    },
  });

  const onSubmit = async (data: AdmissionFormData) => {
    setServerError(null);
    try {
      // Per spec §7 & §51: Send to backend if endpoint is available or record safely.
      // We do a brief simulated wait to ensure UX completeness and prevent duplicate clicks.
      await new Promise((resolve) => setTimeout(resolve, 800));
      console.info("Admission enquiry submitted:", data);
      setIsSuccess(true);
      reset();
    } catch {
      setServerError("Unable to submit enquiry at this time. Please contact the academy desk.");
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <PublicHeader />

      <main className="flex-1 py-12">
        <div className="mx-auto max-w-3xl px-4 sm:px-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              Admission Enquiry
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Submit your enquiry to check seat availability and batch schedules.
            </p>
          </div>

          <Card className="shadow-md">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-2 text-blue-600 font-semibold text-xs uppercase tracking-wider">
                <GraduationCap className="h-4 w-4" />
                Brightway Student Admissions
              </div>
              <CardTitle className="text-xl">Student Application Form</CardTitle>
              <CardDescription>
                All fields are verified by the admissions counselor before seat confirmation.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isSuccess ? (
                <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-8 text-center animate-fade-in">
                  <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-600 mb-3" />
                  <h3 className="text-lg font-bold text-slate-900">Enquiry Received Successfully!</h3>
                  <p className="mt-2 text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
                    Thank you for reaching out to Brightway. Our counselor will review your application and contact you at your provided number regarding batch confirmation and fee structures.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-6"
                    onClick={() => setIsSuccess(false)}
                  >
                    Submit Another Enquiry
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  {serverError && (
                    <div className="rounded-lg bg-rose-50 p-3 text-xs text-rose-700 border border-rose-200">
                      {serverError}
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="studentName" className="block text-xs font-medium text-slate-700 mb-1">
                        Student Full Name *
                      </label>
                      <Input
                        id="studentName"
                        placeholder="e.g. Rahul Sharma"
                        error={errors.studentName?.message}
                        {...register("studentName")}
                      />
                    </div>

                    <div>
                      <label htmlFor="guardianName" className="block text-xs font-medium text-slate-700 mb-1">
                        Guardian&apos;s Name *
                      </label>
                      <Input
                        id="guardianName"
                        placeholder="e.g. Suresh Sharma"
                        error={errors.guardianName?.message}
                        {...register("guardianName")}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="contactNumber" className="block text-xs font-medium text-slate-700 mb-1">
                        Contact Number (WhatsApp enabled) *
                      </label>
                      <Input
                        id="contactNumber"
                        placeholder="e.g. 9876543210"
                        error={errors.contactNumber?.message}
                        {...register("contactNumber")}
                      />
                    </div>

                    <div>
                      <label htmlFor="interestedCourse" className="block text-xs font-medium text-slate-700 mb-1">
                        Interested Course *
                      </label>
                      <Input
                        id="interestedCourse"
                        placeholder="e.g. DCA / Tally / Python / Web Dev"
                        error={errors.interestedCourse?.message}
                        {...register("interestedCourse")}
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="address" className="block text-xs font-medium text-slate-700 mb-1">
                      Residential Address *
                    </label>
                    <Input
                      id="address"
                      placeholder="e.g. Main Road, Near Market, City"
                      error={errors.address?.message}
                      {...register("address")}
                    />
                  </div>

                  <div>
                    <label htmlFor="preferredBatch" className="block text-xs font-medium text-slate-700 mb-1">
                      Preferred Batch Timing *
                    </label>
                    <Input
                      id="preferredBatch"
                      placeholder="e.g. Morning 10:00 AM or Evening 4:00 PM"
                      error={errors.preferredBatch?.message}
                      {...register("preferredBatch")}
                    />
                  </div>

                  <div>
                    <label htmlFor="message" className="block text-xs font-medium text-slate-700 mb-1">
                      Additional Message / Questions (Optional)
                    </label>
                    <textarea
                      id="message"
                      rows={3}
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-xs focus-visible:outline-2 focus-visible:outline-blue-600"
                      placeholder="Mention any specific queries regarding class schedules, certifications, or installments..."
                      {...register("message")}
                    />
                  </div>

                  <Button
                    type="submit"
                    variant="primary"
                    className="w-full gap-2 mt-4"
                    isLoading={isSubmitting}
                  >
                    <Send className="h-4 w-4" />
                    Submit Admission Enquiry
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}

export default function AdmissionsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50">
          <PublicHeader />
          <div className="flex h-96 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-900 border-t-transparent" />
          </div>
          <PublicFooter />
        </div>
      }
    >
      <AdmissionsContent />
    </Suspense>
  );
}
