"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const navLinks = [
  { href: "/courses", label: "Courses" },
  { href: "/admissions", label: "Admissions" },
  { href: "/about", label: "Academy" },
  { href: "/contact", label: "Location" },
];

export function PublicHeader() {
  const [isOpen, setIsOpen] = useState(false);
  const academyName =
    process.env.NEXT_PUBLIC_ACADEMY_NAME || "Brightway Computer Academy";

  return (
    <header className="sticky top-0 z-40 w-full border-b border-rule bg-white/95 backdrop-blur-xs">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6 lg:px-8">
        {/* Editorial Wordmark */}
        <Link href="/" className="flex items-baseline gap-2.5 group">
          <span className="display text-2xl tracking-tight text-ink group-hover:text-blue-700 transition-colors">
            {academyName}
          </span>
          <span className="hidden sm:inline text-[11px] font-medium text-slate-400">
            Est. 2018 · Govt. Regd.
          </span>
        </Link>

        {/* Desktop Navigation */}
        <nav aria-label="Main menu" className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-600">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="transition-colors hover:text-ink"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Action Controls */}
        <div className="hidden md:flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm" className="text-xs text-slate-600">
              Student Portal
              <ArrowUpRight className="h-3.5 w-3.5 ml-1 text-slate-400" />
            </Button>
          </Link>
          <Link href="/admissions">
            <Button variant="default" size="sm" className="text-xs">
              Apply for Admission
            </Button>
          </Link>
        </div>

        {/* Mobile menu trigger */}
        <button
          type="button"
          className="md:hidden rounded-md p-1.5 text-slate-600 hover:bg-slate-100 cursor-pointer"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle navigation menu"
        >
          {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile drawer */}
      {isOpen && (
        <div className="border-b border-rule bg-white px-6 py-5 md:hidden animate-fade-in">
          <div className="flex flex-col space-y-3">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className="text-sm font-medium text-slate-700 hover:text-ink py-1"
              >
                {link.label}
              </Link>
            ))}
            <div className="flex flex-col gap-2 pt-4 border-t border-rule">
              <Link href="/login" onClick={() => setIsOpen(false)}>
                <Button variant="outline" size="sm" className="w-full justify-center text-xs">
                  Student Portal
                </Button>
              </Link>
              <Link href="/admissions" onClick={() => setIsOpen(false)}>
                <Button variant="default" size="sm" className="w-full justify-center text-xs">
                  Apply for Admission
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
