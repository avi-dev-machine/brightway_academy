import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-sm font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 active:translate-y-px disabled:pointer-events-none disabled:opacity-45 select-none cursor-pointer [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-ink text-white hover:bg-slate-800 active:bg-slate-950",
        primary: "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800",
        accent: "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800",
        destructive: "bg-rose-600 text-white hover:bg-rose-700 active:bg-rose-800",
        outline:
          "border border-slate-300 bg-white text-ink hover:border-slate-400 hover:bg-slate-50 active:bg-slate-100",
        secondary: "bg-slate-100 text-ink hover:bg-slate-200/80 active:bg-slate-200",
        ghost: "text-slate-600 hover:bg-slate-100 hover:text-ink active:bg-slate-200/70",
        link: "h-auto p-0 font-medium text-blue-700 underline-offset-4 hover:underline active:translate-y-0",
      },
      size: {
        default: "h-9 px-3.5",
        sm: "h-8 px-3 text-[13px]",
        lg: "h-11 px-5 text-[15px]",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        aria-busy={isLoading || undefined}
        {...props}
      >
        {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
