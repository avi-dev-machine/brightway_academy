import { describe, it, expect } from "vitest";
import {
  ApiError,
  errorFromBody,
  extractFieldErrors,
  fallbackMessage,
  normalizeError,
  ERROR_MESSAGES,
} from "@/lib/api/errors";

describe("API Error Normalization Contract", () => {
  it("normalizes backend 4xx domain errors while preserving safe messages", () => {
    const err = errorFromBody(404, {
      code: "STUDENT_NOT_FOUND",
      message: "Student was not found.",
      request_id: "req_123",
    });

    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.code).toBe("STUDENT_NOT_FOUND");
    expect(err.message).toBe("Student was not found.");
    expect(err.isNotFound).toBe(true);
  });

  it("sanitizes 500 server errors to prevent internal leakage", () => {
    const err = errorFromBody(500, {
      code: "INTERNAL_SERVER_ERROR",
      message: "psycopg.OperationalError: database connection terminated",
      request_id: "req_err_999",
    });

    expect(err.status).toBe(500);
    // Internal exception message must not be exposed to user
    expect(err.message).toBe(ERROR_MESSAGES.server);
    expect(err.message).not.toContain("psycopg");
  });

  it("normalizes fetch network failures into user-friendly message", () => {
    const netErr = new TypeError("Failed to fetch");
    const normalized = normalizeError(netErr);

    expect(normalized.code).toBe("NETWORK_ERROR");
    expect(normalized.message).toBe(ERROR_MESSAGES.network);
    expect(normalized.isNetwork).toBe(true);
  });

  it("extracts field errors from validation error details", () => {
    const details = [
      { field: "body.name", message: "Value error, Student name is required" },
      { field: "body.contact", message: "Contact number must be 10 digits" },
    ];
    const fields = extractFieldErrors(details);

    expect(fields.name).toBe("Student name is required");
    expect(fields.contact).toBe("Contact number must be 10 digits");
  });
});
