"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api/admin";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  Settings,
  Building2,
  Bell,
  CreditCard,
  Server,
  Users,
  CheckCircle2,
  Shield,
} from "lucide-react";
import type { AcademySettings, Role } from "@/types/api";

export default function AdminSettingsPage() {
  const queryClient = useQueryClient();

  const { data: allSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ["admin-all-settings"],
    queryFn: () => adminApi.getAllSettings(),
  });

  const { data: systemStatus, isLoading: statusLoading } = useQuery({
    queryKey: ["admin-system-status"],
    queryFn: () => adminApi.getSystemStatus(),
  });

  const { data: usersData } = useQuery({
    queryKey: ["admin-users-list"],
    queryFn: () => adminApi.listUsers({ page_size: 20 }),
  });

  const { data: setupStatus } = useQuery({
    queryKey: ["admin-setup-status-page"],
    queryFn: () => adminApi.getSetupStatus(),
  });

  // Local Academy form state
  const [academyName, setAcademyName] = useState("");
  const [academyAddress, setAcademyAddress] = useState("");
  const [academyPhone, setAcademyPhone] = useState("");
  const [academyEmail, setAcademyEmail] = useState("");
  const [idPrefix, setIdPrefix] = useState("");
  const [receiptPrefix, setReceiptPrefix] = useState("");
  const [formInitialized, setFormInitialized] = useState(false);

  // User invite modal state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("TEACHER");

  if (allSettings && !formInitialized) {
    setAcademyName(allSettings.academy?.name || "");
    setAcademyAddress(allSettings.academy?.address || "");
    setAcademyPhone(allSettings.academy?.phone || "");
    setAcademyEmail(allSettings.academy?.email || "");
    setIdPrefix(allSettings.academy?.student_id_prefix || "BW");
    setReceiptPrefix(allSettings.academy?.receipt_prefix || "RCP");
    setFormInitialized(true);
  }

  const updateAcademyMutation = useMutation({
    mutationFn: () =>
      adminApi.updateAcademySettings({
        name: academyName,
        address: academyAddress,
        phone: academyPhone,
        email: academyEmail,
        student_id_prefix: idPrefix,
        receipt_prefix: receiptPrefix,
      }),
    onSuccess: () => {
      toast.success("Academy settings saved.");
      queryClient.invalidateQueries({ queryKey: ["admin-all-settings"] });
    },
    onError: () => toast.error("Failed to update academy settings."),
  });

  const inviteUserMutation = useMutation({
    mutationFn: () =>
      adminApi.inviteUser({
        email: inviteEmail,
        role: inviteRole,
      }),
    onSuccess: () => {
      toast.success(`Invite dispatched to ${inviteEmail}.`);
      setInviteEmail("");
      queryClient.invalidateQueries({ queryKey: ["admin-users-list"] });
    },
    onError: () => toast.error("Unable to send user invite."),
  });

  const completeSetupMutation = useMutation({
    mutationFn: () => adminApi.completeSetup(),
    onSuccess: () => {
      toast.success("Academy setup marked as completed!");
      queryClient.invalidateQueries({ queryKey: ["admin-setup-status-page"] });
    },
    onError: () => toast.error("Setup completion check failed."),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Academy Configuration & Settings
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Branding, prefixes, notifications, system integration health, and user roles.
          </p>
        </div>

        {setupStatus && !setupStatus.setup_completed && (
          <Button
            variant="primary"
            size="sm"
            isLoading={completeSetupMutation.isPending}
            onClick={() => completeSetupMutation.mutate()}
            className="gap-2"
          >
            <CheckCircle2 className="h-4 w-4" />
            Complete First-Run Setup
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Academy Branding & Prefixes Form */}
        <Card className="lg:col-span-2 shadow-2xs">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4 text-blue-600" />
              Academy Profile & ID Prefixes
            </CardTitle>
            <CardDescription className="text-xs">
              Displayed on generated ID cards, printed receipts, and public headers.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {settingsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-9 w-full" />
                <Skeleton className="h-9 w-full" />
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Academy Name *
                    </label>
                    <Input
                      value={academyName}
                      onChange={(e) => setAcademyName(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Office Contact Phone
                    </label>
                    <Input
                      value={academyPhone}
                      onChange={(e) => setAcademyPhone(e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Office Email
                    </label>
                    <Input
                      type="email"
                      value={academyEmail}
                      onChange={(e) => setAcademyEmail(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Campus Physical Address
                    </label>
                    <Input
                      value={academyAddress}
                      onChange={(e) => setAcademyAddress(e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Student ID Prefix
                    </label>
                    <Input
                      className="font-mono"
                      value={idPrefix}
                      onChange={(e) => setIdPrefix(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Receipt Number Prefix
                    </label>
                    <Input
                      className="font-mono"
                      value={receiptPrefix}
                      onChange={(e) => setReceiptPrefix(e.target.value)}
                    />
                  </div>
                </div>
              </>
            )}
          </CardContent>
          <CardFooter className="flex justify-end pt-3 border-t border-slate-100">
            <Button
              variant="primary"
              size="sm"
              isLoading={updateAcademyMutation.isPending}
              onClick={() => updateAcademyMutation.mutate()}
            >
              Save Academy Profile
            </Button>
          </CardFooter>
        </Card>

        {/* System & Gateway Status Card */}
        <Card className="shadow-2xs">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="h-4 w-4 text-emerald-600" />
              Integration Health
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-4 text-xs">
            {statusLoading ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <>
                <div className="flex items-center justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Environment</span>
                  <Badge variant="default" className="uppercase font-mono text-[10px]">
                    {systemStatus?.app_env || "development"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Payment Gateway</span>
                  <Badge variant="success" className="font-mono text-[10px]">
                    {systemStatus?.payment_provider || "ONLINE"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Storage Backend</span>
                  <span className="font-mono text-slate-700">{systemStatus?.storage_backend}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">WhatsApp Gateway</span>
                  <Badge variant={systemStatus?.whatsapp_configured ? "success" : "default"}>
                    {systemStatus?.whatsapp_configured ? "CONFIGURED" : "LOGGING ONLY"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between py-1">
                  <span className="text-slate-500">SMS Gateway</span>
                  <Badge variant={systemStatus?.sms_configured ? "success" : "default"}>
                    {systemStatus?.sms_configured ? "CONFIGURED" : "LOGGING ONLY"}
                  </Badge>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* User Accounts & Invites */}
      <Card className="shadow-2xs">
        <CardHeader className="border-b border-slate-100 pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-600" />
            Authorized Portal Accounts
          </CardTitle>
          <CardDescription className="text-xs">
            Invite teachers or academy administrators into the portal system.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-4 space-y-4">
          {/* Invite toolbar */}
          <div className="flex flex-wrap items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
            <Input
              type="email"
              placeholder="instructor@example.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="max-w-xs h-9 bg-white text-xs"
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as Role)}
              className="h-9 rounded-lg border border-slate-300 bg-white px-3 text-xs text-slate-700 focus:outline-blue-600"
            >
              <option value="TEACHER">Teacher / Faculty</option>
              <option value="ADMIN">Administrator</option>
            </select>
            <Button
              variant="primary"
              size="sm"
              disabled={!inviteEmail}
              isLoading={inviteUserMutation.isPending}
              onClick={() => inviteUserMutation.mutate()}
              className="text-xs"
            >
              Dispatch Invite
            </Button>
          </div>

          {/* Users List */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                <tr>
                  <th className="py-2.5 px-4">Account Email</th>
                  <th className="py-2.5 px-4">Assigned Role</th>
                  <th className="py-2.5 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {usersData?.items?.map((u) => (
                  <tr key={u.user_id}>
                    <td className="py-2.5 px-4 font-mono font-medium text-slate-900">{u.email}</td>
                    <td className="py-2.5 px-4">
                      <Badge variant={u.role === "ADMIN" ? "info" : "success"}>{u.role}</Badge>
                    </td>
                    <td className="py-2.5 px-4">
                      <span className="text-emerald-600 font-medium text-xs">Active</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
