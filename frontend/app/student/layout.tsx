import { StudentLayout } from "@/components/layout/student-layout";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Student Portal",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <StudentLayout>{children}</StudentLayout>;
}
