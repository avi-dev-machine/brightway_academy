import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Compact status label. Square-ish geometry and low-saturation fills keep
 * badges legible in dense tables without turning rows into confetti.
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-sm px-1.5 py-px text-[11px] font-medium leading-[18px] whitespace-nowrap tabular-nums",
  {
    variants: {
      variant: {
        default: "bg-slate-100 text-slate-700",
        success: "bg-emerald-50 text-emerald-800 ring-1 ring-inset ring-emerald-200/70",
        warning: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200/70",
        danger: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-200/70",
        info: "bg-blue-50 text-blue-800 ring-1 ring-inset ring-blue-200/70",
        outline: "text-slate-600 ring-1 ring-inset ring-slate-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
