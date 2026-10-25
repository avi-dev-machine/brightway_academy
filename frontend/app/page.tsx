import Link from "next/link";
import { PublicHeader } from "@/components/layout/public-header";
import { PublicFooter } from "@/components/layout/public-footer";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  Clock,
  BookOpen,
  MapPin,
  Calendar,
  ShieldCheck,
  CreditCard,
  IdCard,
} from "lucide-react";

export default function HomePage() {
  const academyName =
    process.env.NEXT_PUBLIC_ACADEMY_NAME || "Brightway Computer Academy";
  const academyAddress = process.env.NEXT_PUBLIC_ACADEMY_ADDRESS;

  return (
    <div className="flex min-h-screen flex-col bg-white text-ink selection:bg-blue-100 selection:text-blue-900">
      <PublicHeader />

      <main className="flex-1">
        {/* ===================================================================
            01. HERO: Editorial Split Layout
           =================================================================== */}
        <section className="border-b border-rule bg-paper pt-16 pb-20 sm:pt-24 sm:pb-28">
          <div className="mx-auto max-w-6xl px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
              {/* Left Column: Editorial Statement */}
              <div className="lg:col-span-7 space-y-6">
                <div className="inline-flex items-center gap-2 text-xs font-mono text-slate-500 uppercase tracking-widest">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />
                  Technical Education &amp; Vocational Training
                </div>

                <h1 className="display text-4xl sm:text-5xl lg:text-6xl text-ink leading-[1.05] tracking-tight">
                  Practical computer education, rigorous certification, and transparent academic administration.
                </h1>

                <p className="text-base text-slate-600 max-w-xl leading-relaxed text-pretty">
                  Brightway equips students with industry-relevant software skills, professional accounting systems, and programming fundamentals. Every enrollment is backed by dedicated laboratory hours, structured installment management, and verifiable credentials.
                </p>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <Link href="/admissions">
                    <Button variant="default" size="lg" className="text-sm font-medium gap-2">
                      Apply for Admission
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>

                  <Link href="/courses">
                    <Button variant="outline" size="lg" className="text-sm font-medium">
                      Explore Course Syllabi
                    </Button>
                  </Link>
                </div>

                {/* Quiet Trust Markers */}
                <div className="pt-8 border-t border-rule grid grid-cols-2 sm:grid-cols-3 gap-6 text-xs text-slate-500">
                  <div>
                    <span className="block font-semibold text-ink text-sm">Govt. Registered</span>
                    Recognised curriculum standards
                  </div>
                  <div>
                    <span className="block font-semibold text-ink text-sm">Hands-on Labs</span>
                    Dedicated daily terminal sessions
                  </div>
                  <div>
                    <span className="block font-semibold text-ink text-sm">Digital Ledger</span>
                    Itemised fees &amp; official receipts
                  </div>
                </div>
              </div>

              {/* Right Column: Realistic Product Artifact (Student Dossier & Verification) */}
              <div className="lg:col-span-5">
                <div className="rounded-lg border border-rule bg-white shadow-sm overflow-hidden text-xs">
                  {/* Fake UI Titlebar */}
                  <div className="flex items-center justify-between px-4 py-3 border-b border-rule bg-slate-50/70">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                    </div>
                    <span className="font-mono text-[11px] text-slate-500">
                      brightway.edu/portal
                    </span>
                    <span className="text-[11px] text-emerald-700 font-medium">Verified Active</span>
                  </div>

                  {/* Student Dossier Preview */}
                  <div className="p-5 space-y-4">
                    <div className="flex items-start justify-between pb-4 border-b border-rule">
                      <div>
                        <p className="text-[11px] uppercase font-mono tracking-wider text-slate-400">
                          Student Academic Record
                        </p>
                        <h4 className="text-sm font-semibold text-ink mt-0.5">
                          Aman Kumar Sharma
                        </h4>
                        <p className="font-mono text-[11px] text-slate-500">
                          ID: RG240019 · ADCA Diploma
                        </p>
                      </div>
                      <span className="rounded-sm bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-800 ring-1 ring-inset ring-emerald-200">
                        In Good Standing
                      </span>
                    </div>

                    {/* Milestone rows */}
                    <div className="space-y-2.5 font-mono text-[11px]">
                      <div className="flex items-center justify-between text-slate-600">
                        <span>Attendance rate</span>
                        <span className="font-semibold text-ink">94% (47 of 50 classes)</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-600">
                        <span>Current installment</span>
                        <span className="text-emerald-700 font-medium">Settled · Receipt #BW-2408</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-600">
                        <span>Digital ID status</span>
                        <span className="text-ink">Issued with barcode verification</span>
                      </div>
                    </div>

                    {/* Live Receipt Clip */}
                    <div className="rounded-md border border-rule bg-paper p-3 font-mono text-[11px] space-y-1 text-slate-600">
                      <div className="flex justify-between font-semibold text-ink">
                        <span>OFFICIAL PAYMENT VOUCHER</span>
                        <span>₹1,500.00</span>
                      </div>
                      <div className="flex justify-between text-[10px] text-slate-400">
                        <span>TallyPrime &amp; GST Module</span>
                        <span>UPI-20261024-8842</span>
                      </div>
                    </div>
                  </div>

                  {/* Bottom Strip */}
                  <div className="px-5 py-2.5 border-t border-rule bg-slate-50/50 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Direct access for students &amp; guardians</span>
                    <Link href="/login" className="text-blue-700 hover:underline font-medium inline-flex items-center gap-0.5">
                      Log in to portal <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================================
            02. ACADEMIC PROGRAMS DIRECTORY
           =================================================================== */}
        <section className="py-20 sm:py-24 border-b border-rule bg-white">
          <div className="mx-auto max-w-6xl px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-12 border-b border-rule">
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase tracking-widest">
                  Academic Offerings
                </p>
                <h2 className="display text-3xl sm:text-4xl text-ink mt-2">
                  Industry-Aligned Curricula
                </h2>
              </div>
              <p className="text-xs text-slate-500 max-w-sm leading-relaxed">
                Courses structured from foundational digital literacy to professional accounting, publishing, and programming careers.
              </p>
            </div>

            {/* Courses Matrix */}
            <div className="divide-y divide-rule pt-4">
              {/* DCA */}
              <div className="py-6 grid grid-cols-1 md:grid-cols-12 gap-4 items-baseline">
                <div className="md:col-span-4">
                  <span className="font-mono text-xs text-slate-400">01</span>
                  <h3 className="text-base font-semibold text-ink mt-0.5">
                    Diploma in Computer Application (DCA)
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">Foundation certification for professional office environments.</p>
                </div>
                <div className="md:col-span-5 text-xs text-slate-600 leading-relaxed">
                  Windows operating systems, MS Office Suite (Word, Excel, PowerPoint), Internet operations, computer architecture, and bilingual typing.
                </div>
                <div className="md:col-span-3 text-right text-xs space-y-1">
                  <span className="font-mono text-slate-500">6 Months · Diploma Track</span>
                  <div>
                    <Link href="/courses" className="text-blue-700 hover:underline font-medium inline-flex items-center gap-1">
                      Syllabus &amp; Fees <ArrowUpRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              </div>

              {/* ADCA */}
              <div className="py-6 grid grid-cols-1 md:grid-cols-12 gap-4 items-baseline">
                <div className="md:col-span-4">
                  <span className="font-mono text-xs text-slate-400">02</span>
                  <h3 className="text-base font-semibold text-ink mt-0.5">
                    Advance Diploma in Computer Application (ADCA)
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">Comprehensive 1-year flagship diploma covering computing and design.</p>
                </div>
                <div className="md:col-span-5 text-xs text-slate-600 leading-relaxed">
                  Full DCA curriculum plus Desktop Publishing (CorelDraw, Photoshop, PageMaker), Tally accounting basics, and internet publishing fundamentals.
                </div>
                <div className="md:col-span-3 text-right text-xs space-y-1">
                  <span className="font-mono text-slate-500">12 Months · Professional Track</span>
                  <div>
                    <Link href="/courses" className="text-blue-700 hover:underline font-medium inline-flex items-center gap-1">
                      Syllabus &amp; Fees <ArrowUpRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              </div>

              {/* TallyPrime */}
              <div className="py-6 grid grid-cols-1 md:grid-cols-12 gap-4 items-baseline">
                <div className="md:col-span-4">
                  <span className="font-mono text-xs text-slate-400">03</span>
                  <h3 className="text-base font-semibold text-ink mt-0.5">
                    TallyPrime with GST &amp; Business Accounting
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">Practical computerized bookkeeping for retail, trading, and service businesses.</p>
                </div>
                <div className="md:col-span-5 text-xs text-slate-600 leading-relaxed">
                  Ledger management, voucher entry, inventory tracking, GST calculation, e-way bills, TDS deductions, and balance sheet finalization.
                </div>
                <div className="md:col-span-3 text-right text-xs space-y-1">
                  <span className="font-mono text-slate-500">3 Months · Vocational Certificate</span>
                  <div>
                    <Link href="/courses" className="text-blue-700 hover:underline font-medium inline-flex items-center gap-1">
                      Syllabus &amp; Fees <ArrowUpRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              </div>

              {/* DTP & Graphic Design */}
              <div className="py-6 grid grid-cols-1 md:grid-cols-12 gap-4 items-baseline">
                <div className="md:col-span-4">
                  <span className="font-mono text-xs text-slate-400">04</span>
                  <h3 className="text-base font-semibold text-ink mt-0.5">
                    Desktop Publishing &amp; Graphic Layout (DTP)
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">Design and layout production for commercial print and digital branding.</p>
                </div>
                <div className="md:col-span-5 text-xs text-slate-600 leading-relaxed">
                  Vector graphics in CorelDraw, digital photo retouching in Adobe Photoshop, typography layouts, publication formatting, and commercial print preparation.
                </div>
                <div className="md:col-span-3 text-right text-xs space-y-1">
                  <span className="font-mono text-slate-500">3 Months · Creative Certificate</span>
                  <div>
                    <Link href="/courses" className="text-blue-700 hover:underline font-medium inline-flex items-center gap-1">
                      Syllabus &amp; Fees <ArrowUpRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================================
            03. THE ACADEMY OPERATING PRINCIPLES
           =================================================================== */}
        <section className="py-20 sm:py-24 border-b border-rule bg-paper">
          <div className="mx-auto max-w-6xl px-6 lg:px-8">
            <div className="max-w-2xl pb-12">
              <p className="text-xs font-mono text-slate-500 uppercase tracking-widest">
                Institutional Standards
              </p>
              <h2 className="display text-3xl sm:text-4xl text-ink mt-2">
                Built for serious learners, operated with total institutional clarity.
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-4">
              {/* Column 1 */}
              <div className="space-y-3">
                <span className="font-mono text-xs text-slate-400">01 / Pedagogy</span>
                <h3 className="text-base font-semibold text-ink">
                  Guaranteed 1:1 Lab Terminals
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  We maintain strict laboratory batch caps so every student works on a dedicated machine during every practical session. No shared screens or theoretical-only classes.
                </p>
              </div>

              {/* Column 2 */}
              <div className="space-y-3">
                <span className="font-mono text-xs text-slate-400">02 / Transparency</span>
                <h3 className="text-base font-semibold text-ink">
                  Digitally Immutable Accounting
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Every rupee collected is recorded in an immutable ledger. Students and guardians receive immediate digital receipts and automated WhatsApp statements without manual disputes.
                </p>
              </div>

              {/* Column 3 */}
              <div className="space-y-3">
                <span className="font-mono text-xs text-slate-400">03 / Credentials</span>
                <h3 className="text-base font-semibold text-ink">
                  Verifiable Academic IDs &amp; Diplomas
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Graduates receive government-recognized diplomas with individual certificate serials and QR-verifiable student ID cards that validate credentials to employers.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================================
            04. CAMPUS LOCATION & ADMISSIONS CONSULTATION
           =================================================================== */}
        <section className="py-20 sm:py-24 bg-white">
          <div className="mx-auto max-w-6xl px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
              <div className="lg:col-span-5 space-y-5">
                <p className="text-xs font-mono text-slate-500 uppercase tracking-widest">
                  Campus &amp; Admissions
                </p>
                <h2 className="display text-3xl sm:text-4xl text-ink">
                  Visit our campus for in-person counseling.
                </h2>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Prospective students are welcome to tour our computer laboratory, review syllabus handouts, and speak with instructors before confirming admission.
                </p>

                <div className="space-y-3 pt-3 text-xs">
                  <div className="flex items-start gap-2.5">
                    <MapPin className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-ink block">Campus Address</span>
                      <span className="text-slate-600">{academyAddress || "Main Academy Road, City Campus"}</span>
                    </div>
                  </div>

                  <div className="flex items-start gap-2.5">
                    <Clock className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-ink block">Office &amp; Laboratory Hours</span>
                      <span className="text-slate-600">Monday through Saturday · 9:00 AM – 7:00 PM</span>
                    </div>
                  </div>
                </div>

                <div className="pt-4 flex flex-wrap gap-3">
                  <Link href="/admissions">
                    <Button variant="default" size="sm">
                      Submit Online Admission Form
                    </Button>
                  </Link>
                  <Link href="/contact">
                    <Button variant="outline" size="sm">
                      Get Driving Directions
                    </Button>
                  </Link>
                </div>
              </div>

              {/* Right: Admission Requirements & Protocol */}
              <div className="lg:col-span-7">
                <div className="rounded-lg border border-rule bg-paper p-6 space-y-4">
                  <h3 className="text-sm font-semibold text-ink">
                    Admission Protocol &amp; Required Documents
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Enrollment is open year-round with morning, afternoon, and evening batches to accommodate both school students and working professionals.
                  </p>

                  <ul className="space-y-2.5 text-xs text-slate-700 pt-2">
                    <li className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-blue-700 shrink-0 mt-0.5" />
                      <span>2 recent passport-size photographs for digital ID registration</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-blue-700 shrink-0 mt-0.5" />
                      <span>Copy of highest educational qualification certificate (10th / 12th / Degree)</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-blue-700 shrink-0 mt-0.5" />
                      <span>Government photo identification card (Aadhaar / Voter ID / School ID)</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <Check className="h-4 w-4 text-blue-700 shrink-0 mt-0.5" />
                      <span>First installment or full tuition payment via UPI, Cash, or NetBanking</span>
                    </li>
                  </ul>

                  <div className="pt-4 border-t border-rule flex items-center justify-between text-xs text-slate-500">
                    <span>Batch capacity limited to maintain machine ratios.</span>
                    <Link href="/admissions" className="text-blue-700 hover:underline font-medium">
                      Check batch availability →
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
