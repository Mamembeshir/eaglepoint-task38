import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/lib/api'

export interface RiskTerm {
  id: string
  term: string
  category: string
  severity: string
  description: string | null
  replacement_suggestion: string | null
  is_active: boolean
  is_regex: boolean
  match_count: number
  created_at: string
}

interface CohortMember {
  id: string
  email: string
  display_name: string | null
}

interface CohortWithMembers {
  id: string
  name: string
  slug: string
  description: string | null
  is_admin_defined: boolean
  is_active: boolean
  created_at: string
  members: CohortMember[]
}

export interface AuditLogItem {
  id: string
  action: string
  entity_type: string
  entity_id: string | null
  user_id: string | null
  user_email: string | null
  ip_address: string | null
  description: string | null
  request_url: string | null
  request_method: string | null
  before_data: unknown
  after_data: unknown
  changes: unknown
  created_at: string
}

interface WebhookConfig {
  id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  retry_count: number
  retry_delay_seconds: number
  timeout_seconds: number
  created_at: string
}

export interface WebhookDelivery {
  id: string
  webhook_config_id: string
  event_name: string
  status: string
  attempts: number
  response_status: number | null
  last_error: string | null
  queued_at: string
  delivered_at: string | null
  created_at: string
}

export interface WorkflowTemplateStage {
  id: string
  stage_name: string
  stage_order: number
  description: string | null
  is_required: boolean
  is_parallel: boolean
  is_active: boolean
  created_by_id: string | null
  created_at: string
}

interface WorkflowInitResponse {
  content_id: string
  stages_created: number
  status: string
}

interface AuditFilters {
  user_email?: string
  action?: string
  start_at?: string
  end_at?: string
}

interface PublishingHistoryItem {
  id: string
  action: string
  actor_id: string | null
  reason: string | null
  before_state: Record<string, unknown> | null
  after_state: Record<string, unknown> | null
  created_at: string
}

interface CanaryVisibilityResult {
  content_id: string
  user_id: string
  visible: boolean
  reason: string
}

export const useAdminWorkspaceStore = defineStore('admin-workspace', () => {
  const loading = ref(false)
  const riskTerms = ref<RiskTerm[]>([])
  const cohorts = ref<CohortWithMembers[]>([])
  const auditLogs = ref<AuditLogItem[]>([])
  const webhookConfigs = ref<WebhookConfig[]>([])
  const webhookDeliveries = ref<WebhookDelivery[]>([])
  const workflowTemplateStages = ref<WorkflowTemplateStage[]>([])
  const publishingHistory = ref<PublishingHistoryItem[]>([])
  const canaryVisibilityResult = ref<CanaryVisibilityResult | null>(null)

  async function loadRiskTerms() {
    const { data } = await api.get<RiskTerm[]>('/api/v1/admin/risk-dictionary')
    riskTerms.value = data
  }

  async function loadCohorts() {
    const { data } = await api.get<CohortWithMembers[]>('/api/v1/admin/cohorts')
    cohorts.value = data
  }

  async function loadWebhookConfigs() {
    const { data } = await api.get<WebhookConfig[]>('/api/v1/webhooks/configs')
    webhookConfigs.value = data
  }

  async function loadWebhookDeliveries(status?: string) {
    const { data } = await api.get<WebhookDelivery[]>('/api/v1/webhooks/deliveries', {
      params: {
        status: status || undefined,
        limit: 200
      }
    })
    webhookDeliveries.value = data
  }

  async function loadAuditLogs(filters: AuditFilters = {}) {
    const { data } = await api.get<{ items: AuditLogItem[] }>('/api/v1/audit-logs', {
      params: {
        limit: 100,
        user_email: filters.user_email || undefined,
        action: filters.action || undefined,
        start_at: filters.start_at || undefined,
        end_at: filters.end_at || undefined
      }
    })
    auditLogs.value = data.items
  }

  async function loadWorkflowTemplateStages() {
    const { data } = await api.get<WorkflowTemplateStage[]>('/api/v1/review-workflow/templates/stages')
    workflowTemplateStages.value = data
  }

  async function createCohort(payload: {
    name: string
    slug: string
    description?: string
    is_admin_defined?: boolean
  }) {
    await api.post('/api/v1/cohorts', payload)
    await loadCohorts()
  }

  async function loadAll() {
    loading.value = true
    try {
      await Promise.all([
        loadRiskTerms(),
        loadCohorts(),
        loadAuditLogs(),
        loadWebhookConfigs(),
        loadWebhookDeliveries(),
        loadWorkflowTemplateStages()
      ])
    } finally {
      loading.value = false
    }
  }

  async function createRiskTerm(payload: {
    term: string
    category: string
    severity: string
    description?: string
    replacement_suggestion?: string
    is_regex?: boolean
  }) {
    await api.post('/api/v1/admin/risk-dictionary', payload)
    await loadRiskTerms()
  }

  async function updateRiskTerm(id: string, payload: {
    term?: string
    category?: string
    severity?: string
    description?: string
    replacement_suggestion?: string
    is_active?: boolean
    is_regex?: boolean
  }) {
    await api.patch(`/api/v1/admin/risk-dictionary/${id}`, payload)
    await loadRiskTerms()
  }

  async function deleteRiskTerm(id: string) {
    await api.delete(`/api/v1/admin/risk-dictionary/${id}`)
    await loadRiskTerms()
  }

  async function createWebhook(payload: {
    name: string
    url: string
    secret?: string
    events: string[]
    retry_count?: number
    retry_delay_seconds?: number
    timeout_seconds?: number
  }) {
    await api.post('/api/v1/webhooks/configs', payload)
    await Promise.all([loadWebhookConfigs(), loadWebhookDeliveries()])
  }

  async function retryWebhookDelivery(deliveryId: string) {
    await api.post(`/api/v1/webhooks/deliveries/${deliveryId}/retry`)
    await loadWebhookDeliveries()
  }

  async function schedulePublishing(contentId: string, payload: {
    scheduled_publish_at: string
    scheduled_unpublish_at?: string
    canary?: {
      enabled: boolean
      percentage?: number
      duration_minutes?: number
      segmentation_type?: 'random' | 'cohort'
      target_cohort_ids?: string[]
    }
  }) {
    await api.post(`/api/v1/publishing/content/${contentId}/schedule`, payload)
    await loadAuditLogs()
  }

  async function takedownContent(contentId: string, reason: string) {
    await api.post(`/api/v1/publishing/content/${contentId}/takedown`, { reason })
    await loadAuditLogs()
  }

  async function assignUserToCohort(cohortId: string, userId: string) {
    await api.post(`/api/v1/cohorts/${cohortId}/users/${userId}`)
    await loadCohorts()
  }

  async function removeUserFromCohort(cohortId: string, userId: string) {
    await api.delete(`/api/v1/cohorts/${cohortId}/users/${userId}`)
    await loadCohorts()
  }

  async function createWorkflowTemplateStage(payload: {
    stage_name: string
    stage_order: number
    description?: string
    is_required: boolean
    is_parallel: boolean
  }) {
    await api.post('/api/v1/review-workflow/templates/stages', payload)
    await loadWorkflowTemplateStages()
  }

  async function initializeContentWorkflow(contentId: string) {
    const { data } = await api.post<WorkflowInitResponse>(`/api/v1/review-workflow/contents/${contentId}/initialize`)
    return data
  }

  async function loadPublishingHistory(contentId: string) {
    const { data } = await api.get<PublishingHistoryItem[]>(`/api/v1/publishing/content/${contentId}/history`)
    publishingHistory.value = data
  }

  async function checkCanaryVisibility(contentId: string, userId: string) {
    const { data } = await api.get<CanaryVisibilityResult>(`/api/v1/publishing/content/${contentId}/visibility/${userId}`)
    canaryVisibilityResult.value = data
    return data
  }

  return {
    loading,
    riskTerms,
    cohorts,
    auditLogs,
    webhookConfigs,
    webhookDeliveries,
    workflowTemplateStages,
    publishingHistory,
    canaryVisibilityResult,
    loadAll,
    loadRiskTerms,
    loadAuditLogs,
    loadWebhookDeliveries,
    loadWorkflowTemplateStages,
    createRiskTerm,
    createCohort,
    updateRiskTerm,
    deleteRiskTerm,
    createWebhook,
    retryWebhookDelivery,
    schedulePublishing,
    takedownContent,
    assignUserToCohort,
    removeUserFromCohort,
    createWorkflowTemplateStage,
    initializeContentWorkflow,
    loadPublishingHistory,
    checkCanaryVisibility
  }
})
