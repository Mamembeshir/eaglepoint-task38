import { api } from '@/lib/api'
import type {
  AuditFilters,
  AuditLogItem,
  CanaryVisibilityResult,
  CohortWithMembers,
  LegalHoldStatus,
  PublishingHistoryItem,
  RiskTerm,
  WebhookConfig,
  WebhookDelivery,
  WorkflowInitResponse,
  WorkflowTemplateStage
} from '@/stores/workspace/adminWorkspace.types'

export const adminWorkspaceClient = {
  loadRiskTerms: async () => (await api.get<RiskTerm[]>('/api/v1/admin/risk-dictionary')).data,
  loadCohorts: async () => (await api.get<CohortWithMembers[]>('/api/v1/admin/cohorts')).data,
  loadWebhookConfigs: async () => (await api.get<WebhookConfig[]>('/api/v1/webhooks/configs')).data,
  loadWebhookDeliveries: async (status?: string) => (
    await api.get<WebhookDelivery[]>('/api/v1/webhooks/deliveries', {
      params: { status: status || undefined, limit: 200 }
    })
  ).data,
  loadAuditLogs: async (filters: AuditFilters = {}) => (
    await api.get<{ items: AuditLogItem[] }>('/api/v1/audit-logs', {
      params: {
        limit: 100,
        user_email: filters.user_email || undefined,
        action: filters.action || undefined,
        start_at: filters.start_at || undefined,
        end_at: filters.end_at || undefined
      }
    })
  ).data.items,
  loadWorkflowTemplateStages: async () => (await api.get<WorkflowTemplateStage[]>('/api/v1/review-workflow/templates/stages')).data,
  createCohort: async (payload: {
    name: string
    slug: string
    description?: string
    is_admin_defined?: boolean
  }) => api.post('/api/v1/cohorts', payload),
  createRiskTerm: async (payload: {
    term: string
    category: string
    severity: string
    description?: string
    replacement_suggestion?: string
    is_regex?: boolean
  }) => api.post('/api/v1/admin/risk-dictionary', payload),
  updateRiskTerm: async (id: string, payload: {
    term?: string
    category?: string
    severity?: string
    description?: string
    replacement_suggestion?: string
    is_active?: boolean
    is_regex?: boolean
  }) => api.patch(`/api/v1/admin/risk-dictionary/${id}`, payload),
  deleteRiskTerm: async (id: string) => api.delete(`/api/v1/admin/risk-dictionary/${id}`),
  createWebhook: async (payload: {
    name: string
    url: string
    secret?: string
    events: string[]
    retry_count?: number
    retry_delay_seconds?: number
    timeout_seconds?: number
  }) => api.post('/api/v1/webhooks/configs', payload),
  retryWebhookDelivery: async (deliveryId: string) => api.post(`/api/v1/webhooks/deliveries/${deliveryId}/retry`),
  schedulePublishing: async (contentId: string, payload: {
    scheduled_publish_at: string
    scheduled_unpublish_at?: string
    canary?: {
      enabled: boolean
      percentage?: number
      duration_minutes?: number
      segmentation_type?: 'random' | 'cohort'
      target_cohort_ids?: string[]
    }
  }) => api.post(`/api/v1/publishing/content/${contentId}/schedule`, payload),
  takedownContent: async (contentId: string, reason: string) => api.post(`/api/v1/publishing/content/${contentId}/takedown`, { reason }),
  assignUserToCohort: async (cohortId: string, userId: string) => api.post(`/api/v1/cohorts/${cohortId}/users/${userId}`),
  removeUserFromCohort: async (cohortId: string, userId: string) => api.delete(`/api/v1/cohorts/${cohortId}/users/${userId}`),
  createWorkflowTemplateStage: async (payload: {
    stage_name: string
    stage_order: number
    description?: string
    is_required: boolean
    is_parallel: boolean
  }) => api.post('/api/v1/review-workflow/templates/stages', payload),
  initializeContentWorkflow: async (contentId: string) => (
    await api.post<WorkflowInitResponse>(`/api/v1/review-workflow/contents/${contentId}/initialize`)
  ).data,
  loadPublishingHistory: async (contentId: string) => (
    await api.get<PublishingHistoryItem[]>(`/api/v1/publishing/content/${contentId}/history`)
  ).data,
  checkCanaryVisibility: async (contentId: string, userId: string) => (
    await api.get<CanaryVisibilityResult>(`/api/v1/publishing/content/${contentId}/visibility/${userId}`)
  ).data,
  getLegalHoldStatus: async (userId: string) => (
    await api.get<LegalHoldStatus>(`/api/v1/admin/users/${userId}/legal-hold`)
  ).data,
  updateLegalHold: async (userId: string, payload: { legal_hold: boolean; reason?: string }) => (
    await api.patch<LegalHoldStatus>(`/api/v1/admin/users/${userId}/legal-hold`, payload)
  ).data
}
