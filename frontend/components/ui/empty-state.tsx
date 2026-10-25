import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex min-h-[200px] flex-col items-center justify-center px-6 py-10 text-center",
        className,
      )}
    >
      {icon && <div className="mb-3 text-slate-300 [&_svg]:h-5 [&_svg]:w-5">{icon}</div>}
      <h3 className="text-sm font-medium text-ink">{title}</h3>
      {description && (
        <p className="mt-1 max-w-xs text-[13px] leading-relaxed text-slate-500">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
