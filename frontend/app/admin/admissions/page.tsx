"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { UserPlus, Phone, Calendar } from "lucide-react";
import Link from "next/link";

export default function AdminAdmissionsQueuePage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Admissions Queue
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Incoming public enquiry submissions awaiting counselor follow-up and batch enrollment.
          </p>
        </div>

        <Link href="/admin/students">
          <Button variant="primary" size="sm" className="gap-1.5 text-xs">
            <UserPlus className="h-3.5 w-3.5" />
            Direct Student Enrollment
          </Button>
        </Link>
      </div>

      <Card className="p-8">
        <EmptyState
          icon={<UserPlus className="h-8 w-8" />}
          title="No pending enquiries in queue"
          description="Public admission enquiry forms submitted on the academy website will appear here for counseling follow-up."
          action={
            <Link href="/admissions" target="_blank">
              <Button variant="outline" size="sm">
                View Public Admissions Form ↗
              </Button>
            </Link>
          }
        />
      </Card>
    </div>
  );
}
