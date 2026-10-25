"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/providers/auth-provider";
import {
  LayoutGrid,
  Users,
  UserPlus,
  BookOpen,
  Layers,
  UserCheck,
  CalendarCheck,
  IdCard,
  Wallet,
  ReceiptText,
  MessageSquare,
  BarChart3,
  FileUp,
  Settings,
  LogOut,
  Menu,
  X,
  Eye,
  EyeOff,
  ArrowUpRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  exact?: boolean;
}

interface NavGroup {
  section: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    section: "Academy",
    items: [
      { href: "/admin", label: "Overview", icon: LayoutGrid, exact: true },
      { href: "/admin/students", label: "Students", icon: Users },
      { href: "/admin/admissions", label: "Admissions", icon: UserPlus },
    ],
  },
  {
    section: "Teaching",
    items: [
      { href: "/admin/courses", label: "Courses", icon: BookOpen },
      { href: "/admin/batches", label: "Batches", icon: Layers },
      { href: "/admin/teachers", label: "Teachers", icon: UserCheck },
      { href: "/admin/attendance", label: "Attendance", icon: CalendarCheck },
      { href: "/admin/id-cards", label: "ID cards", icon: IdCard },
    ],
  },
  {
    section: "Finance",
    items: [
      { href: "/admin/fees", label: "Fees & dues", icon: Wallet },
      { href: "/admin/receipts", label: "Receipts", icon: ReceiptText },
      { href: "/admin/notifications", label: "Messages", icon: MessageSquare },
    ],
  },
  {
    section: "System",
    items: [
      { href: "/admin/reports", label: "Reports", icon: BarChart3 },
      { href: "/admin/import", label: "Import", icon: FileUp },
      { href: "/admin/settings", label: "Settings", icon: Settings },
    ],
  },
];

const allItems = navGroups.flatMap((g) => g.items);

function isActive(pathname: string | null, href: string, exact?: boolean) {
  if (!pathname) return false;
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLinks({ pathname, onNavigate }: { pathname: string | null; onNavigate?: () => void }) {
  return (
    <div className="space-y-5">
      {navGroups.map((group) => (
        <div key={group.section}>
          <p className="px-3 pb-1.5 text-[11px] font-medium text-slate-500">{group.section}</p>
          <ul className="space-y-px">
            {group.items.map((item) => {
              const active = isActive(pathname, item.href, item.exact);
              const Icon = item.icon;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "group relative flex h-8 items-center gap-2.5 rounded-md px-3 text-[13px] transition-colors duration-150",
                      active
                        ? "bg-white/[0.07] text-white"
                        : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100",
                    )}
                  >
                    {active && (
                      <span
                        aria-hidden
                        className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-blue-400"
                      />
                    )}
                    <Icon
                      strokeWidth={1.75}
                      className={cn(
                        "h-[15px] w-[15px]",
                        active ? "text-blue-300" : "text-slate-500 group-hover:text-slate-300",
                      )}
                    />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}

/**
 * Reading the URL suspends during prerendering of routes with unknown dynamic params
 * (e.g. /admin/students/[id]) when Cache Components is enabled. Only these small parts
 * read it, each inside <Suspense>, so the rest of the shell still prerenders.
 */
function ActiveNavLinks(props: { onNavigate?: () => void }) {
  return <NavLinks pathname={usePathname()} {...props} />;
}

function NavigationLinks(props: { onNavigate?: () => void }) {
  return (
    <Suspense fallback={<NavLinks pathname={null} {...props} />}>
      <ActiveNavLinks {...props} />
    </Suspense>
  );
}

function CurrentSection() {
  const pathname = usePathname();
  const match = [...allItems]
    .sort((a, b) => b.href.length - a.href.length)
    .find((item) => isActive(pathname, item.href, item.exact));
  const isDetail = match && pathname !== match.href;
  return (
    <div className="flex min-w-0 items-center gap-1.5 text-[13px]">
      <span className="text-slate-400">Admin</span>
      <span className="text-slate-300">/</span>
      {isDetail ? (
        <>
          <Link href={match.href} className="text-slate-500 hover:text-ink">
            {match.label}
          </Link>
          <span className="text-slate-300">/</span>
          <span className="truncate font-medium text-ink">Detail</span>
        </>
      ) : (
        <span className="truncate font-medium text-ink">{match?.label ?? "Overview"}</span>
      )}
    </div>
  );
}

function Wordmark({ inverted = false }: { inverted?: boolean }) {
  return (
    <span className="flex items-baseline gap-2">
      <span className={cn("display text-[22px] leading-none", inverted ? "text-white" : "text-ink")}>
        Brightway
      </span>
      <span
        className={cn(
          "text-[11px] font-medium",
          inverted ? "text-slate-500" : "text-slate-400",
        )}
      >
        Admin
      </span>
    </span>
  );
}

export function AdminLayout({ children }: { children: ReactNode }) {
  const { user, login, logout, isLoading } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isVerified, setIsVerified] = useState<boolean | null>(null);
  const [adminId, setAdminId] = useState("BWADMIN");
  const [passcode, setPasscode] = useState("");
  const [showPasscode, setShowPasscode] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("brightway_admin_session_verified");
      setIsVerified(stored === "true" && user?.role === "ADMIN");
    }
  }, [user]);

  const handleAuthorize = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsVerifying(true);
    try {
      const logged = await login({
        identifier: adminId.trim(),
        password: passcode,
      });
      if (logged.role !== "ADMIN") {
        setErrorMsg("This account does not have administrator access.");
        return;
      }
      sessionStorage.setItem("brightway_admin_session_verified", "true");
      setIsVerified(true);
    } catch {
      setErrorMsg("The ID or passcode is incorrect.");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleSignOut = async () => {
    sessionStorage.removeItem("brightway_admin_session_verified");
    setIsVerified(false);
    await logout();
  };

  if (isVerified === null || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper" aria-busy>
        <span className="sr-only">Loading</span>
        <div className="h-px w-24 overflow-hidden bg-rule">
          <div className="h-full w-1/3 animate-pulse bg-ink/60" />
        </div>
      </div>
    );
  }

  // Passcode gate: the admin console requires verification on every session.
  if (!isVerified) {
    return (
      <div className="flex min-h-screen flex-col bg-paper">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
          <Wordmark />
          <Link href="/" className="text-[13px] text-slate-500 hover:text-ink">
            Back to website
          </Link>
        </div>

        <main className="flex flex-1 items-center justify-center px-6 pb-24">
          <div className="w-full max-w-sm animate-rise">
            <h1 className="text-xl font-semibold tracking-[-0.02em] text-ink">
              Sign in to the console
            </h1>
            <p className="mt-1.5 text-sm text-slate-500">
              The passcode is requested at the start of every session.
            </p>

            <form onSubmit={handleAuthorize} className="mt-8 space-y-4" noValidate>
              {errorMsg && (
                <p
                  role="alert"
                  className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[13px] text-rose-800"
                >
                  {errorMsg}
                </p>
              )}

              <div className="space-y-1.5">
                <label htmlFor="admin-id" className="text-[13px] font-medium text-ink">
                  Administrator ID
                </label>
                <Input
                  id="admin-id"
                  type="text"
                  value={adminId}
                  onChange={(e) => setAdminId(e.target.value)}
                  autoComplete="username"
                  required
                  className="font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="admin-passcode" className="text-[13px] font-medium text-ink">
                  Passcode
                </label>
                <div className="relative">
                  <Input
                    id="admin-passcode"
                    type={showPasscode ? "text" : "password"}
                    value={passcode}
                    onChange={(e) => setPasscode(e.target.value)}
                    autoComplete="current-password"
                    required
                    autoFocus
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasscode(!showPasscode)}
                    aria-label={showPasscode ? "Hide passcode" : "Show passcode"}
                    className="absolute right-1 top-1 flex h-7 w-7 items-center justify-center rounded-sm text-slate-400 hover:text-ink cursor-pointer"
                  >
                    {showPasscode ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button type="submit" className="w-full" isLoading={isVerifying}>
                Continue
              </Button>
            </form>
          </div>
        </main>
      </div>
    );
  }

  const displayName = user?.display_name || user?.email || "Administrator";
  const initials = displayName
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const sidebarFooter = (
    <div className="border-t border-white/[0.06] p-3">
      <div className="flex items-center gap-2.5 px-2 py-1.5">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10 text-[11px] font-medium text-slate-200">
          {initials}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] text-slate-200">{displayName}</p>
          <p className="text-[11px] text-slate-500">Administrator</p>
        </div>
        <button
          onClick={handleSignOut}
          aria-label="Sign out"
          title="Sign out"
          className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-white/[0.06] hover:text-slate-200 cursor-pointer"
        >
          <LogOut className="h-[15px] w-[15px]" strokeWidth={1.75} />
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-white">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col bg-navy lg:flex">
        <div className="flex h-14 items-center px-5">
          <Link href="/admin">
            <Wordmark inverted />
          </Link>
        </div>
        <nav aria-label="Admin" className="flex-1 overflow-y-auto px-2 py-3">
          <NavigationLinks />
        </nav>
        {sidebarFooter}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden" role="dialog" aria-modal="true">
          <div className="fixed inset-0 bg-ink/40 animate-fade-in" onClick={() => setMobileOpen(false)} />
          <div className="relative z-10 flex w-64 flex-col bg-navy animate-drawer-in">
            <div className="flex h-14 items-center justify-between px-5">
              <Wordmark inverted />
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation"
                className="rounded-md p-1.5 text-slate-400 hover:bg-white/[0.06] hover:text-white cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <nav aria-label="Admin" className="flex-1 overflow-y-auto px-2 py-3">
              <NavigationLinks onNavigate={() => setMobileOpen(false)} />
            </nav>
            {sidebarFooter}
          </div>
        </div>
      )}

      {/* Workspace */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-rule px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setMobileOpen(true)}
              className="-ml-1.5 rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-ink lg:hidden cursor-pointer"
              aria-label="Open navigation"
            >
              <Menu className="h-[18px] w-[18px]" />
            </button>
            <Suspense fallback={<span className="text-[13px] text-slate-400">Admin</span>}>
              <CurrentSection />
            </Suspense>
          </div>
          <Link
            href="/"
            target="_blank"
            className="inline-flex items-center gap-1 text-[13px] text-slate-500 transition-colors hover:text-ink"
          >
            Website
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
