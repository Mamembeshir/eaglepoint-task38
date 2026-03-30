<script setup lang="ts">
import { Activity, AlertOctagon, CalendarClock, Link2, RotateCcw, Users } from 'lucide-vue-next'

import { UIBadge } from '@/components/ui/badge'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UIInput } from '@/components/ui/input'
import { UITextarea } from '@/components/ui/textarea'
import StepUpConfirmationModal from '@/components/app/StepUpConfirmationModal.vue'
import { useAdminWorkspaceView } from '@/composables/workspace/useAdminWorkspaceView'

const {
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
} = useAdminWorkspaceView()
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
          <div v-for="term in pagedRiskTerms" :key="term.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
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
          <div v-if="store.riskTerms.length > 8" class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>Showing page {{ riskPage }} of {{ riskPageCount }}</span>
            <div class="flex gap-2">
              <UIButton size="sm" variant="outline" :disabled="riskPage <= 1" @click="riskPage = Math.max(1, riskPage - 1)">Previous page</UIButton>
              <UIButton size="sm" variant="outline" :disabled="riskPage >= riskPageCount" @click="riskPage = Math.min(riskPageCount, riskPage + 1)">Next page</UIButton>
            </div>
          </div>
        </UICardContent>
      </UICard>
    </div>

    <UICard v-else-if="activeTab === 'cohorts'" class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle class="flex items-center gap-2 text-lg"><Users class="h-5 w-5" /> Cohort Management</UICardTitle>
      </UICardHeader>
      <UICardContent class="space-y-3">
        <div class="rounded-lg border border-border/60 bg-background/60 p-3">
          <p class="mb-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">Create Cohort</p>
          <div class="grid gap-2 md:grid-cols-2">
            <UIInput v-model="cohortForm.name" placeholder="Cohort name" />
            <UIInput v-model="cohortForm.slug" placeholder="cohort-slug" />
          </div>
          <UITextarea v-model="cohortForm.description" class="mt-2" :rows="2" placeholder="Description (optional)" />
          <UIButton size="sm" class="mt-2" @click="createCohort">Create Cohort</UIButton>
        </div>

        <div class="rounded-lg border border-border/60 bg-background/60 p-3">
          <p class="mb-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">Sensitive membership update</p>
          <div class="grid gap-2 md:grid-cols-2">
            <select v-model="membershipForm.cohortId" class="h-10 rounded-md border border-input bg-background px-3 text-sm">
              <option value="">Select cohort</option>
              <option v-for="cohort in store.cohorts" :key="cohort.id" :value="cohort.id">{{ cohort.name }}</option>
            </select>
            <UIInput v-model="membershipForm.userId" placeholder="User ID" />
          </div>
          <div class="mt-2 flex gap-2">
            <UIButton size="sm" @click="assignMembership">Assign</UIButton>
            <UIButton size="sm" variant="outline" @click="removeMembership">Remove</UIButton>
          </div>
        </div>

        <div v-for="cohort in pagedCohorts" :key="cohort.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
          <div class="mb-1 flex items-center justify-between">
            <p class="font-medium">{{ cohort.name }}</p>
            <UIBadge :variant="cohort.is_admin_defined ? 'default' : 'outline'">{{ cohort.is_admin_defined ? 'Admin' : 'User' }}</UIBadge>
          </div>
          <p class="text-xs text-muted-foreground">{{ cohort.members.length }} members</p>
        </div>
        <div v-if="store.cohorts.length > 8" class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>Showing page {{ cohortPage }} of {{ cohortPageCount }}</span>
          <div class="flex gap-2">
            <UIButton size="sm" variant="outline" :disabled="cohortPage <= 1" @click="cohortPage = Math.max(1, cohortPage - 1)">Previous page</UIButton>
            <UIButton size="sm" variant="outline" :disabled="cohortPage >= cohortPageCount" @click="cohortPage = Math.min(cohortPageCount, cohortPage + 1)">Next page</UIButton>
          </div>
        </div>
      </UICardContent>
    </UICard>

    <div v-else-if="activeTab === 'publishing'" class="space-y-5">
      <div class="grid gap-5 xl:grid-cols-[1fr,1.2fr]">
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
          <UICardTitle class="flex items-center gap-2 text-lg"><Activity class="h-5 w-5" /> Sensitive Publishing Actions</UICardTitle>
          </UICardHeader>
          <UICardContent class="space-y-2">
            <div class="rounded-lg border border-border/60 bg-background/60 p-3">
              <p class="mb-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">Content Takedown</p>
              <div class="space-y-2">
                <UIInput v-model="takedownForm.contentId" placeholder="Content ID" />
                <UITextarea v-model="takedownForm.reason" :rows="2" placeholder="Reason for takedown" />
                <UIButton size="sm" variant="outline" @click="takeDownContent">Run Takedown</UIButton>
              </div>
            </div>

            <p class="pt-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">Recent Audit Activity</p>
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

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle>Review Workflow Setup</UICardTitle>
          <UICardDescription>
            Reviewers only see submissions after template stages are configured and workflow is initialized per content.
          </UICardDescription>
        </UICardHeader>
        <UICardContent class="grid gap-4 xl:grid-cols-[1fr,1.2fr]">
          <div class="space-y-3 rounded-lg border border-border/60 bg-background/60 p-3">
            <p class="text-xs uppercase tracking-[0.12em] text-muted-foreground">Create Template Stage</p>
            <UIInput v-model="workflowStageForm.stage_name" placeholder="Stage name" />
            <UIInput v-model="workflowStageForm.stage_order" type="number" placeholder="Stage order" />
            <UITextarea v-model="workflowStageForm.description" :rows="2" placeholder="Description (optional)" />
            <div class="grid gap-2 sm:grid-cols-2">
              <label class="flex items-center gap-2 text-sm">
                <input v-model="workflowStageForm.is_required" type="checkbox" />
                Required stage
              </label>
              <label class="flex items-center gap-2 text-sm">
                <input v-model="workflowStageForm.is_parallel" type="checkbox" />
                Parallel approvals
              </label>
            </div>
            <UIButton size="sm" @click="createWorkflowStage">Create Stage</UIButton>
          </div>

          <div class="space-y-3 rounded-lg border border-border/60 bg-background/60 p-3">
            <p class="text-xs uppercase tracking-[0.12em] text-muted-foreground">Initialize Content Workflow</p>
            <UIInput v-model="workflowInitForm.contentId" placeholder="Content ID (UUID)" />
            <UIButton size="sm" variant="outline" @click="initializeWorkflowForContent">Initialize Workflow</UIButton>
            <p v-if="workflowMessage" class="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-sm text-muted-foreground">
              {{ workflowMessage }}
            </p>

            <div class="space-y-2">
              <p class="text-xs uppercase tracking-[0.12em] text-muted-foreground">Active Template Stages</p>
              <div
                v-for="stage in store.workflowTemplateStages"
                :key="stage.id"
                class="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-sm"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="font-medium">{{ stage.stage_order }}. {{ stage.stage_name }}</span>
                  <div class="flex gap-1">
                    <UIBadge variant="outline">{{ stage.is_required ? 'Required' : 'Optional' }}</UIBadge>
                    <UIBadge variant="outline">{{ stage.is_parallel ? 'Parallel' : 'Sequential' }}</UIBadge>
                  </div>
                </div>
                <p v-if="stage.description" class="mt-1 text-xs text-muted-foreground">{{ stage.description }}</p>
              </div>
              <p v-if="!store.workflowTemplateStages.length" class="text-xs text-muted-foreground">
                No active template stages yet.
              </p>
            </div>
          </div>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle>Publishing History and Visibility</UICardTitle>
          <UICardDescription>Inspect publishing records and canary visibility from the admin workspace.</UICardDescription>
        </UICardHeader>
        <UICardContent class="grid gap-4 xl:grid-cols-[1fr,1.2fr]">
          <div class="space-y-3 rounded-lg border border-border/60 bg-background/60 p-3">
            <p class="text-xs uppercase tracking-[0.12em] text-muted-foreground">History Lookup</p>
            <UIInput v-model="publishingLookupForm.historyContentId" placeholder="Content ID" />
            <UIButton size="sm" @click="loadPublishingHistory">Load History</UIButton>
            <div v-if="store.publishingHistory.length" class="space-y-2">
              <div v-for="entry in store.publishingHistory" :key="entry.id" class="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-sm">
                <div class="flex items-center justify-between gap-2">
                  <span class="font-medium">{{ entry.action }}</span>
                  <span class="text-xs text-muted-foreground">{{ new Date(entry.created_at).toLocaleString() }}</span>
                </div>
                <p class="mt-1 text-xs text-muted-foreground">{{ entry.reason || 'No reason recorded.' }}</p>
              </div>
            </div>
          </div>

          <div class="space-y-3 rounded-lg border border-border/60 bg-background/60 p-3">
            <p class="text-xs uppercase tracking-[0.12em] text-muted-foreground">Canary Visibility Lookup</p>
            <UIInput v-model="publishingLookupForm.visibilityContentId" placeholder="Content ID" />
            <UIInput v-model="publishingLookupForm.visibilityUserId" placeholder="User ID" />
            <UIButton size="sm" variant="outline" @click="checkVisibility">Check Visibility</UIButton>
            <div v-if="store.canaryVisibilityResult" class="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-sm">
              <p class="font-medium">{{ store.canaryVisibilityResult.visible ? 'Visible' : 'Not visible' }}</p>
              <p class="mt-1 text-xs text-muted-foreground">Reason: {{ store.canaryVisibilityResult.reason }}</p>
            </div>
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
        <div v-if="isAdmin" class="rounded-lg border border-border/60 bg-background/60 p-3">
          <p class="mb-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">Legal Hold</p>
          <div class="grid gap-2 md:grid-cols-2">
            <UIInput v-model="legalHoldForm.userId" placeholder="User ID" />
            <UIInput v-model="legalHoldForm.reason" placeholder="Reason (optional)" />
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <UIButton size="sm" variant="outline" @click="loadLegalHold">Check Status</UIButton>
            <UIButton size="sm" @click="setLegalHold(true)">Set Hold</UIButton>
            <UIButton size="sm" variant="outline" @click="setLegalHold(false)">Unset Hold</UIButton>
          </div>
          <div v-if="store.legalHoldStatus" class="mt-2 text-xs text-muted-foreground">
            <p>Status: {{ store.legalHoldStatus.legal_hold ? 'On hold' : 'Not on hold' }}</p>
            <p>Updated: {{ store.legalHoldStatus.updated_at ? new Date(store.legalHoldStatus.updated_at).toLocaleString() : 'n/a' }}</p>
            <p v-if="store.legalHoldStatus.reason">Reason: {{ store.legalHoldStatus.reason }}</p>
          </div>
          <p v-if="legalHoldMessage" class="mt-2 text-xs text-muted-foreground">{{ legalHoldMessage }}</p>
        </div>

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
          <div v-for="log in pagedAuditLogs" :key="log.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
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
          <div v-if="store.auditLogs.length > 12" class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>Showing page {{ auditPage }} of {{ auditPageCount }}</span>
            <div class="flex gap-2">
              <UIButton size="sm" variant="outline" :disabled="auditPage <= 1" @click="auditPage = Math.max(1, auditPage - 1)">Previous page</UIButton>
              <UIButton size="sm" variant="outline" :disabled="auditPage >= auditPageCount" @click="auditPage = Math.min(auditPageCount, auditPage + 1)">Next page</UIButton>
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
          <div v-for="delivery in pagedWebhookDeliveries" :key="delivery.id" class="rounded-lg border border-border/60 bg-background/60 p-3">
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

          <div v-if="store.webhookDeliveries.length > 12" class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>Showing page {{ webhookPage }} of {{ webhookPageCount }}</span>
            <div class="flex gap-2">
              <UIButton size="sm" variant="outline" :disabled="webhookPage <= 1" @click="webhookPage = Math.max(1, webhookPage - 1)">Previous page</UIButton>
              <UIButton size="sm" variant="outline" :disabled="webhookPage >= webhookPageCount" @click="webhookPage = Math.min(webhookPageCount, webhookPage + 1)">Next page</UIButton>
            </div>
          </div>

          <div v-if="!store.webhookDeliveries.length" class="rounded-xl border border-dashed border-border/70 p-8 text-center text-sm text-muted-foreground">
            No webhook deliveries found for the selected filter.
          </div>
        </UICardContent>
      </UICard>
    </div>

    <StepUpConfirmationModal
      :open="stepUpOpen"
      title="Step-up confirmation"
      description="Re-enter your password to continue with this sensitive action."
      confirm-label="Confirm action"
      :loading="stepUpLoading"
      :error-message="stepUpError"
      @cancel="cancelStepUp"
      @confirm="onStepUpConfirm"
    />
  </section>
</template>
