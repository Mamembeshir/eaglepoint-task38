<script setup lang="ts">
import { AlertTriangle, FileText, Send, ShieldAlert } from 'lucide-vue-next'
import { computed, onMounted, reactive } from 'vue'

import { UIBadge } from '@/components/ui/badge'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UIInput } from '@/components/ui/input'
import { UITextarea } from '@/components/ui/textarea'
import { useContentAuthorWorkspaceStore } from '@/stores/contentAuthorWorkspace'

const store = useContentAuthorWorkspaceStore()

const submitForm = reactive({
  content_type: 'article' as 'article' | 'video' | 'job_announcement',
  title: '',
  body: '',
  media_url: ''
})

const selectedSubmission = computed(() => store.submissions[0] ?? null)

async function submit() {
  const ok = await store.submitContent({
    content_type: submitForm.content_type,
    title: submitForm.title,
    body: submitForm.body || undefined,
    media_url: submitForm.media_url || undefined
  })
  if (!ok) return
  submitForm.title = ''
  submitForm.body = ''
  submitForm.media_url = ''
}

onMounted(async () => {
  await store.loadSubmissions()
})
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Content Author</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Editorial Submission Studio</h2>
      <p class="mt-1 text-sm text-muted-foreground">Submit content, monitor risk grading, and review workflow feedback in one place.</p>
    </header>

    <div class="grid gap-5 xl:grid-cols-[1fr,1.1fr]">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><Send class="h-5 w-5" /> New Submission</UICardTitle>
          <UICardDescription>Article, video, or job announcement content with automatic risk analysis.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <select v-model="submitForm.content_type" class="h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
            <option value="article">Article</option>
            <option value="video">Video</option>
            <option value="job_announcement">Job Announcement</option>
          </select>
          <UIInput v-model="submitForm.title" placeholder="Content title" />
          <UITextarea v-model="submitForm.body" placeholder="Body (required for article/job announcement)" :rows="5" />
          <UIInput v-model="submitForm.media_url" placeholder="Media URL (required for video)" />
          <p v-if="store.submitError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {{ store.submitError }}
          </p>
          <UIButton class="w-full" :disabled="store.loading" @click="submit">
            {{ store.loading ? 'Submitting...' : 'Submit for Review' }}
          </UIButton>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><FileText class="h-5 w-5" /> Submission Queue</UICardTitle>
          <UICardDescription>Track review status, risk score, and comments from reviewers.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <div
            v-for="item in store.submissions"
            :key="item.content_id"
            class="rounded-lg border border-border/60 bg-background/60 p-3"
          >
            <div class="mb-2 flex items-start justify-between gap-2">
              <div>
                <p class="font-medium leading-5">{{ item.title }}</p>
                <p class="text-xs capitalize text-muted-foreground">{{ item.content_type.replace('_', ' ') }}</p>
              </div>
              <UIBadge variant="secondary" class="capitalize">{{ item.status.replace('_', ' ') }}</UIBadge>
            </div>

            <div class="mb-2 flex flex-wrap gap-2">
              <UIBadge v-if="item.risk_grade" variant="outline" class="gap-1">
                <ShieldAlert class="h-3 w-3" />
                {{ item.risk_grade }} ({{ item.risk_score ?? 0 }})
              </UIBadge>
            </div>

            <div class="space-y-2">
              <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">Review comments</p>
              <div
                v-for="comment in item.review_comments"
                :key="`${item.content_id}-${comment.created_at}-${comment.stage_name}`"
                class="rounded-md border border-border/60 bg-card/60 p-2"
              >
                <div class="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                  <span>{{ comment.stage_name }} • {{ comment.decision }}</span>
                  <span>{{ new Date(comment.created_at).toLocaleString() }}</span>
                </div>
                <p class="text-sm">{{ comment.comments || 'No comment text provided.' }}</p>
              </div>
              <p v-if="!item.review_comments.length" class="text-xs text-muted-foreground">No review comments yet.</p>
            </div>
          </div>

          <div v-if="!store.submissions.length" class="rounded-xl border border-dashed border-border/70 p-8 text-center text-sm text-muted-foreground">
            No submissions yet. Start by sending your first item for risk and review.
          </div>
        </UICardContent>
      </UICard>
    </div>

    <UICard v-if="selectedSubmission" class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle class="flex items-center gap-2 text-lg"><AlertTriangle class="h-5 w-5" /> Latest Submission Snapshot</UICardTitle>
        <UICardDescription>
          {{ selectedSubmission.title }} • {{ selectedSubmission.status.replace('_', ' ') }}
        </UICardDescription>
      </UICardHeader>
      <UICardContent>
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="rounded-lg border border-border/60 bg-background/60 p-3">
            <p class="text-xs text-muted-foreground">Risk Grade</p>
            <p class="text-lg font-semibold">{{ selectedSubmission.risk_grade || 'N/A' }}</p>
          </div>
          <div class="rounded-lg border border-border/60 bg-background/60 p-3">
            <p class="text-xs text-muted-foreground">Risk Score</p>
            <p class="text-lg font-semibold">{{ selectedSubmission.risk_score ?? 0 }}</p>
          </div>
          <div class="rounded-lg border border-border/60 bg-background/60 p-3">
            <p class="text-xs text-muted-foreground">Comment Count</p>
            <p class="text-lg font-semibold">{{ selectedSubmission.review_comments.length }}</p>
          </div>
        </div>
      </UICardContent>
    </UICard>
  </section>
</template>
