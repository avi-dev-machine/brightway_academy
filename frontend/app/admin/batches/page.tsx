"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { batchesApi } from "@/lib/api/batches";
import { coursesApi } from "@/lib/api/courses";
import { teachersApi } from "@/lib/api/teachers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { formatDate } from "@/lib/utils";
import { toast } from "sonner";
import { Layers, Plus, Users, Calendar, UserCheck, X } from "lucide-react";
import type { Batch, Student } from "@/types/api";

export default function BatchesManagementPage() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBatch, setEditingBatch] = useState<Batch | null>(null);

  // Roster modal
  const [rosterBatch, setRosterBatch] = useState<Batch | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [courseId, setCourseId] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [schedule, setSchedule] = useState("");
  const [capacity, setCapacity] = useState<number | "">("");

  const { data: batchesData, isLoading } = useQuery({
    queryKey: ["admin-batches"],
    queryFn: () => batchesApi.list({ page_size: 50 }),
  });

  const { data: coursesData } = useQuery({
    queryKey: ["admin-courses-active"],
    queryFn: () => coursesApi.list({ active: true }),
  });

  const { data: teachersData } = useQuery({
    queryKey: ["admin-teachers-active"],
    queryFn: () => teachersApi.list({ active: true }),
  });

  const { data: rosterStudents, isLoading: rosterLoading } = useQuery({
    queryKey: ["batch-students", rosterBatch?.id],
    queryFn: () => batchesApi.students(rosterBatch!.id),
    enabled: !!rosterBatch,
  });

  const batches = batchesData?.items || [];

  const openCreateModal = () => {
    setEditingBatch(null);
    setName("");
    setCourseId(coursesData?.items?.[0]?.id || "");
    setTeacherId("");
    setSchedule("");
    setCapacity("");
    setModalOpen(true);
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const cap = capacity === "" ? null : Number(capacity);
      if (editingBatch) {
        return batchesApi.update(editingBatch.id, {
          name,
          teacher_id: teacherId || null,
          schedule: schedule || null,
          capacity: cap,
        });
      } else {
        return batchesApi.create({
          course_id: courseId,
          name,
          teacher_id: teacherId || null,
          schedule: schedule || null,
          capacity: cap,
        });
      }
    },
    onSuccess: () => {
      toast.success(editingBatch ? "Batch updated." : "Batch created.");
      setModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-batches"] });
    },
    onError: () => toast.error("Failed to save batch."),
  });

  const removeStudentMutation = useMutation({
    mutationFn: ({ batchId, studentId }: { batchId: string; studentId: string }) =>
      batchesApi.removeStudent(batchId, studentId),
    onSuccess: () => {
      toast.success("Student removed from batch.");
      queryClient.invalidateQueries({ queryKey: ["batch-students", rosterBatch?.id] });
      queryClient.invalidateQueries({ queryKey: ["admin-batches"] });
    },
    onError: () => toast.error("Failed to remove student from batch."),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Batch Management
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Organize student cohorts, instructor assignments, and class schedules.
          </p>
        </div>
        <Button variant="primary" size="sm" className="gap-2" onClick={openCreateModal}>
          <Plus className="h-4 w-4" />
          Create New Batch
        </Button>
      </div>

      <Card className="overflow-hidden shadow-2xs">
        {isLoading ? (
          <div className="p-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : batches.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<Layers className="h-8 w-8" />}
              title="No batches created"
              action={
                <Button variant="primary" size="sm" onClick={openCreateModal}>
                  Create First Batch
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Batch Name</th>
                  <th className="py-3 px-4">Course</th>
                  <th className="py-3 px-4">Assigned Teacher</th>
                  <th className="py-3 px-4">Schedule</th>
                  <th className="py-3 px-4">Enrolled / Cap</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {batches.map((batch) => (
                  <tr key={batch.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-bold text-slate-900">{batch.name}</td>
                    <td className="py-3 px-4 text-slate-700">{batch.course_name || "—"}</td>
                    <td className="py-3 px-4 text-slate-600">
                      {batch.teacher_name ? (
                        <span className="flex items-center gap-1">
                          <UserCheck className="h-3.5 w-3.5 text-emerald-600" />
                          {batch.teacher_name}
                        </span>
                      ) : (
                        <span className="text-slate-400">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-mono text-[11px]">
                      {batch.schedule || "—"}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-slate-900">{batch.student_count ?? 0}</span>
                      {batch.capacity && (
                        <span className="text-slate-400"> / {batch.capacity}</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={batch.active ? "success" : "default"}>
                        {batch.active ? "Active" : "Archived"}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        onClick={() => setRosterBatch(batch)}
                      >
                        <Users className="h-3 w-3" />
                        Students ({batch.student_count ?? 0})
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Batch Create/Edit Dialog */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingBatch ? "Edit Batch" : "Create New Batch"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Batch Name *</label>
              <Input
                placeholder="e.g. DCA Morning Batch 2026-A"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            {!editingBatch && (
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Course *</label>
                <select
                  value={courseId}
                  onChange={(e) => setCourseId(e.target.value)}
                  className="w-full h-9.5 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
                >
                  {coursesData?.items?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Assigned Teacher</label>
              <select
                value={teacherId}
                onChange={(e) => setTeacherId(e.target.value)}
                className="w-full h-9.5 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
              >
                <option value="">No Teacher Assigned</option>
                {teachersData?.items?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Schedule / Timings</label>
                <Input
                  placeholder="e.g. Mon-Fri 10:00 AM"
                  value={schedule}
                  onChange={(e) => setSchedule(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Capacity</label>
                <Input
                  type="number"
                  placeholder="e.g. 25"
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value === "" ? "" : Number(e.target.value))}
                />
              </div>
            </div>
          </div>
          <DialogFooter className="pt-3">
            <Button variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!name || (!editingBatch && !courseId)}
              isLoading={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              Save Batch
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Batch Students Roster Modal */}
      <Dialog open={!!rosterBatch} onOpenChange={(open) => !open && setRosterBatch(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Enrolled Students — {rosterBatch?.name}</DialogTitle>
          </DialogHeader>
          <div className="max-h-80 overflow-y-auto space-y-2 py-2">
            {rosterLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : rosterStudents?.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">
                No students currently assigned to this batch.
              </p>
            ) : (
              rosterStudents?.map((student) => (
                <div
                  key={student.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 p-2.5 text-xs hover:bg-slate-50"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{student.name}</p>
                    <p className="font-mono text-[10px] text-slate-500">ID: {student.id_no}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-rose-600 hover:bg-rose-50 text-[10px]"
                    onClick={() =>
                      removeStudentMutation.mutate({
                        batchId: rosterBatch!.id,
                        studentId: student.id,
                      })
                    }
                  >
                    <X className="h-3 w-3 mr-1" />
                    Remove
                  </Button>
                </div>
              ))
            )}
          </div>
          <DialogFooter className="pt-2">
            <Button variant="outline" onClick={() => setRosterBatch(null)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
