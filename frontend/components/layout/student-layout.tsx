"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/providers/auth-provider";
import {
  LayoutDashboard,
  CreditCard,
  Receipt,
  CalendarCheck,
  User,
  Bell,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";

const studentNav = [
  { href: "/student", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/student/fees", label: "Fees & dues", icon: CreditCard },
  { href: "/student/receipts", label: "Receipts", icon: Receipt },
  { href: "/student/attendance", label: "Attendance", icon: CalendarCheck },
  { href: "/student/profile", label: "Academic record", icon: User },
];

export function StudentLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { logout } = useAuth();

  const isActive = (href: string, exact?: boolean) => {
    if (!pathname) return false;
    if (exact) return pathname === href;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <div className="flex min-h-screen flex-col bg-white pb-16 md:pb-0">
      {/* Top Header */}
      <header className="sticky top-0 z-30 border-b border-rule bg-white">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
          <Link href="/student" className="flex items-baseline gap-2">
            <span className="display text-xl leading-none text-ink">Brightway</span>
            <span className="text-[11px] font-medium text-slate-400">Student</span>
          </Link>

          {/* Desktop Nav */}
          <nav aria-label="Student portal" className="hidden md:flex items-center gap-1">
            {studentNav.map((item) => {
              const active = isActive(item.href, item.exact);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    active
                      ? "bg-slate-100 text-ink"
                      : "text-slate-500 hover:text-ink hover:bg-slate-50",
                  )}
                >
                  <Icon
                    strokeWidth={1.75}
                    className={cn(
                      "h-3.5 w-3.5",
                      active ? "text-blue-700" : "text-slate-400",
                    )}
                  />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* User actions */}
          <div className="flex items-center gap-1.5">
            <Link
              href="/student/notifications"
              aria-label="Notifications"
              className="flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-ink transition-colors"
            >
              <Bell className="h-4 w-4" strokeWidth={1.75} />
            </Link>

            <button
              onClick={() => logout()}
              aria-label="Sign out"
              title="Sign out"
              className="hidden sm:inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-ink transition-colors cursor-pointer"
            >
              <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Page Content */}
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        {children}
      </main>

      {/* Mobile Bottom Navigation */}
      <nav
        aria-label="Mobile navigation"
        className="fixed bottom-0 left-0 right-0 z-40 flex h-14 items-center justify-around border-t border-rule bg-white md:hidden"
      >
        {studentNav.map((item) => {
          const active = isActive(item.href, item.exact);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-col items-center justify-center py-1 transition-colors",
                active ? "text-blue-700 font-medium" : "text-slate-500 hover:text-ink",
              )}
            >
              <Icon strokeWidth={1.75} className="h-4 w-4" />
              <span className="text-[10px] mt-1">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
