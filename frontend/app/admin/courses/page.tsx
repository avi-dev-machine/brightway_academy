"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { coursesApi } from "@/lib/api/courses";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { formatCurrency } from "@/lib/utils";
import { toast } from "sonner";
import { GraduationCap, Plus, Search, Edit2, PowerOff, CheckCircle } from "lucide-react";
import type { Course } from "@/types/api";

export default function CoursesManagementPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);

  // Form state
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [durationMonths, setDurationMonths] = useState<number | "">("");
  const [feeRupees, setFeeRupees] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-courses", searchTerm],
    queryFn: () => coursesApi.list({ q: searchTerm || undefined }),
  });

  const courses = data?.items || [];

  const openCreateModal = () => {
    setEditingCourse(null);
    setCode("");
    setName("");
    setDescription("");
    setDurationMonths("");
    setFeeRupees("");
    setModalOpen(true);
  };

  const openEditModal = (c: Course) => {
    setEditingCourse(c);
    setCode(c.code);
    setName(c.name);
    setDescription(c.description || "");
    setDurationMonths(c.duration_months || "");
    setFeeRupees(c.default_fee_paise ? (c.default_fee_paise / 100).toString() : "");
    setModalOpen(true);
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const default_fee_paise = feeRupees ? Math.round(parseFloat(feeRupees) * 100) : null;
      const duration = durationMonths === "" ? null : Number(durationMonths);

      if (editingCourse) {
        return coursesApi.update(editingCourse.id, {
          name,
          description: description || null,
          duration_months: duration,
          default_fee_paise,
        });
      } else {
        return coursesApi.create({
          code,
          name,
          description: description || null,
          duration_months: duration,
          default_fee_paise,
        });
      }
    },
    onSuccess: () => {
      toast.success(editingCourse ? "Course updated." : "Course added.");
      setModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
    },
    onError: () => toast.error("Unable to save course record."),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: (c: Course) => coursesApi.update(c.id, { active: !c.active }),
    onSuccess: (updated) => {
      toast.success(`Course ${updated.name} ${updated.active ? "activated" : "deactivated"}.`);
      queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
    },
    onError: () => toast.error("Failed to update course status."),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Course Management
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Define curriculum programs, duration, and default fee schedules.
          </p>
        </div>
        <Button variant="primary" size="sm" className="gap-2" onClick={openCreateModal}>
          <Plus className="h-4 w-4" />
          Add New Course
        </Button>
      </div>

      <Card className="p-4 shadow-2xs">
        <div className="relative w-full max-w-sm">
          <Input
            placeholder="Search courses..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-9 text-xs"
          />
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        </div>
      </Card>

      <Card className="overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : courses.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<GraduationCap className="h-8 w-8" />}
              title="No courses found"
              action={
                <Button variant="primary" size="sm" onClick={openCreateModal}>
                  Create First Course
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Course Name</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Default Fee</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {courses.map((course) => (
                  <tr key={course.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-mono font-bold text-blue-600">{course.code}</td>
                    <td className="py-3 px-4">
                      <p className="font-semibold text-slate-900">{course.name}</p>
                      {course.description && (
                        <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{course.description}</p>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {course.duration_months ? `${course.duration_months} Months` : "—"}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      {formatCurrency(course.default_fee_paise)}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={course.active ? "success" : "default"}>
                        {course.active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs text-slate-600"
                          onClick={() => openEditModal(course)}
                        >
                          <Edit2 className="h-3.5 w-3.5 mr-1" />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className={`h-7 text-xs ${
                            course.active ? "text-amber-600 hover:bg-amber-50" : "text-emerald-600 hover:bg-emerald-50"
                          }`}
                          onClick={() => toggleActiveMutation.mutate(course)}
                        >
                          {course.active ? (
                            <>
                              <PowerOff className="h-3.5 w-3.5 mr-1" />
                              Deactivate
                            </>
                          ) : (
                            <>
                              <CheckCircle className="h-3.5 w-3.5 mr-1" />
                              Activate
                            </>
                          )}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Course Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingCourse ? "Edit Course" : "Add New Course"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Course Code *</label>
              <Input
                placeholder="e.g. DCA-101"
                value={code}
                disabled={!!editingCourse}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Course Name *</label>
              <Input
                placeholder="e.g. Diploma in Computer Applications"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Duration (Months)</label>
                <Input
                  type="number"
                  placeholder="e.g. 6"
                  value={durationMonths}
                  onChange={(e) => setDurationMonths(e.target.value === "" ? "" : Number(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Default Fee (₹)</label>
                <Input
                  type="number"
                  placeholder="e.g. 5000"
                  value={feeRupees}
                  onChange={(e) => setFeeRupees(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Course Description</label>
              <Input
                placeholder="Key topics and software covered..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="pt-3">
            <Button variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!name || (!editingCourse && !code)}
              isLoading={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              {editingCourse ? "Save Changes" : "Create Course"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
