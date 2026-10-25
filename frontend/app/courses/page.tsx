"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { coursesApi } from "@/lib/api/courses";
import { PublicHeader } from "@/components/layout/public-header";
import { PublicFooter } from "@/components/layout/public-footer";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { formatCurrency } from "@/lib/utils";
import Link from "next/link";
import { BookOpen, Clock, Search, ArrowRight } from "lucide-react";

export default function CoursesPage() {
  const [searchTerm, setSearchTerm] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["public-courses", searchTerm],
    queryFn: () => coursesApi.list({ active: true, q: searchTerm || undefined }),
  });

  const courses = data?.items || [];

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <PublicHeader />

      <main className="flex-1 py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
              Academic Courses & Programs
            </h1>
            <p className="mt-3 text-sm text-slate-600">
              Practical, certification-oriented computer programs designed for beginners and advancing professionals.
            </p>

            {/* Search input */}
            <div className="mt-6 relative max-w-md mx-auto">
              <Input
                type="text"
                placeholder="Search by course name or code..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 bg-white"
              />
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            </div>
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Card key={i} className="h-48 p-6 space-y-4">
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-16 w-full" />
                </Card>
              ))}
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center text-xs text-rose-700">
              Unable to load course catalog at this time. Please try refreshing.
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && courses.length === 0 && (
            <EmptyState
              icon={<BookOpen className="h-8 w-8" />}
              title="No courses found"
              description={
                searchTerm
                  ? `No course matching "${searchTerm}". Try a different search query.`
                  : "Course catalog is currently being updated by the administration."
              }
              action={
                searchTerm ? (
                  <Button variant="outline" size="sm" onClick={() => setSearchTerm("")}>
                    Clear Search
                  </Button>
                ) : undefined
              }
            />
          )}

          {/* Courses grid */}
          {!isLoading && !error && courses.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {courses.map((course) => (
                <Card key={course.id} className="flex flex-col justify-between shadow-xs hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-center justify-between gap-2">
                      <Badge variant="info" className="text-[10px]">
                        {course.code}
                      </Badge>
                      {course.duration_months && (
                        <div className="flex items-center gap-1 text-xs text-slate-500">
                          <Clock className="h-3.5 w-3.5" />
                          <span>{course.duration_months} Months</span>
                        </div>
                      )}
                    </div>
                    <CardTitle className="mt-2 text-lg">{course.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                      {course.description || "Comprehensive hands-on training module covering foundational theory, guided laboratory practice, and assessment."}
                    </p>
                    <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-xs text-slate-500">Standard Fee:</span>
                      <span className="text-sm font-semibold text-slate-900">
                        {course.default_fee_paise
                          ? formatCurrency(course.default_fee_paise)
                          : "Contact Desk"}
                      </span>
                    </div>
                  </CardContent>
                  <CardFooter className="pt-0 border-t-0">
                    <Link href={`/admissions?course=${encodeURIComponent(course.name)}`} className="w-full">
                      <Button variant="primary" size="sm" className="w-full gap-1.5">
                        Enquire for this Course
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
