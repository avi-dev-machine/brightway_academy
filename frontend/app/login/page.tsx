"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuth } from "@/providers/auth-provider";
import { getErrorMessage } from "@/lib/api/errors";
import { GraduationCap, Eye, EyeOff, Lock, Mail, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const loginSchema = z.object({
  identifier: z.string().min(1, "Student ID, Admin ID, or Email is required"),
  password: z.string().min(1, "Password or Passcode is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectPath = searchParams.get("redirect");
  const { login } = useAuth();

  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setServerError(null);
    try {
      const user = await login({
        identifier: data.identifier.trim(),
        email: data.identifier.includes("@") ? data.identifier.trim() : undefined,
        password: data.password,
      });
      if (redirectPath) {
        router.push(redirectPath);
        return;
      }
      if (user.role === "ADMIN") {
        router.push("/admin");
      } else if (user.role === "TEACHER") {
        router.push("/teacher");
      } else {
        router.push("/student");
      }
    } catch (err) {
      setServerError(getErrorMessage(err));
    }
  };

  const academyName =
    process.env.NEXT_PUBLIC_ACADEMY_NAME || "Brightway Computer Academy";

  return (
    <div className="flex min-h-screen flex-col justify-center bg-slate-50 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link href="/" className="inline-flex items-center gap-2 group">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm transition-transform group-hover:scale-105">
            <GraduationCap className="h-6 w-6" />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900">
            {academyName}
          </span>
        </Link>
        <h2 className="mt-6 text-2xl font-bold tracking-tight text-slate-900">
          Sign in to your portal
        </h2>
        <p className="mt-2 text-xs text-slate-500">
          Students, teachers, and academy administrators
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <Card className="shadow-md">
          <CardHeader className="pb-4">
            <CardTitle>Sign In</CardTitle>
            <CardDescription>
              Enter your Student ID, Admin ID, or registered email and passcode
            </CardDescription>
          </CardHeader>
          <CardContent>
            {serverError && (
              <div
                role="alert"
                className="mb-4 rounded-lg bg-rose-50 p-3 text-xs font-medium text-rose-700 border border-rose-200"
              >
                {serverError}
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label
                  htmlFor="identifier"
                  className="block text-xs font-medium text-slate-700 mb-1"
                >
                  Student ID, Admin ID, or Email
                </label>
                <div className="relative">
                  <Input
                    id="identifier"
                    type="text"
                    autoComplete="username"
                    placeholder="e.g. BWADMIN or RG240017"
                    error={errors.identifier?.message}
                    {...register("identifier")}
                    className="pl-9"
                  />
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                </div>
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="block text-xs font-medium text-slate-700 mb-1"
                >
                  Passcode / Password
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    error={errors.password?.message}
                    {...register("password")}
                    className="pl-9 pr-10"
                  />
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                  <button
                    type="button"
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 cursor-pointer"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="rounded-md bg-blue-50/70 p-2.5 text-[11px] text-blue-800 border border-blue-100 leading-relaxed">
                <span className="font-semibold">Student Login Hint:</span> Your passcode is the first 3 letters of your name (in uppercase) + the last 4 digits of your Student ID (e.g., <code className="bg-blue-100/70 px-1 py-0.5 rounded font-mono">AGN0017</code> for RG240017).
              </div>

              <Button
                type="submit"
                variant="primary"
                className="w-full mt-2 gap-2"
                isLoading={isSubmitting}
              >
                Sign In
                <ArrowRight className="h-4 w-4" />
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-xs text-slate-500">
          Need an account or having trouble signing in?{" "}
          <Link href="/contact" className="font-medium text-blue-600 hover:underline">
            Contact Academy Desk
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-900 border-t-transparent" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
