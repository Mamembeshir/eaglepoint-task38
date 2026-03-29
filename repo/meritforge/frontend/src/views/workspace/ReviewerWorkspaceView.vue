<script setup lang="ts">
import { Check, CornerDownLeft, ShieldCheck } from 'lucide-vue-next'
import { onMounted, reactive } from 'vue'

import { UIBadge } from '@/components/ui/badge'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UITextarea } from '@/components/ui/textarea'
import { useReviewerWorkspaceStore } from '@/stores/reviewerWorkspace'

const store = useReviewerWorkspaceStore()
const commentsByStage = reactive<Record<string, string>>({})

async function approve(stageId: string) {
  const ok = await store.approve(stageId, commentsByStage[stageId] || undefined)
  if (ok) {
    commentsByStage[stageId] = ''
  }
}

async function returnForRevision(stageId: string) {
  const ok = await store.returnForRevision(stageId, commentsByStage[stageId] || '')
  if (ok) {
    commentsByStage[stageId] = ''
  }
}

onMounted(async () => {
  await store.loadQueue()
})
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Reviewer</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Review Decision Workspace</h2>
      <p class="mt-1 text-sm text-muted-foreground">Process the queue quickly with one-click approvals and revision returns.</p>
    </header>

    <UICard class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle class="flex items-center gap-2 text-lg"><ShieldCheck class="h-5 w-5" /> Review Queue</UICardTitle>
        <UICardDescription>Items awaiting reviewer decisions across workflow stages.</UICardDescription>
      </UICardHeader>
      <UICardContent class="space-y-4">
        <p v-if="store.actionError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {{ store.actionError }}
        </p>

        <div
          v-for="item in store.queue"
          :key="item.stage_id"
          class="rounded-xl border border-border/60 bg-background/60 p-4"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <div>
              <p class="font-medium leading-5">{{ item.title }}</p>
              <p class="text-xs text-muted-foreground">Stage {{ item.stage_order }} • {{ item.stage_name }}</p>
            </div>
            <div class="flex items-center gap-2">
              <UIBadge variant="secondary" class="capitalize">{{ item.status.replace('_', ' ') }}</UIBadge>
              <UIBadge variant="outline">{{ item.current_distinct_approvers }}/{{ item.required_distinct_reviewers }} approvals</UIBadge>
            </div>
          </div>

          <div v-if="item.latest_comment" class="mb-3 rounded-md border border-border/60 bg-card/60 p-2 text-sm">
            <p class="mb-1 text-xs uppercase text-muted-foreground">Latest comment</p>
            <p>{{ item.latest_comment }}</p>
          </div>

          <div class="mb-3">
            <label class="mb-1 block text-xs uppercase text-muted-foreground">Comment</label>
            <UITextarea
              v-model="commentsByStage[item.stage_id]"
              placeholder="Add reviewer context (required for Return for Revision)"
              :rows="3"
            />
            <p class="mt-1 text-xs text-muted-foreground">
              {{ (commentsByStage[item.stage_id] || '').trim().length }}/20 minimum characters for return-for-revision
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <UIButton size="sm" class="gap-2" @click="approve(item.stage_id)">
              <Check class="h-4 w-4" />
              Approve
            </UIButton>
            <UIButton
              size="sm"
              variant="outline"
              class="gap-2"
              :disabled="(commentsByStage[item.stage_id] || '').trim().length < 20"
              @click="returnForRevision(item.stage_id)"
            >
              <CornerDownLeft class="h-4 w-4" />
              Return for Revision
            </UIButton>
          </div>
        </div>

        <div v-if="!store.queue.length" class="rounded-xl border border-dashed border-border/70 p-8 text-center text-sm text-muted-foreground">
          <p class="font-medium text-foreground">No items are visible in the review queue yet.</p>
          <p class="mt-2">
            Submissions appear here only after an administrator configures workflow template stages and initializes workflow for each content item.
          </p>
        </div>
      </UICardContent>
    </UICard>
  </section>
</template>
