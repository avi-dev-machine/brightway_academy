import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";

describe("UI Core Components", () => {
  it("renders button with text and handles loading state", () => {
    const { rerender } = render(<Button>Pay Now</Button>);
    expect(screen.getByRole("button", { name: "Pay Now" })).toBeInTheDocument();

    rerender(<Button isLoading>Pay Now</Button>);
    const btn = screen.getByRole("button", { name: "Pay Now" });
    expect(btn).toBeDisabled();
  });

  it("renders status badge variants", () => {
    const { container } = render(<Badge variant="success">Paid</Badge>);
    expect(container.firstChild).toHaveTextContent("Paid");
  });

  it("renders EmptyState with title and action button", () => {
    render(
      <EmptyState
        title="No students found"
        description="Try adjusting your filter"
        action={<button>Add Student</button>}
      />,
    );

    expect(screen.getByText("No students found")).toBeInTheDocument();
    expect(screen.getByText("Try adjusting your filter")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Student" })).toBeInTheDocument();
  });
});
