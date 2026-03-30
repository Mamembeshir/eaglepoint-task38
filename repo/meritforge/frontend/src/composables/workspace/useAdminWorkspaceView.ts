import { computed, onMounted, reactive, ref, watch } from 'vue'

import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'
import { confirmStepUp } from '@/lib/stepUp'
import { useAuthStore } from '@/stores/auth'
import { useAdminWorkspaceStore } from '@/stores/adminWorkspace'

export function useAdminWorkspaceView() {
  const store = useAdminWorkspaceStore()
  const auth = useAuthStore()
  const isAdmin = computed(() => auth.role === 'system_administrator')

  const activeTab = ref<'risk' | 'cohorts' | 'publishing' | 'audit' | 'webhooks'>('risk')
  const message = ref('')
  const riskPage = ref(1)
  const cohortPage = ref(1)
  const auditPage = ref(1)
  const webhookPage = ref(1)
  const RISK_PAGE_SIZE = 8
  const COHORT_PAGE_SIZE = 8
  const AUDIT_PAGE_SIZE = 12
  const WEBHOOK_PAGE_SIZE = 12

  const riskForm = reactive({
    term: '',
    category: '',
    severity: 'medium',
    description: '',
    replacement_suggestion: '',
    is_regex: false
  })

  const editingRiskId = ref<string | null>(null)
  const riskEditForm = reactive({
    term: '',
    category: '',
    severity: '',
    description: '',
    replacement_suggestion: '',
    is_regex: false,
    is_active: true
  })

  const webhookForm = reactive({
    name: '',
    url: '',
    secret: '',
    events: 'content.published,application.submitted',
    retry_count: '3',
    retry_delay_seconds: '60',
    timeout_seconds: '30'
  })

  const webhookStatusFilter = ref('')

  const publishForm = reactive({
    contentId: '',
    publishAt: '',
    unpublishAt: '',
    canaryEnabled: true,
    percentage: '5',
    durationMinutes: '120'
  })

  const workflowStageForm = reactive({
    stage_name: 'Initial review',
    stage_order: '1',
    description: 'Default required review stage',
    is_required: true,
    is_parallel: false
  })

  const workflowInitForm = reactive({
    contentId: ''
  })
  const workflowMessage = ref('')
  const publishingLookupForm = reactive({
    historyContentId: '',
    visibilityContentId: '',
    visibilityUserId: ''
  })

  const auditFilters = reactive({
    user_email: '',
    action: '',
    start_at: '',
    end_at: ''
  })
  const expandedAuditId = ref<string | null>(null)

  const membershipForm = reactive({
    cohortId: '',
    userId: ''
  })

  const cohortForm = reactive({
    name: '',
    slug: '',
    description: ''
  })

  const takedownForm = reactive({
    contentId: '',
    reason: ''
  })

  const legalHoldForm = reactive({
    userId: '',
    reason: ''
  })
  const legalHoldMessage = ref('')

  const riskPageCount = computed(() => Math.max(1, Math.ceil(store.riskTerms.length / RISK_PAGE_SIZE)))
  const pagedRiskTerms = computed(() => {
    const start = (riskPage.value - 1) * RISK_PAGE_SIZE
    return store.riskTerms.slice(start, start + RISK_PAGE_SIZE)
  })
  const cohortPageCount = computed(() => Math.max(1, Math.ceil(store.cohorts.length / COHORT_PAGE_SIZE)))
  const pagedCohorts = computed(() => {
    const start = (cohortPage.value - 1) * COHORT_PAGE_SIZE
    return store.cohorts.slice(start, start + COHORT_PAGE_SIZE)
  })
  const auditPageCount = computed(() => Math.max(1, Math.ceil(store.auditLogs.length / AUDIT_PAGE_SIZE)))
  const pagedAuditLogs = computed(() => {
    const start = (auditPage.value - 1) * AUDIT_PAGE_SIZE
    return store.auditLogs.slice(start, start + AUDIT_PAGE_SIZE)
  })
  const webhookPageCount = computed(() => Math.max(1, Math.ceil(store.webhookDeliveries.length / WEBHOOK_PAGE_SIZE)))
  const pagedWebhookDeliveries = computed(() => {
    const start = (webhookPage.value - 1) * WEBHOOK_PAGE_SIZE
    return store.webhookDeliveries.slice(start, start + WEBHOOK_PAGE_SIZE)
  })

  const stepUpOpen = ref(false)
  const stepUpLoading = ref(false)
  const stepUpError = ref('')
  let stepUpAction: (() => Promise<void>) | null = null

  function openStepUp(action: () => Promise<void>) {
    stepUpError.value = ''
    stepUpAction = action
    stepUpOpen.value = true
  }

  function cancelStepUp() {
    stepUpOpen.value = false
    stepUpError.value = ''
    stepUpAction = null
  }

  async function onStepUpConfirm(password: string) {
    stepUpLoading.value = true
    stepUpError.value = ''
    try {
      await confirmStepUp(password)
      if (stepUpAction) {
        await stepUpAction()
      }
      cancelStepUp()
    } catch (error) {
      stepUpError.value = getApiErrorMessage(error)
      logDevError(error)
    } finally {
      stepUpLoading.value = false
    }
  }

  function toIsoDateTime(localDateTime: string) {
    if (!localDateTime) return undefined
    const date = new Date(localDateTime)
    return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
  }

  function prettyJson(value: unknown) {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'string') return value
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }

  async function createRisk() {
    await store.createRiskTerm({
      term: riskForm.term,
      category: riskForm.category,
      severity: riskForm.severity,
      description: riskForm.description || undefined,
      replacement_suggestion: riskForm.replacement_suggestion || undefined,
      is_regex: riskForm.is_regex
    })
    riskForm.term = ''
    riskForm.category = ''
    riskForm.description = ''
    riskForm.replacement_suggestion = ''
    riskForm.severity = 'medium'
    riskForm.is_regex = false
    message.value = 'Risk term created.'
    riskPage.value = 1
  }

  function startRiskEdit(termId: string) {
    const term = store.riskTerms.find((item) => item.id === termId)
    if (!term) return
    editingRiskId.value = termId
    riskEditForm.category = term.category
    riskEditForm.term = term.term
    riskEditForm.severity = term.severity
    riskEditForm.description = term.description || ''
    riskEditForm.replacement_suggestion = term.replacement_suggestion || ''
    riskEditForm.is_regex = term.is_regex
    riskEditForm.is_active = term.is_active
  }

  function cancelRiskEdit() {
    editingRiskId.value = null
  }

  async function saveRiskEdit(termId: string) {
    await store.updateRiskTerm(termId, {
      term: riskEditForm.term,
      category: riskEditForm.category,
      severity: riskEditForm.severity,
      description: riskEditForm.description || undefined,
      replacement_suggestion: riskEditForm.replacement_suggestion || undefined,
      is_regex: riskEditForm.is_regex,
      is_active: riskEditForm.is_active
    })
    editingRiskId.value = null
    message.value = 'Risk term updated.'
  }

  async function deleteRisk(termId: string) {
    const accepted = window.confirm('Delete this risk term? This cannot be undone.')
    if (!accepted) return
    await store.deleteRiskTerm(termId)
    message.value = 'Risk term deleted.'
    if (riskPage.value > riskPageCount.value) {
      riskPage.value = riskPageCount.value
    }
  }

  async function createWebhook() {
    await store.createWebhook({
      name: webhookForm.name,
      url: webhookForm.url,
      secret: webhookForm.secret || undefined,
      events: webhookForm.events.split(',').map((x) => x.trim()).filter(Boolean),
      retry_count: Number(webhookForm.retry_count),
      retry_delay_seconds: Number(webhookForm.retry_delay_seconds),
      timeout_seconds: Number(webhookForm.timeout_seconds)
    })
    webhookForm.name = ''
    webhookForm.url = ''
    webhookForm.secret = ''
    message.value = 'Webhook created.'
  }

  async function refreshWebhookLogs() {
    await store.loadWebhookDeliveries(webhookStatusFilter.value || undefined)
  }

  async function retryDelivery(deliveryId: string) {
    await store.retryWebhookDelivery(deliveryId)
    message.value = 'Retry queued for selected delivery.'
  }

  async function schedulePublishing() {
    const publishAtIso = toIsoDateTime(publishForm.publishAt)
    if (!publishAtIso) {
      message.value = 'Please choose a valid publish datetime.'
      return
    }
    await store.schedulePublishing(publishForm.contentId, {
      scheduled_publish_at: publishAtIso,
      scheduled_unpublish_at: toIsoDateTime(publishForm.unpublishAt),
      canary: {
        enabled: publishForm.canaryEnabled,
        percentage: Number(publishForm.percentage),
        duration_minutes: Number(publishForm.durationMinutes),
        segmentation_type: 'random'
      }
    })
    message.value = 'Publishing schedule saved.'
  }

  async function createWorkflowStage() {
    workflowMessage.value = ''
    try {
      await store.createWorkflowTemplateStage({
        stage_name: workflowStageForm.stage_name.trim(),
        stage_order: Number(workflowStageForm.stage_order),
        description: workflowStageForm.description.trim() || undefined,
        is_required: workflowStageForm.is_required,
        is_parallel: workflowStageForm.is_parallel
      })
      workflowMessage.value = 'Template stage created.'
    } catch (error) {
      workflowMessage.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function initializeWorkflowForContent() {
    workflowMessage.value = ''
    const contentId = workflowInitForm.contentId.trim()
    if (!contentId) {
      workflowMessage.value = 'Provide a content ID to initialize workflow.'
      return
    }
    try {
      const result = await store.initializeContentWorkflow(contentId)
      workflowMessage.value = `Workflow initialized: ${result.stages_created} stage(s) created.`
    } catch (error) {
      workflowMessage.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function createCohort() {
    if (!cohortForm.name.trim() || !cohortForm.slug.trim()) {
      message.value = 'Provide cohort name and slug.'
      return
    }
    try {
      await store.createCohort({
        name: cohortForm.name.trim(),
        slug: cohortForm.slug.trim(),
        description: cohortForm.description.trim() || undefined,
        is_admin_defined: true
      })
      cohortForm.name = ''
      cohortForm.slug = ''
      cohortForm.description = ''
      message.value = 'Cohort created.'
      cohortPage.value = 1
    } catch (error) {
      message.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function takeDownContent() {
    if (!takedownForm.contentId.trim() || !takedownForm.reason.trim()) {
      message.value = 'Provide both content ID and takedown reason.'
      return
    }
    openStepUp(async () => {
      await store.takedownContent(takedownForm.contentId.trim(), takedownForm.reason.trim())
      message.value = 'Content takedown completed.'
      takedownForm.reason = ''
    })
  }

  async function assignMembership() {
    if (!membershipForm.cohortId.trim() || !membershipForm.userId.trim()) {
      message.value = 'Provide cohort ID and user ID.'
      return
    }
    openStepUp(async () => {
      await store.assignUserToCohort(membershipForm.cohortId.trim(), membershipForm.userId.trim())
      message.value = 'User assigned to cohort.'
    })
  }

  async function removeMembership() {
    if (!membershipForm.cohortId.trim() || !membershipForm.userId.trim()) {
      message.value = 'Provide cohort ID and user ID.'
      return
    }
    openStepUp(async () => {
      await store.removeUserFromCohort(membershipForm.cohortId.trim(), membershipForm.userId.trim())
      message.value = 'User removed from cohort.'
    })
  }

  async function loadPublishingHistory() {
    if (!publishingLookupForm.historyContentId.trim()) {
      message.value = 'Provide a content ID to load publishing history.'
      return
    }
    try {
      await store.loadPublishingHistory(publishingLookupForm.historyContentId.trim())
    } catch (error) {
      message.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function checkVisibility() {
    if (!publishingLookupForm.visibilityContentId.trim() || !publishingLookupForm.visibilityUserId.trim()) {
      message.value = 'Provide both content ID and user ID for visibility lookup.'
      return
    }
    try {
      await store.checkCanaryVisibility(
        publishingLookupForm.visibilityContentId.trim(),
        publishingLookupForm.visibilityUserId.trim()
      )
    } catch (error) {
      message.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function loadLegalHold() {
    legalHoldMessage.value = ''
    if (!legalHoldForm.userId.trim()) {
      legalHoldMessage.value = 'Provide a user ID to check legal hold status.'
      return
    }
    try {
      await store.getLegalHoldStatus(legalHoldForm.userId.trim())
    } catch (error) {
      legalHoldMessage.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function setLegalHold(legalHold: boolean) {
    legalHoldMessage.value = ''
    if (!legalHoldForm.userId.trim()) {
      legalHoldMessage.value = 'Provide a user ID before updating legal hold.'
      return
    }
    try {
      const result = await store.updateLegalHold(legalHoldForm.userId.trim(), {
        legal_hold: legalHold,
        reason: legalHoldForm.reason.trim() || undefined
      })
      legalHoldMessage.value = `Legal hold ${result.legal_hold ? 'enabled' : 'disabled'} for user ${result.user_id}.`
    } catch (error) {
      legalHoldMessage.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function applyAuditFilters() {
    await store.loadAuditLogs({
      user_email: auditFilters.user_email || undefined,
      action: auditFilters.action || undefined,
      start_at: toIsoDateTime(auditFilters.start_at),
      end_at: toIsoDateTime(auditFilters.end_at)
    })
    auditPage.value = 1
  }

  watch(
    () => store.riskTerms.length,
    () => {
      if (riskPage.value > riskPageCount.value) {
        riskPage.value = riskPageCount.value
      }
    }
  )

  watch(
    () => store.cohorts.length,
    () => {
      if (cohortPage.value > cohortPageCount.value) {
        cohortPage.value = cohortPageCount.value
      }
    }
  )

  watch(
    () => store.auditLogs.length,
    () => {
      if (auditPage.value > auditPageCount.value) {
        auditPage.value = auditPageCount.value
      }
    }
  )

  watch(
    () => store.webhookDeliveries.length,
    () => {
      if (webhookPage.value > webhookPageCount.value) {
        webhookPage.value = webhookPageCount.value
      }
    }
  )

  onMounted(async () => {
    try {
      await store.loadAll()
    } catch (error) {
      message.value = getApiErrorMessage(error)
      logDevError(error)
    }
  })

  return {
    store,
    isAdmin,
    activeTab,
    message,
    riskPage,
    riskPageCount,
    pagedRiskTerms,
    cohortPage,
    cohortPageCount,
    pagedCohorts,
    auditPage,
    auditPageCount,
    pagedAuditLogs,
    webhookPage,
    webhookPageCount,
    pagedWebhookDeliveries,
    riskForm,
    editingRiskId,
    riskEditForm,
    webhookForm,
    webhookStatusFilter,
    publishForm,
    workflowStageForm,
    workflowInitForm,
    workflowMessage,
    publishingLookupForm,
    auditFilters,
    expandedAuditId,
    membershipForm,
    cohortForm,
    takedownForm,
    legalHoldForm,
    legalHoldMessage,
    stepUpOpen,
    stepUpLoading,
    stepUpError,
    cancelStepUp,
    onStepUpConfirm,
    prettyJson,
    createRisk,
    startRiskEdit,
    cancelRiskEdit,
    saveRiskEdit,
    deleteRisk,
    createWebhook,
    refreshWebhookLogs,
    retryDelivery,
    schedulePublishing,
    createWorkflowStage,
    initializeWorkflowForContent,
    createCohort,
    takeDownContent,
    assignMembership,
    removeMembership,
    loadPublishingHistory,
    checkVisibility,
    loadLegalHold,
    setLegalHold,
    applyAuditFilters
  }
}
