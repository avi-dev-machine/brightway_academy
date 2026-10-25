import { PublicHeader } from "@/components/layout/public-header";
import { PublicFooter } from "@/components/layout/public-footer";
import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2, Shield, Target, Users, Award, BookOpen } from "lucide-react";

export default function AboutPage() {
  const academyName =
    process.env.NEXT_PUBLIC_ACADEMY_NAME || "Brightway Computer Academy";

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <PublicHeader />

      <main className="flex-1 py-12">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              About {academyName}
            </h1>
            <p className="mt-3 text-sm text-slate-600 leading-relaxed">
              Dedicated to delivering accessible, rigorous, and employment-focused technology education to learners of all levels.
            </p>
          </div>

          <div className="space-y-12">
            {/* Mission & Vision */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <Card>
                <CardContent className="p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 mb-4">
                    <Target className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">Our Mission</h3>
                  <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                    To make digital literacy, software competencies, and modern technological tools accessible, empowering every student with the confidence and qualification required in today&apos;s digital workforce.
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600 mb-4">
                    <Award className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">Our Vision</h3>
                  <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                    To be the leading regional centre of computer learning known for transparent administration, verified educational standards, and practical student outcomes.
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Core Values */}
            <div className="rounded-2xl bg-white p-8 border border-slate-200">
              <h2 className="text-xl font-bold text-slate-900 mb-6">Our Core Educational Principles</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div>
                  <div className="flex items-center gap-2 font-semibold text-sm text-slate-900 mb-2">
                    <BookOpen className="h-4 w-4 text-blue-600" />
                    Hands-On Laboratory First
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Every theoretical concept is supported by immediate practical laboratory execution on individual terminals.
                  </p>
                </div>

                <div>
                  <div className="flex items-center gap-2 font-semibold text-sm text-slate-900 mb-2">
                    <Users className="h-4 w-4 text-blue-600" />
                    Dedicated Mentorship
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Small batch sizes ensure personalized feedback and prompt doubt clearance by experienced instructors.
                  </p>
                </div>

                <div>
                  <div className="flex items-center gap-2 font-semibold text-sm text-slate-900 mb-2">
                    <Shield className="h-4 w-4 text-blue-600" />
                    Transparency & Trust
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Transparent fee installments, verified ID credentials, and permanent digital payment receipts for all enrolled learners.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
