import type {
  IdCard,
  IdCardTemplate,
  TemplateCreate,
  TemplateUpdate,
  UUID,
} from "@/types/api";
import { api, backendUrl } from "./client";

export const idCardsApi = {
  listTemplates: () => api.get<IdCardTemplate[]>("/id-cards/templates"),
  createTemplate: (payload: TemplateCreate) =>
    api.post<IdCardTemplate>("/id-cards/templates", payload),
  updateTemplate: (id: UUID, payload: TemplateUpdate) =>
    api.patch<IdCardTemplate>(`/id-cards/templates/${id}`, payload),
  previewTemplateUrl: (id: UUID) => backendUrl(`/id-cards/templates/${id}/preview`),
  generate: (studentId: UUID, templateId?: UUID) =>
    api.post<IdCard>(`/id-cards/students/${studentId}/generate`, {
      template_id: templateId ?? null,
    }),
  downloadUrl: (studentId: UUID) => backendUrl(`/id-cards/students/${studentId}/download`),
  history: (studentId: UUID) => api.get<IdCard[]>(`/id-cards/students/${studentId}/history`),
};
