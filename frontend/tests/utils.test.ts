import { describe, it, expect } from "vitest";
import { formatCurrency, formatDate, formatStatus } from "@/lib/utils";

describe("Formatting Utilities", () => {
  it("formats integer paise to INR currency strings", () => {
    expect(formatCurrency(150000)).toMatch(/1,500\.00/);
    expect(formatCurrency(0)).toMatch(/0\.00/);
    expect(formatCurrency(null)).toBe("₹0.00");
    expect(formatCurrency(undefined)).toBe("₹0.00");
  });

  it("formats ISO date strings cleanly", () => {
    expect(formatDate("2026-04-15")).toMatch(/15 Apr 2026/);
    expect(formatDate(null)).toBe("—");
    expect(formatDate("")).toBe("—");
  });

  it("formats enum codes to title case", () => {
    expect(formatStatus("PARTIALLY_PAID")).toBe("Partially Paid");
    expect(formatStatus("ACTIVE")).toBe("Active");
    expect(formatStatus("BANK_TRANSFER")).toBe("Bank Transfer");
  });
});
