import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, id, ...props }, ref) => {
    const generatedId = React.useId();
    const errorId = error ? `${id ?? generatedId}-error` : undefined;
    return (
      <div className="w-full">
        <input
          id={id}
          type={type}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          className={cn(
            "flex h-9 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-ink transition-[border-color,box-shadow] duration-150 placeholder:text-slate-400 hover:border-slate-400 focus-visible:border-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600/15 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-60",
            error && "border-rose-500 hover:border-rose-500 focus-visible:border-rose-600 focus-visible:ring-rose-600/15",
            className,
          )}
          ref={ref}
          {...props}
        />
        {error && (
          <p id={errorId} className="mt-1.5 text-xs text-rose-700">
            {error}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = "Input";

export { Input };
