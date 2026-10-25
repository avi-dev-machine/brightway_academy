import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Consistent page heading for application routes. */
export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-subtitle max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

/**
 * A single metric. Label above, value below, optional secondary line.
 * Rendered inside a shared strip rather than as an individual floating card.
 */
export function Metric({
  label,
  value,
  detail,
  tone = "default",
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "default" | "danger" | "success";
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 bg-white px-5 py-4", className)}>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd
        className={cn(
          "mt-1.5 text-xl font-semibold tracking-[-0.02em] tabular-nums",
          tone === "danger" && "text-rose-700",
          tone === "success" && "text-emerald-700",
          tone === "default" && "text-ink",
        )}
      >
        {value}
      </dd>
      {detail && <div className="mt-1 text-xs text-slate-500 tabular-nums">{detail}</div>}
    </div>
  );
}

/** Horizontal strip of metrics separated by hairlines. */
export function MetricStrip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <dl
      className={cn(
        "grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-rule bg-rule lg:grid-cols-4",
        className,
      )}
    >
      {children}
    </dl>
  );
}

/** Section heading inside a page: title + optional trailing link/action. */
export function SectionHeading({
  title,
  description,
  action,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-end justify-between gap-4", className)}>
      <div className="min-w-0">
        <h2 className="section-title">{title}</h2>
        {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}
