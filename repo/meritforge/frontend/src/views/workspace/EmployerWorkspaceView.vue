<script setup lang="ts">
import { Briefcase, CheckCircle2, ClipboardList, Plus } from 'lucide-vue-next'
import { computed, onMounted, reactive, watch } from 'vue'

import { UIBadge } from '@/components/ui/badge'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UIInput } from '@/components/ui/input'
import { UITextarea } from '@/components/ui/textarea'
import { useEmployerWorkspaceStore } from '@/stores/employerWorkspace'

const store = useEmployerWorkspaceStore()

const createForm = reactive({
  title: '',
  employer_name: '',
  location: '',
  employment_type: '',
  application_deadline: '',
  description: ''
})

const milestoneTemplateForm = reactive({
  key: '',
  name: '',
  description: '',
  threshold_count: '1'
})

const selectedPost = computed(() => store.posts.find((p) => p.id === store.selectedPostId) ?? null)

async function createPost() {
  await store.createPost({
    title: createForm.title,
    employer_name: createForm.employer_name,
    location: createForm.location || undefined,
    employment_type: createForm.employment_type || undefined,
    application_deadline: createForm.application_deadline || undefined,
    description: createForm.description || undefined
  })

  createForm.title = ''
  createForm.employer_name = ''
  createForm.location = ''
  createForm.employment_type = ''
  createForm.application_deadline = ''
  createForm.description = ''
}

async function createMilestoneTemplate() {
  await store.createMilestoneTemplate({
    key: milestoneTemplateForm.key,
    name: milestoneTemplateForm.name,
    description: milestoneTemplateForm.description || undefined,
    threshold_count: Number(milestoneTemplateForm.threshold_count)
  })
  milestoneTemplateForm.key = ''
  milestoneTemplateForm.name = ''
  milestoneTemplateForm.description = ''
  milestoneTemplateForm.threshold_count = '1'
}

watch(
  () => store.selectedPostId,
  async () => {
    await store.loadSelectedPostDetails()
  }
)

onMounted(async () => {
  await store.loadPosts()
  await store.loadSelectedPostDetails()
})
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Employer Manager</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Hiring Operations Workspace</h2>
      <p class="mt-1 text-sm text-muted-foreground">Create job posts, track applications, and verify candidate milestone progress.</p>
    </header>

    <div class="grid gap-5 xl:grid-cols-[1fr,1.1fr]">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><Plus class="h-5 w-5" /> Create Job Post</UICardTitle>
          <UICardDescription>Publish a new role for your organization.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <UIInput v-model="createForm.title" placeholder="Role title" />
          <UIInput v-model="createForm.employer_name" placeholder="Employer name" />
          <div class="grid gap-3 sm:grid-cols-2">
            <UIInput v-model="createForm.location" placeholder="Location" />
            <UIInput v-model="createForm.employment_type" placeholder="Employment type" />
          </div>
          <UIInput v-model="createForm.application_deadline" type="date" />
          <UITextarea v-model="createForm.description" placeholder="Optional job summary" :rows="3" />
          <UIButton class="w-full" @click="createPost">Create Job Post</UIButton>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><Briefcase class="h-5 w-5" /> Your Job Posts</UICardTitle>
          <UICardDescription>Select a job post to inspect application and milestone activity.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-2">
          <button
            v-for="post in store.posts"
            :key="post.id"
            class="w-full rounded-lg border border-border/60 bg-background/60 p-3 text-left transition hover:bg-accent/30"
            :class="store.selectedPostId === post.id ? 'border-primary/50 bg-primary/10' : ''"
            @click="store.selectedPostId = post.id"
          >
            <div class="flex items-center justify-between gap-2">
              <p class="font-medium leading-5">{{ post.title }}</p>
              <UIBadge :variant="post.is_active ? 'success' : 'outline'">{{ post.is_active ? 'Active' : 'Inactive' }}</UIBadge>
            </div>
            <p class="text-xs text-muted-foreground">{{ post.employer_name }} • {{ post.location || 'Location flexible' }}</p>
          </button>
          <p v-if="!store.posts.length" class="text-sm text-muted-foreground">No job posts created yet.</p>
        </UICardContent>
      </UICard>
    </div>

    <div class="grid gap-5 xl:grid-cols-2">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="text-lg">Milestone Template Setup</UICardTitle>
          <UICardDescription>Create hiring-track milestone templates for the selected post.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <UIInput v-model="milestoneTemplateForm.key" placeholder="Template key" />
          <UIInput v-model="milestoneTemplateForm.name" placeholder="Template name" />
          <UITextarea v-model="milestoneTemplateForm.description" :rows="2" placeholder="Description (optional)" />
          <UIInput v-model="milestoneTemplateForm.threshold_count" type="number" placeholder="Threshold count" />
          <UIButton class="w-full" :disabled="!store.selectedPostId" @click="createMilestoneTemplate">Create Template</UIButton>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><ClipboardList class="h-5 w-5" /> Applications</UICardTitle>
          <UICardDescription v-if="selectedPost">Tracking for {{ selectedPost.title }}</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <div
            v-for="app in store.applications"
            :key="app.id"
            class="rounded-lg border border-border/60 bg-background/60 p-3"
          >
            <div class="mb-2 flex items-center justify-between gap-2">
              <p class="text-sm font-medium">Applicant: {{ app.applicant_id.slice(0, 8) }}...</p>
              <UIBadge variant="secondary" class="capitalize">{{ app.status.replace('_', ' ') }}</UIBadge>
            </div>
            <div class="flex flex-wrap gap-2">
              <UIButton size="sm" variant="outline" @click="store.updateApplicationStatus(app.id, 'under_review')">Under Review</UIButton>
              <UIButton size="sm" variant="outline" @click="store.updateApplicationStatus(app.id, 'interview_scheduled')">Interview</UIButton>
              <UIButton size="sm" variant="outline" @click="store.updateApplicationStatus(app.id, 'accepted')">Accept</UIButton>
              <UIButton size="sm" variant="outline" @click="store.updateApplicationStatus(app.id, 'rejected')">Reject</UIButton>
            </div>
          </div>
          <p v-if="!store.applications.length" class="text-sm text-muted-foreground">No applications for this post yet.</p>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><CheckCircle2 class="h-5 w-5" /> Milestone Verification</UICardTitle>
          <UICardDescription>Validate student-reported progress for this hiring track.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <div
            v-for="milestone in store.milestones"
            :key="milestone.id"
            class="rounded-lg border border-border/60 bg-background/60 p-3"
          >
            <div class="mb-2 flex items-center justify-between gap-2">
              <p class="text-sm font-medium">{{ milestone.milestone_name }}</p>
              <UIBadge :variant="milestone.is_verified ? 'success' : 'outline'">{{ milestone.is_verified ? 'Verified' : 'Pending' }}</UIBadge>
            </div>
            <p class="mb-2 text-xs text-muted-foreground">{{ milestone.progress_value }}/{{ milestone.target_value }} progress</p>
            <div class="flex gap-2">
              <UIButton size="sm" variant="outline" @click="store.verifyMilestone(milestone.id, true)">Verify</UIButton>
              <UIButton size="sm" variant="outline" @click="store.verifyMilestone(milestone.id, false)">Unverify</UIButton>
            </div>
          </div>
          <p v-if="!store.milestones.length" class="text-sm text-muted-foreground">No milestones to verify yet.</p>
        </UICardContent>
      </UICard>
    </div>
  </section>
</template>
