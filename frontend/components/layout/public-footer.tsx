"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export function PublicFooter() {
  const year = 2026;

  const academyName =
    process.env.NEXT_PUBLIC_ACADEMY_NAME || "Brightway Computer Academy";
  const academyAddress = process.env.NEXT_PUBLIC_ACADEMY_ADDRESS;
  const academyPhone = process.env.NEXT_PUBLIC_ACADEMY_PHONE;
  const academyEmail = process.env.NEXT_PUBLIC_ACADEMY_EMAIL;
  const academyHours = process.env.NEXT_PUBLIC_ACADEMY_HOURS;

  return (
    <footer className="border-t border-rule bg-paper text-slate-600">
      <div className="mx-auto max-w-6xl px-6 py-14 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10">
          {/* Brand Column */}
          <div className="md:col-span-4 space-y-3">
            <Link href="/" className="inline-block">
              <span className="display text-2xl tracking-tight text-ink">
                {academyName}
              </span>
            </Link>
            <p className="text-xs text-slate-500 leading-relaxed max-w-sm">
              An institution dedicated to foundational and advanced practical computer education, certified vocational diplomas, and verifiable skill training.
            </p>
            <p className="text-[11px] text-slate-400 font-mono">
              Govt. Registered Institution · ISO Certified
            </p>
          </div>

          {/* Academic Courses */}
          <div className="md:col-span-3 space-y-2.5">
            <h4 className="text-xs font-semibold text-ink">Academic Programs</h4>
            <ul className="space-y-1.5 text-xs text-slate-500">
              <li>
                <Link href="/courses" className="hover:text-ink transition-colors">
                  Diploma in Computer Application (DCA)
                </Link>
              </li>
              <li>
                <Link href="/courses" className="hover:text-ink transition-colors">
                  Advance Diploma (ADCA)
                </Link>
              </li>
              <li>
                <Link href="/courses" className="hover:text-ink transition-colors">
                  TallyPrime &amp; GST Accounting
                </Link>
              </li>
              <li>
                <Link href="/courses" className="hover:text-ink transition-colors">
                  Desktop Publishing &amp; Graphic Tools
                </Link>
              </li>
              <li>
                <Link href="/courses" className="hover:text-ink transition-colors">
                  Python Programming &amp; Web Basics
                </Link>
              </li>
            </ul>
          </div>

          {/* Direct Portals */}
          <div className="md:col-span-2 space-y-2.5">
            <h4 className="text-xs font-semibold text-ink">Member Access</h4>
            <ul className="space-y-1.5 text-xs text-slate-500">
              <li>
                <Link href="/login" className="hover:text-ink inline-flex items-center gap-1 transition-colors">
                  Student Portal
                  <ArrowUpRight className="h-3 w-3 text-slate-400" />
                </Link>
              </li>
              <li>
                <Link href="/admin" className="hover:text-ink inline-flex items-center gap-1 transition-colors">
                  Administration
                  <ArrowUpRight className="h-3 w-3 text-slate-400" />
                </Link>
              </li>
              <li>
                <Link href="/admissions" className="hover:text-ink transition-colors">
                  Online Admission
                </Link>
              </li>
              <li>
                <Link href="/contact" className="hover:text-ink transition-colors">
                  Campus Location
                </Link>
              </li>
            </ul>
          </div>

          {/* Campus Desk */}
          <div className="md:col-span-3 space-y-2.5 text-xs text-slate-500">
            <h4 className="text-xs font-semibold text-ink">Campus &amp; Office</h4>
            <p className="leading-relaxed">
              {academyAddress || "Academy campus address available through administration desk."}
            </p>
            {academyPhone && (
              <p className="font-mono text-slate-600">
                Phone: {academyPhone}
              </p>
            )}
            {academyEmail && (
              <p>
                Email: <span className="text-slate-600">{academyEmail}</span>
              </p>
            )}
            <p className="text-[11px] text-slate-400">
              {academyHours || "Monday – Saturday: 9:00 AM – 7:00 PM"}
            </p>
          </div>
        </div>

        {/* Bottom Hairline & Legal */}
        <div className="mt-12 pt-6 border-t border-rule flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
          <p>© {year} {academyName}. All institutional rights reserved.</p>
          <div className="flex items-center gap-4 text-[11px]">
            <span>Verified Certification Registry</span>
            <span>·</span>
            <span>Fee Transparency Protocol</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
