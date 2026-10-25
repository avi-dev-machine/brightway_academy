"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./button";

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  isLoading?: boolean;
}

export function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
  isLoading,
}: PaginationProps) {
  if (total === 0) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  const pages = Math.max(1, totalPages);

  return (
    <nav
      aria-label="Pagination"
      className="flex items-center justify-between gap-4 border-t border-rule px-3 py-2.5 text-xs text-slate-500"
    >
      <p className="tabular-nums">
        <span className="text-ink">
          {start}–{end}
        </span>{" "}
        of {total.toLocaleString("en-IN")}
      </p>
      <div className="flex items-center gap-1">
        <span className="mr-2 hidden tabular-nums sm:inline">
          Page {page} of {pages}
        </span>
        <Button
          variant="outline"
          size="icon"
          className="h-7 w-7"
          aria-label="Previous page"
          disabled={page <= 1 || isLoading}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-7 w-7"
          aria-label="Next page"
          disabled={page >= pages || isLoading}
          onClick={() => onPageChange(page + 1)}
        >
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </nav>
  );
}
