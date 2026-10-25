"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { toast } from "sonner";
import { UserCheck, Plus, Search, Edit2, Phone, Mail, PowerOff } from "lucide-react";
import type { Teacher } from "@/types/api";

export default function TeachersManagementPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTeacher, setEditingTeacher] = useState<Teacher | null>(null);

  // Form
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["admin-teachers", searchTerm],
    queryFn: () => teachersApi.list({ q: searchTerm || undefined }),
  });

  const teachers = data?.items || [];

  const openCreateModal = () => {
    setEditingTeacher(null);
    setName("");
    setPhone("");
    setEmail("");
    setModalOpen(true);
  };

  const openEditModal = (t: Teacher) => {
    setEditingTeacher(t);
    setName(t.name);
    setPhone(t.phone || "");
    setEmail(t.email || "");
    setModalOpen(true);
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      if (editingTeacher) {
        return teachersApi.update(editingTeacher.id, {
          name,
          phone: phone || null,
          email: email || null,
        });
      } else {
        return teachersApi.create({
          name,
          phone: phone || null,
          email: email || null,
        });
      }
    },
    onSuccess: () => {
      toast.success(editingTeacher ? "Instructor updated." : "Instructor added.");
      setModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["admin-teachers"] });
    },
    onError: () => toast.error("Unable to save instructor record."),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: (t: Teacher) => teachersApi.update(t.id, { active: !t.active }),
    onSuccess: (updated) => {
      toast.success(`Instructor ${updated.name} ${updated.active ? "activated" : "deactivated"}.`);
      queryClient.invalidateQueries({ queryKey: ["admin-teachers"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Instructor & Faculty Management
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage academy teachers, contact information, and teaching assignments.
          </p>
        </div>
        <Button variant="primary" size="sm" className="gap-2" onClick={openCreateModal}>
          <Plus className="h-4 w-4" />
          Add Instructor
        </Button>
      </div>

      <Card className="p-4 shadow-2xs">
        <div className="relative w-full max-w-sm">
          <Input
            placeholder="Search instructors..."
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
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : teachers.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={<UserCheck className="h-8 w-8" />}
              title="No instructors found"
              action={
                <Button variant="primary" size="sm" onClick={openCreateModal}>
                  Add Instructor
                </Button>
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Instructor Name</th>
                  <th className="py-3 px-4">Phone</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {teachers.map((teacher) => (
                  <tr key={teacher.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-semibold text-slate-900">{teacher.name}</td>
                    <td className="py-3 px-4 text-slate-600 font-mono">
                      {teacher.phone ? (
                        <span className="flex items-center gap-1.5">
                          <Phone className="h-3 w-3 text-slate-400" />
                          {teacher.phone}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {teacher.email ? (
                        <span className="flex items-center gap-1.5">
                          <Mail className="h-3 w-3 text-slate-400" />
                          {teacher.email}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={teacher.active ? "success" : "default"}>
                        {teacher.active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs text-slate-600"
                          onClick={() => openEditModal(teacher)}
                        >
                          <Edit2 className="h-3.5 w-3.5 mr-1" />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs text-amber-600 hover:bg-amber-50"
                          onClick={() => toggleActiveMutation.mutate(teacher)}
                        >
                          <PowerOff className="h-3.5 w-3.5 mr-1" />
                          {teacher.active ? "Deactivate" : "Activate"}
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

      {/* Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingTeacher ? "Edit Instructor" : "Add Instructor"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Full Name *</label>
              <Input
                placeholder="e.g. Priya Sharma"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Phone Number</label>
              <Input
                placeholder="e.g. 9876543210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Email Address</label>
              <Input
                placeholder="e.g. priya@brightwayacademy.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter className="pt-3">
            <Button variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!name}
              isLoading={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              Save Record
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
