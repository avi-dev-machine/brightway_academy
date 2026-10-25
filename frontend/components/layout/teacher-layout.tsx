"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/providers/auth-provider";
import {
  LayoutDashboard,
  CalendarCheck,
  Layers,
  LogOut,
  GraduationCap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const teacherNav = [
  { href: "/teacher", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/teacher/attendance", label: "Mark Attendance", icon: CalendarCheck },
  { href: "/teacher/batches", label: "My Batches", icon: Layers },
];

export function TeacherLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isActive = (href: string, exact?: boolean) => {
    if (exact) return pathname === href;
    return pathname.startsWith(href);
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-6">
            <Link href="/teacher" className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600 text-white">
                <GraduationCap className="h-5 w-5" />
              </div>
              <div>
                <span className="text-sm font-bold text-slate-900 leading-tight">Brightway</span>
                <span className="ml-1 text-[11px] font-medium text-emerald-600">Teacher Portal</span>
              </div>
            </Link>

            <nav className="hidden sm:flex items-center gap-1">
              {teacherNav.map((item) => {
                const active = isActive(item.href, item.exact);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                      active
                        ? "bg-emerald-50 text-emerald-800 font-semibold"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:block text-right">
              <p className="text-xs font-semibold text-slate-900">{user?.display_name || user?.email}</p>
              <Badge variant="success" className="text-[10px] py-0 px-1.5">
                TEACHER
              </Badge>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="text-xs text-rose-600 hover:bg-rose-50"
              onClick={() => logout()}
            >
              <LogOut className="h-3.5 w-3.5 mr-1" />
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
    </div>
  );
}
