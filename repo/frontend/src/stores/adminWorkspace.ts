import { defineStore } from 'pinia'
import { ref } from 'vue'

import { adminWorkspaceClient } from '@/stores/workspace/adminWorkspace.client'
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
  WorkflowTemplateStage
} from '@/stores/workspace/adminWorkspace.types'

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
  const legalHoldStatus = ref<LegalHoldStatus | null>(null)

  async function loadRiskTerms() {
    riskTerms.value = await adminWorkspaceClient.loadRiskTerms()
  }

  async function loadCohorts() {
    cohorts.value = await adminWorkspaceClient.loadCohorts()
  }

  async function loadWebhookConfigs() {
    webhookConfigs.value = await adminWorkspaceClient.loadWebhookConfigs()
  }

  async function loadWebhookDeliveries(status?: string) {
    webhookDeliveries.value = await adminWorkspaceClient.loadWebhookDeliveries(status)
  }

  async function loadAuditLogs(filters: AuditFilters = {}) {
    auditLogs.value = await adminWorkspaceClient.loadAuditLogs(filters)
  }

  async function loadWorkflowTemplateStages() {
    workflowTemplateStages.value = await adminWorkspaceClient.loadWorkflowTemplateStages()
  }

  async function createCohort(payload: {
    name: string
    slug: string
    description?: string
    is_admin_defined?: boolean
  }) {
    await adminWorkspaceClient.createCohort(payload)
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
    await adminWorkspaceClient.createRiskTerm(payload)
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
    await adminWorkspaceClient.updateRiskTerm(id, payload)
    await loadRiskTerms()
  }

  async function deleteRiskTerm(id: string) {
    await adminWorkspaceClient.deleteRiskTerm(id)
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
    await adminWorkspaceClient.createWebhook(payload)
    await Promise.all([loadWebhookConfigs(), loadWebhookDeliveries()])
  }

  async function retryWebhookDelivery(deliveryId: string) {
    await adminWorkspaceClient.retryWebhookDelivery(deliveryId)
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
    await adminWorkspaceClient.schedulePublishing(contentId, payload)
    await loadAuditLogs()
  }

  async function takedownContent(contentId: string, reason: string) {
    await adminWorkspaceClient.takedownContent(contentId, reason)
    await loadAuditLogs()
  }

  async function assignUserToCohort(cohortId: string, userId: string) {
    await adminWorkspaceClient.assignUserToCohort(cohortId, userId)
    await loadCohorts()
  }

  async function removeUserFromCohort(cohortId: string, userId: string) {
    await adminWorkspaceClient.removeUserFromCohort(cohortId, userId)
    await loadCohorts()
  }

  async function createWorkflowTemplateStage(payload: {
    stage_name: string
    stage_order: number
    description?: string
    is_required: boolean
    is_parallel: boolean
  }) {
    await adminWorkspaceClient.createWorkflowTemplateStage(payload)
    await loadWorkflowTemplateStages()
  }

  async function initializeContentWorkflow(contentId: string) {
    return adminWorkspaceClient.initializeContentWorkflow(contentId)
  }

  async function loadPublishingHistory(contentId: string) {
    publishingHistory.value = await adminWorkspaceClient.loadPublishingHistory(contentId)
  }

  async function checkCanaryVisibility(contentId: string, userId: string) {
    const data = await adminWorkspaceClient.checkCanaryVisibility(contentId, userId)
    canaryVisibilityResult.value = data
    return data
  }

  async function getLegalHoldStatus(userId: string) {
    const data = await adminWorkspaceClient.getLegalHoldStatus(userId)
    legalHoldStatus.value = data
    return data
  }

  async function updateLegalHold(userId: string, payload: { legal_hold: boolean; reason?: string }) {
    const data = await adminWorkspaceClient.updateLegalHold(userId, payload)
    legalHoldStatus.value = data
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
    legalHoldStatus,
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
    checkCanaryVisibility,
    getLegalHoldStatus,
    updateLegalHold
  }
})
