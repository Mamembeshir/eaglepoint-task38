<script setup lang="ts">
import { Activity, AlertOctagon, CalendarClock, Link2, RotateCcw, Users } from 'lucide-vue-next'
import { onMounted, reactive, ref } from 'vue'

import { UIBadge } from '@/components/ui/badge'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UIInput } from '@/components/ui/input'
import { UITextarea } from '@/components/ui/textarea'
import { useAdminWorkspaceStore } from '@/stores/adminWorkspace'

const store = useAdminWorkspaceStore()

const activeTab = ref<'risk' | 'cohorts' | 'publishing' | 'audit' | 'webhooks'>('risk')
const message = ref('')

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

const auditFilters = reactive({
  user_email: '',
  action: '',
  start_at: '',
  end_at: ''
})
const expandedAuditId = ref<string | null>(null)

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

async function applyAuditFilters() {
  await store.loadAuditLogs({
    user_email: auditFilters.user_email || undefined,
    action: auditFilters.action || undefined,
    start_at: toIsoDateTime(auditFilters.start_at),
    end_at: toIsoDateTime(auditFilters.end_at)
  })
}

onMounted(async () => {
  await store.loadAll()
})
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">System Administrator</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Control Center</h2>
      <p class="mt-1 text-sm text-muted-foreground">Centralized management for policy, cohorts, publishing, audits, and integrations.</p>
    </header>

    <div class="flex flex-wrap items-center gap-2 rounded-xl border border-border/60 bg-card/70 p-2">
      <UIButton :variant="activeTab === 'risk' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'risk'">Risk Dictionary</UIButton>
      <UIButton :variant="activeTab === 'cohorts' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'cohorts'">Cohorts</UIButton>
      <UIButton :variant="activeTab === 'publishing' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'publishing'">Publishing</UIButton>
      <UIButton :variant="activeTab === 'audit' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'audit'">Audit Logs</UIButton>
      <UIButton :variant="activeTab === 'webhooks' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'webhooks'">Webhooks</UIButton>
    </div>

    <p v-if="message" class="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-sm text-muted-foreground">{{ message }}</p>

    <div v-if="activeTab === 'risk'" class="grid gap-5 xl:grid-cols-[1fr,1.25fr]">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><AlertOctagon class="h-5 w-5" /> Create Dictionary Entry</UICardTitle>
          <UICardDescription>Create keywords and regex rules with severity controls.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <UIInput v-model="riskForm.term" placeholder="Keyword or regex pattern" />
          <div class="grid gap-3 sm:grid-cols-2">
            <UIInput v-model="riskForm.category" placeholder="Category" />
            <UIInput v-model="riskForm.severity" placeholder="Severity (low|medium|high)" />
          </div>
          <UITextarea v-model="riskForm.description" placeholder="Description" :rows="2" />
          <UIInput v-model="riskForm.replacement_suggestion" placeholder="Replacement suggestion" />
          <label class="flex items-center gap-2 text-sm">
            <input v-model="riskForm.is_regex" type="checkbox" />
            Treat term as regex
          </label>
          <UIButton class="w-full" @click="createRisk">Create Entry</UIButton>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle>Dictionary Management</UICardTitle>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <div v-for="term in store.riskTerms" :key="term.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
            <template v-if="editingRiskId !== term.id">
              <div class="mb-2 flex items-center justify-between gap-2">
                <div>
                  <p class="font-medium">{{ term.term }}</p>
                  <p class="text-xs text-muted-foreground">Matches: {{ term.match_count }} • {{ term.is_regex ? 'Regex' : 'Keyword' }}</p>
                </div>
                <div class="flex items-center gap-2">
                  <UIBadge variant="outline">{{ term.category }}</UIBadge>
                  <UIBadge variant="secondary">{{ term.severity }}</UIBadge>
                  <UIBadge :variant="term.is_active ? 'success' : 'outline'">{{ term.is_active ? 'Active' : 'Inactive' }}</UIBadge>
                </div>
              </div>
              <div class="flex gap-2">
                <UIButton size="sm" variant="outline" @click="startRiskEdit(term.id)">Edit</UIButton>
                <UIButton size="sm" variant="outline" @click="deleteRisk(term.id)">Delete</UIButton>
              </div>
            </template>

            <template v-else>
              <div class="grid gap-2 sm:grid-cols-2">
                <UIInput v-model="riskEditForm.term" placeholder="Keyword or regex pattern" class="sm:col-span-2" />
                <UIInput v-model="riskEditForm.category" placeholder="Category" />
                <UIInput v-model="riskEditForm.severity" placeholder="Severity" />
              </div>
              <UITextarea v-model="riskEditForm.description" placeholder="Description" :rows="2" />
              <UIInput v-model="riskEditForm.replacement_suggestion" placeholder="Replacement suggestion" />
              <div class="grid gap-2 sm:grid-cols-2">
                <label class="flex items-center gap-2 text-sm">
                  <input v-model="riskEditForm.is_regex" type="checkbox" />
                  Regex rule
                </label>
                <label class="flex items-center gap-2 text-sm">
                  <input v-model="riskEditForm.is_active" type="checkbox" />
                  Active
                </label>
              </div>
              <div class="flex gap-2">
                <UIButton size="sm" @click="saveRiskEdit(term.id)">Save</UIButton>
                <UIButton size="sm" variant="outline" @click="cancelRiskEdit">Cancel</UIButton>
              </div>
            </template>
          </div>
        </UICardContent>
      </UICard>
    </div>

    <UICard v-else-if="activeTab === 'cohorts'" class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle class="flex items-center gap-2 text-lg"><Users class="h-5 w-5" /> Cohort Management</UICardTitle>
      </UICardHeader>
      <UICardContent class="space-y-3">
        <div v-for="cohort in store.cohorts" :key="cohort.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
          <div class="mb-1 flex items-center justify-between">
            <p class="font-medium">{{ cohort.name }}</p>
            <UIBadge :variant="cohort.is_admin_defined ? 'default' : 'outline'">{{ cohort.is_admin_defined ? 'Admin' : 'User' }}</UIBadge>
          </div>
          <p class="text-xs text-muted-foreground">{{ cohort.members.length }} members</p>
        </div>
      </UICardContent>
    </UICard>

    <div v-else-if="activeTab === 'publishing'" class="grid gap-5 xl:grid-cols-[1fr,1.2fr]">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><CalendarClock class="h-5 w-5" /> Publishing Controls</UICardTitle>
          <UICardDescription>Schedule datetime, canary percentage, and canary duration.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <UIInput v-model="publishForm.contentId" placeholder="Content ID" />
          <div class="space-y-1">
            <label class="text-xs text-muted-foreground">Publish At</label>
            <UIInput v-model="publishForm.publishAt" type="datetime-local" />
          </div>
          <div class="space-y-1">
            <label class="text-xs text-muted-foreground">Unpublish At (optional)</label>
            <UIInput v-model="publishForm.unpublishAt" type="datetime-local" />
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="space-y-1">
              <label class="text-xs text-muted-foreground">Canary Percentage</label>
              <UIInput v-model="publishForm.percentage" type="number" placeholder="1-100" />
            </div>
            <div class="space-y-1">
              <label class="text-xs text-muted-foreground">Duration (minutes)</label>
              <UIInput v-model="publishForm.durationMinutes" type="number" placeholder="30" />
            </div>
          </div>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="publishForm.canaryEnabled" type="checkbox" />
            Enable canary rollout
          </label>
          <UIButton class="w-full" @click="schedulePublishing">Save Schedule</UIButton>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><Activity class="h-5 w-5" /> Recent Audit Activity</UICardTitle>
        </UICardHeader>
        <UICardContent class="space-y-2">
          <div v-for="log in store.auditLogs.slice(0, 10)" :key="log.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-medium">{{ log.entity_type }}</p>
              <UIBadge variant="outline">{{ log.action }}</UIBadge>
            </div>
            <p class="text-xs text-muted-foreground">{{ log.user_email || 'system' }} • {{ new Date(log.created_at).toLocaleString() }}</p>
          </div>
        </UICardContent>
      </UICard>
    </div>

    <UICard v-else-if="activeTab === 'audit'" class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle>Audit Log Viewer</UICardTitle>
        <UICardDescription>Filter by user, action, and date range, then inspect before/after data.</UICardDescription>
      </UICardHeader>
      <UICardContent class="space-y-4">
        <div class="grid gap-2 md:grid-cols-5">
          <UIInput v-model="auditFilters.user_email" placeholder="User email contains..." class="md:col-span-2" />
          <UIInput v-model="auditFilters.action" placeholder="Action (create/update/etc.)" />
          <UIInput v-model="auditFilters.start_at" type="datetime-local" />
          <UIInput v-model="auditFilters.end_at" type="datetime-local" />
        </div>
        <div class="flex gap-2">
          <UIButton size="sm" @click="applyAuditFilters">Apply Filters</UIButton>
          <UIButton
            size="sm"
            variant="outline"
            @click="auditFilters.user_email = ''; auditFilters.action = ''; auditFilters.start_at = ''; auditFilters.end_at = ''; applyAuditFilters()"
          >
            Reset
          </UIButton>
        </div>

        <div class="space-y-2">
          <div v-for="log in store.auditLogs" :key="log.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
            <div class="flex items-center justify-between gap-2">
              <div>
                <p class="text-sm font-medium">{{ log.entity_type }}</p>
                <p class="text-xs text-muted-foreground">{{ log.user_email || 'system' }} • {{ new Date(log.created_at).toLocaleString() }}</p>
              </div>
              <div class="flex items-center gap-2">
                <UIBadge variant="secondary">{{ log.action }}</UIBadge>
                <UIButton size="sm" variant="outline" @click="expandedAuditId = expandedAuditId === log.id ? null : log.id">
                  {{ expandedAuditId === log.id ? 'Hide Diff' : 'View Diff' }}
                </UIButton>
              </div>
            </div>

            <p class="mt-2 text-xs text-muted-foreground">{{ log.description || 'No description' }}</p>

            <div v-if="expandedAuditId === log.id" class="mt-3 grid gap-3 lg:grid-cols-2">
              <div class="rounded-md border border-border/60 bg-card/50 p-2">
                <p class="mb-2 text-xs uppercase text-muted-foreground">Before</p>
                <pre class="max-h-56 overflow-auto text-xs">{{ prettyJson(log.before_data) }}</pre>
              </div>
              <div class="rounded-md border border-border/60 bg-card/50 p-2">
                <p class="mb-2 text-xs uppercase text-muted-foreground">After</p>
                <pre class="max-h-56 overflow-auto text-xs">{{ prettyJson(log.after_data) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </UICardContent>
    </UICard>

    <div v-else class="grid gap-5 xl:grid-cols-[1fr,1.2fr]">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><Link2 class="h-5 w-5" /> Webhook Config</UICardTitle>
          <UICardDescription>Create intranet-only webhooks with retry policy controls.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <UIInput v-model="webhookForm.name" placeholder="Name" />
          <UIInput v-model="webhookForm.url" placeholder="http://internal-host/webhook" />
          <UIInput v-model="webhookForm.secret" placeholder="HMAC secret" />
          <UITextarea v-model="webhookForm.events" :rows="2" placeholder="comma-separated events" />
          <div class="grid gap-2 sm:grid-cols-3">
            <UIInput v-model="webhookForm.retry_count" type="number" placeholder="Retries" />
            <UIInput v-model="webhookForm.retry_delay_seconds" type="number" placeholder="Retry delay s" />
            <UIInput v-model="webhookForm.timeout_seconds" type="number" placeholder="Timeout s" />
          </div>
          <UIButton class="w-full" @click="createWebhook">Create Webhook</UIButton>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <div class="flex items-center justify-between gap-2">
            <div>
              <UICardTitle>Delivery Logs</UICardTitle>
              <UICardDescription>Review deliveries and retry failed attempts.</UICardDescription>
            </div>
            <div class="flex items-center gap-2">
              <select v-model="webhookStatusFilter" class="h-9 rounded-md border border-input bg-background px-2 text-sm">
                <option value="">All</option>
                <option value="queued">Queued</option>
                <option value="retrying">Retrying</option>
                <option value="success">Success</option>
                <option value="dead_letter">Dead Letter</option>
              </select>
              <UIButton size="sm" variant="outline" @click="refreshWebhookLogs">Refresh</UIButton>
            </div>
          </div>
        </UICardHeader>
        <UICardContent class="space-y-2">
          <div v-for="delivery in store.webhookDeliveries" :key="delivery.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-sm font-medium">{{ delivery.event_name }}</p>
                <p class="text-xs text-muted-foreground">{{ new Date(delivery.created_at).toLocaleString() }}</p>
              </div>
              <div class="flex items-center gap-2">
                <UIBadge :variant="delivery.status === 'success' ? 'success' : 'outline'">{{ delivery.status }}</UIBadge>
                <UIButton
                  v-if="delivery.status !== 'success'"
                  size="sm"
                  variant="outline"
                  class="gap-1"
                  @click="retryDelivery(delivery.id)"
                >
                  <RotateCcw class="h-3.5 w-3.5" />
                  Retry
                </UIButton>
              </div>
            </div>
            <p class="mt-1 text-xs text-muted-foreground">Attempts: {{ delivery.attempts }} • HTTP: {{ delivery.response_status ?? 'n/a' }}</p>
            <p v-if="delivery.last_error" class="mt-1 text-xs text-destructive">{{ delivery.last_error }}</p>
          </div>

          <div v-if="!store.webhookDeliveries.length" class="rounded-xl border border-dashed border-border/70 p-8 text-center text-sm text-muted-foreground">
            No webhook deliveries found for the selected filter.
          </div>
        </UICardContent>
      </UICard>
    </div>
  </section>
</template>
