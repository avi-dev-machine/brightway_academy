"use client";

import { useQuery } from "@tanstack/react-query";
import { idCardsApi } from "@/lib/api/id-cards";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { IdCard as IdCardIcon, Eye, ExternalLink } from "lucide-react";

export default function AdminIdCardsPage() {
  const { data: templates, isLoading } = useQuery({
    queryKey: ["id-card-templates"],
    queryFn: () => idCardsApi.listTemplates(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          ID Card Templates & Generation
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Backend PDF ID-card layout templates with photo embedding and verified student credentials.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {isLoading ? (
          <div className="col-span-2 space-y-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : !templates || templates.length === 0 ? (
          <div className="col-span-2">
            <EmptyState
              icon={<IdCardIcon className="h-8 w-8" />}
              title="No templates found"
              description="Default ID-card templates are seeded via backend migrations."
            />
          </div>
        ) : (
          templates.map((tpl) => (
            <Card key={tpl.id} className="shadow-2xs">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Badge variant={tpl.is_default ? "success" : "default"} className="text-[10px]">
                    {tpl.is_default ? "Default Template" : "Template"}
                  </Badge>
                  <span className="font-mono text-xs text-slate-400">
                    {tpl.layout?.width_mm}mm × {tpl.layout?.height_mm}mm
                  </span>
                </div>
                <CardTitle className="text-base mt-2">{tpl.name}</CardTitle>
                <CardDescription className="text-xs">
                  {tpl.layout?.elements?.length ?? 0} layout elements (photo frame, name, course code, barcode)
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-2 flex items-center justify-between border-t border-slate-100">
                <span className="text-xs text-slate-500">
                  Status: {tpl.active ? "Active" : "Disabled"}
                </span>
                <a
                  href={idCardsApi.previewTemplateUrl(tpl.id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button variant="outline" size="sm" className="h-7 text-xs gap-1.5">
                    <Eye className="h-3.5 w-3.5" />
                    Preview Sample PDF
                    <ExternalLink className="h-3 w-3 text-slate-400" />
                  </Button>
                </a>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      <Card className="bg-blue-50 border-blue-200 p-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-1">
          How Student ID Generation Works
        </h3>
        <p className="text-xs text-blue-700 leading-relaxed max-w-2xl">
          To generate or regenerate a student&apos;s physical ID Card, open their individual profile from the Students directory and click <strong>Generate ID Card</strong>. If a photo has been uploaded, it is automatically centered and stamped with academy colors.
        </p>
      </Card>
    </div>
  );
}
