import { TeacherLayout } from "@/components/layout/teacher-layout";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Teacher Portal",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <TeacherLayout>{children}</TeacherLayout>;
}
