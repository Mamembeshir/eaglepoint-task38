<script setup lang="ts">
import {
  BookHeart,
  Bookmark,
  CheckCircle2,
  FileText,
  FastForward,
  Heart,
  Newspaper,
  Play,
  Sparkles,
  StickyNote,
  Video
} from 'lucide-vue-next'
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { UIBadge } from '@/components/ui/badge'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UIInput } from '@/components/ui/input'
import { UITextarea } from '@/components/ui/textarea'
import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'
import { useStudentWorkspaceStore } from '@/stores/studentWorkspace'

const workspace = useStudentWorkspaceStore()

const playerEl = ref<HTMLVideoElement | null>(null)
const activeTab = ref<'videos' | 'bookshelf' | 'milestones'>('videos')
const contentFilter = ref<'all' | 'video' | 'article' | 'job_announcement'>('all')
const annotationDraft = ref('')
const annotationSaving = ref(false)
const annotationError = ref('')
const transcriptSelectionHost = ref<HTMLElement | null>(null)
const selectedStartOffset = ref<number | null>(null)
const selectedEndOffset = ref<number | null>(null)
const selectedHighlightedText = ref('')
const searchQuery = ref('')
const searchResults = ref<Array<{ id: string; title: string; topic: string; durationSeconds: number; contentType: string }>>([])
const searching = ref(false)
const pageError = ref('')
const videoLoadError = ref('')
const videoLoading = ref(false)
const milestoneForm = reactive({
  applicationId: '',
  milestoneTemplateId: '',
  milestoneName: '',
  progressValue: '1',
  targetValue: '1',
  description: ''
})
const applyForm = reactive({
  coverLetter: ''
})
const applyLoading = ref(false)
const applyMessage = ref('')
let searchDebounceHandle: ReturnType<typeof setTimeout> | null = null
let lastTelemetryTick = 0

const allTopics = computed(() => [...new Set(workspace.videos.map((video) => video.topic))])
const filteredContent = computed(() => {
  if (contentFilter.value === 'all') return workspace.videos
  return workspace.videos.filter((item) => item.contentType === contentFilter.value)
})
const currentContent = computed(() => workspace.currentVideo)
const currentProgress = computed(() => {
  const current = currentContent.value
  if (!current || current.contentType !== 'video') return 0
  return workspace.progressByVideo[current.id] ?? 0
})

const currentAnnotations = computed(() => {
  const current = workspace.currentVideo
  if (!current) return []
  return workspace.annotationsByVideo[current.id] ?? []
})

const completionPercentage = (progressValue: number, targetValue: number) => {
  if (targetValue <= 0) return 0
  return Math.min(100, Math.round((progressValue / targetValue) * 100))
}

async function onVideoPlay() {
  if (!playerEl.value) return
  await workspace.trackPlay(Math.floor(playerEl.value.currentTime))
}

async function onVideoTimeUpdate() {
  if (!playerEl.value || !workspace.currentVideo) return
  if (workspace.currentVideo.contentType !== 'video') return
  const now = Date.now()
  if (now - lastTelemetryTick < 5000) return
  lastTelemetryTick = now
  await workspace.trackPlay(Math.floor(playerEl.value.currentTime))
}

async function skipVideo() {
  await workspace.skipCurrentVideo()
  const currentIndex = workspace.videos.findIndex((v) => v.id === workspace.currentVideoId)
  const next = workspace.videoItems[(workspace.videoItems.findIndex((v) => v.id === workspace.currentVideoId) + 1) % workspace.videoItems.length]
  if (next) {
    workspace.selectVideo(next.id)
  }
}

function onVideoSourceChange() {
  videoLoadError.value = ''
  videoLoading.value = Boolean(workspace.currentVideo?.streamUrl)
}

function onVideoLoaded() {
  videoLoadError.value = ''
  videoLoading.value = false
}

function onVideoError() {
  videoLoading.value = false
  videoLoadError.value = "This video URL couldn't be loaded (network, CORS, or invalid URL)."
}

function retryVideoLoad() {
  if (!playerEl.value) return
  videoLoadError.value = ''
  videoLoading.value = true
  playerEl.value.load()
}

async function submitMilestoneUpdate() {
  pageError.value = ''
  try {
    await workspace.reportApplicationMilestone({
      applicationId: milestoneForm.applicationId,
      milestoneTemplateId: milestoneForm.milestoneTemplateId,
      milestoneName: milestoneForm.milestoneName,
      progressValue: Number(milestoneForm.progressValue),
      targetValue: Number(milestoneForm.targetValue),
      description: milestoneForm.description || undefined
    })
    milestoneForm.milestoneName = ''
    milestoneForm.description = ''
  } catch (error) {
    pageError.value = getApiErrorMessage(error)
    logDevError(error)
  }
}

async function applyToSelectedJob() {
  if (!currentContent.value?.jobPostId) {
    applyMessage.value = 'This job announcement cannot accept applications from this view yet.'
    return
  }

  applyLoading.value = true
  applyMessage.value = ''
  try {
    const application = await workspace.applyToJobPost(currentContent.value.jobPostId, {
      coverLetter: applyForm.coverLetter || undefined
    })
    applyMessage.value = `Application submitted (${application.id.slice(0, 8)}...).`
    applyForm.coverLetter = ''
  } catch (error) {
    applyMessage.value = getApiErrorMessage(error)
    logDevError(error)
  } finally {
    applyLoading.value = false
  }
}

async function saveAnnotation() {
  annotationError.value = ''
  if (!workspace.currentVideo || !annotationDraft.value.trim()) return
  if (selectedStartOffset.value === null || selectedEndOffset.value === null || !selectedHighlightedText.value.trim()) {
    annotationError.value = 'Select text from transcript/content before saving annotation.'
    return
  }
  annotationSaving.value = true
  try {
    await workspace.addAnnotation(workspace.currentVideo.id, annotationDraft.value, {
      startOffset: selectedStartOffset.value,
      endOffset: selectedEndOffset.value,
      highlightedText: selectedHighlightedText.value
    })
    annotationDraft.value = ''
    selectedStartOffset.value = null
    selectedEndOffset.value = null
    selectedHighlightedText.value = ''
  } catch (error) {
    annotationError.value = getApiErrorMessage(error)
    logDevError(error)
  } finally {
    annotationSaving.value = false
  }
}

function captureSelectionFromTranscript() {
  const host = transcriptSelectionHost.value
  const selection = window.getSelection()
  if (!host || !selection || selection.rangeCount === 0) {
    selectedStartOffset.value = null
    selectedEndOffset.value = null
    selectedHighlightedText.value = ''
    return
  }

  const range = selection.getRangeAt(0)
  if (!host.contains(range.commonAncestorContainer)) {
    selectedStartOffset.value = null
    selectedEndOffset.value = null
    selectedHighlightedText.value = ''
    return
  }

  const highlighted = range.toString()
  if (!highlighted.trim()) {
    selectedStartOffset.value = null
    selectedEndOffset.value = null
    selectedHighlightedText.value = ''
    return
  }

  const preRange = document.createRange()
  preRange.selectNodeContents(host)
  preRange.setEnd(range.startContainer, range.startOffset)

  selectedStartOffset.value = preRange.toString().length
  selectedEndOffset.value = selectedStartOffset.value + highlighted.length
  selectedHighlightedText.value = highlighted
}

watch(
  searchQuery,
  (value) => {
    if (searchDebounceHandle) {
      clearTimeout(searchDebounceHandle)
    }
    searchDebounceHandle = setTimeout(async () => {
      const normalized = value.trim()
      if (!normalized) {
        searchResults.value = []
        return
      }
      searching.value = true
      try {
        const results = await workspace.searchCatalog(normalized, undefined, 20)
        searchResults.value = results.map((item) => ({
          id: item.id,
          title: item.title,
          topic: item.topic,
          durationSeconds: item.durationSeconds,
          contentType: item.contentType
        }))
      } catch (error) {
        pageError.value = getApiErrorMessage(error)
        logDevError(error)
      } finally {
        searching.value = false
      }
    }, 300)
  }
)

watch(
  () => workspace.currentVideoId,
  async (videoId) => {
    pageError.value = ''
    applyMessage.value = ''
    onVideoSourceChange()
    try {
      await workspace.loadAnnotations(videoId)
    } catch (error) {
      pageError.value = getApiErrorMessage(error)
      logDevError(error)
    }
    selectedStartOffset.value = null
    selectedEndOffset.value = null
    selectedHighlightedText.value = ''
    const resume = workspace.progressByVideo[videoId] ?? 0
    if (playerEl.value && resume > 0) {
      playerEl.value.currentTime = resume
    }
  }
)

onMounted(async () => {
  pageError.value = ''
  onVideoSourceChange()
  try {
    await workspace.hydrateServerState()
    if (workspace.currentVideo) {
      await workspace.loadAnnotations(workspace.currentVideo.id)
    }
  } catch (error) {
    pageError.value = getApiErrorMessage(error)
    logDevError(error)
  }
})
</script>

<template>
  <section class="space-y-6">
    <header class="space-y-2">
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Student Workspace</p>
      <h2 class="text-3xl font-semibold tracking-tight">Career Learning Studio</h2>
      <p class="max-w-3xl text-sm text-muted-foreground">
        Browse published career videos, articles, and job announcements, then save the items you want to revisit.
      </p>
    </header>

    <div class="flex flex-wrap items-center gap-2 rounded-xl border border-border/60 bg-card/70 p-2">
      <UIButton :variant="activeTab === 'videos' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'videos'">Browse Content</UIButton>
      <UIButton :variant="activeTab === 'bookshelf' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'bookshelf'">Bookshelf</UIButton>
      <UIButton :variant="activeTab === 'milestones' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'milestones'">Milestones</UIButton>
    </div>

    <p v-if="workspace.loading" class="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-sm text-muted-foreground">
      Loading your workspace...
    </p>
    <p v-if="workspace.hydrateError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {{ workspace.hydrateError }}
    </p>
    <p v-if="workspace.actionError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {{ workspace.actionError }}
    </p>
    <p v-if="workspace.searchError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {{ workspace.searchError }}
    </p>
    <p v-if="workspace.annotationsError || pageError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {{ workspace.annotationsError || pageError }}
    </p>

    <div v-if="activeTab === 'videos'" class="grid gap-5 xl:grid-cols-[1.25fr,0.85fr]">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <div class="flex items-center justify-between gap-4">
            <div>
              <UICardTitle class="text-2xl">{{ currentContent?.title }}</UICardTitle>
              <UICardDescription>{{ currentContent?.summary }}</UICardDescription>
            </div>
            <UIBadge variant="secondary" class="capitalize">{{ currentContent?.contentType?.replace('_', ' ') || currentContent?.topic }}</UIBadge>
          </div>
        </UICardHeader>
        <UICardContent class="space-y-4">
          <div v-if="currentContent?.contentType === 'video'" class="overflow-hidden rounded-xl border border-border/60 bg-black">
            <video
              ref="playerEl"
              class="aspect-video w-full"
              controls
              :poster="currentContent?.poster"
              @play="onVideoPlay"
              @timeupdate="onVideoTimeUpdate"
              @loadeddata="onVideoLoaded"
              @error="onVideoError"
            >
              <source :src="currentContent?.streamUrl" type="video/mp4" />
            </video>
          </div>

          <div v-else-if="currentContent?.contentType === 'article'" class="rounded-xl border border-border/60 bg-background/60 p-5">
            <div class="mb-3 flex items-center gap-2 text-muted-foreground">
              <FileText class="h-4 w-4" />
              <span class="text-sm font-medium">Article</span>
            </div>
            <p class="text-sm leading-7 text-foreground/90">{{ currentContent.summary || 'No article summary is available yet.' }}</p>
          </div>

          <div v-else-if="currentContent?.contentType === 'job_announcement'" class="rounded-xl border border-border/60 bg-background/60 p-5">
            <div class="mb-3 flex items-center gap-2 text-muted-foreground">
              <Newspaper class="h-4 w-4" />
              <span class="text-sm font-medium">Job announcement</span>
            </div>
            <p class="text-sm leading-7 text-foreground/90">{{ currentContent.summary || 'No job summary is available yet.' }}</p>
            <div class="mt-3 space-y-2">
              <UITextarea v-model="applyForm.coverLetter" :rows="3" placeholder="Optional short cover letter" />
              <UIButton :disabled="applyLoading || !currentContent?.jobPostId" @click="applyToSelectedJob">
                {{ applyLoading ? 'Submitting...' : 'Apply to this job' }}
              </UIButton>
              <p v-if="applyMessage" class="text-xs text-muted-foreground">{{ applyMessage }}</p>
            </div>
          </div>

          <div v-if="currentContent?.status === 'retracted'" class="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-700">
            {{ currentContent.retractionNotice || 'This content has been retracted.' }}
          </div>

          <p v-if="videoLoading" class="text-xs text-muted-foreground">Loading video...</p>
          <div v-if="videoLoadError" class="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            <p>{{ videoLoadError }}</p>
            <div class="mt-2 flex flex-wrap items-center gap-2">
              <UIButton size="sm" variant="outline" @click="retryVideoLoad">Retry</UIButton>
              <a
                v-if="currentContent?.streamUrl"
                :href="currentContent.streamUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="text-xs text-primary underline-offset-2 hover:underline"
              >
                Open video URL in new tab
              </a>
            </div>
          </div>

          <div v-if="currentContent?.contentType === 'video'" class="grid gap-3 sm:grid-cols-2">
            <UIButton class="gap-2" @click="onVideoPlay">
              <Play class="h-4 w-4" />
              Track play
            </UIButton>
            <UIButton variant="secondary" class="gap-2" @click="skipVideo">
              <FastForward class="h-4 w-4" />
              Skip to next
            </UIButton>
            <UIButton
              variant="outline"
              class="gap-2"
              @click="currentContent && workspace.toggleFavorite(currentContent.id)"
            >
              <Heart class="h-4 w-4" :class="currentContent && workspace.favoriteVideoIds.includes(currentContent.id) ? 'fill-current text-rose-500' : ''" />
              Favorite
            </UIButton>
            <UIButton
              variant="outline"
              class="gap-2"
              @click="currentContent && workspace.toggleBookmark(currentContent.id)"
            >
              <Bookmark class="h-4 w-4" />
              Bookmark
            </UIButton>
          </div>

          <div v-if="currentContent?.contentType === 'video'" class="rounded-xl border border-border/60 bg-background/60 p-4">
            <div class="mb-2 flex items-center justify-between text-sm">
              <span class="font-medium">Resume where you left off</span>
              <span class="text-muted-foreground">{{ currentProgress }}s</span>
            </div>
            <div class="h-2 rounded-full bg-muted">
              <div
                class="h-2 rounded-full bg-primary transition-all"
                :style="{ width: `${currentContent ? Math.min(100, (currentProgress / currentContent.durationSeconds) * 100) : 0}%` }"
              />
            </div>
          </div>
        </UICardContent>
      </UICard>

      <div class="space-y-5">
        <UICard class="border-border/60 bg-card/75">
          <UICardHeader>
            <UICardTitle class="flex items-center gap-2 text-lg"><Video class="h-5 w-5" /> Content Catalog</UICardTitle>
            <UICardDescription>Browse published career content across video, article, and hiring updates.</UICardDescription>
          </UICardHeader>
          <UICardContent class="space-y-2">
            <div class="space-y-2 rounded-lg border border-border/60 bg-background/50 p-3">
              <label class="text-xs uppercase tracking-[0.12em] text-muted-foreground">Search Content</label>
              <UIInput v-model="searchQuery" placeholder="Search by title, summary, or metadata" />
              <div class="flex flex-wrap gap-2">
                <UIButton size="sm" :variant="contentFilter === 'all' ? 'default' : 'outline'" @click="contentFilter = 'all'">All</UIButton>
                <UIButton size="sm" :variant="contentFilter === 'video' ? 'default' : 'outline'" @click="contentFilter = 'video'">Videos</UIButton>
                <UIButton size="sm" :variant="contentFilter === 'article' ? 'default' : 'outline'" @click="contentFilter = 'article'">Articles</UIButton>
                <UIButton size="sm" :variant="contentFilter === 'job_announcement' ? 'default' : 'outline'" @click="contentFilter = 'job_announcement'">Job announcements</UIButton>
              </div>
              <p v-if="searching" class="text-xs text-muted-foreground">Searching...</p>
              <div v-else-if="searchQuery.trim()" class="space-y-2">
                <button
                  v-for="video in searchResults"
                  :key="`search-${video.id}`"
                  class="w-full rounded-lg border border-border/50 p-2 text-left transition hover:bg-accent/40"
                  @click="workspace.selectVideo(video.id)"
                >
                  <p class="text-sm font-medium leading-5">{{ video.title }}</p>
                  <p class="text-xs text-muted-foreground capitalize">
                    {{ video.contentType.replace('_', ' ') }}<span v-if="video.contentType === 'video'"> · {{ Math.ceil(video.durationSeconds / 60) }} min</span>
                  </p>
                </button>
                <p v-if="!searchResults.length" class="text-xs text-muted-foreground">No results found.</p>
              </div>
            </div>
            <button
              v-for="item in filteredContent"
              :key="item.id"
              class="w-full rounded-lg border border-border/50 p-3 text-left transition hover:bg-accent/40"
              :class="item.id === workspace.currentVideoId ? 'bg-primary/10 border-primary/40' : ''"
              @click="workspace.selectVideo(item.id)"
            >
              <div class="flex items-start justify-between gap-2">
                <div>
                  <p class="text-sm font-medium leading-5">{{ item.title }}</p>
                  <p class="text-xs text-muted-foreground">
                    {{ item.contentType.replace('_', ' ') }}
                    <span v-if="item.contentType === 'video'"> · {{ Math.ceil(item.durationSeconds / 60) }} min</span>
                  </p>
                  <p v-if="item.summary" class="mt-1 line-clamp-2 text-xs text-muted-foreground">{{ item.summary }}</p>
                </div>
                <UIBadge variant="outline" class="capitalize">{{ item.topic }}</UIBadge>
              </div>
            </button>
            <p v-if="!filteredContent.length" class="text-xs text-muted-foreground">No content matches this filter yet.</p>
          </UICardContent>
        </UICard>

        <UICard class="border-border/60 bg-card/75">
          <UICardHeader>
            <UICardTitle class="flex items-center gap-2 text-lg"><Sparkles class="h-5 w-5" /> Topic Subscriptions</UICardTitle>
            <UICardDescription>Subscribe to tailor your career stream.</UICardDescription>
          </UICardHeader>
          <UICardContent class="flex flex-wrap gap-2">
            <UIButton
              v-for="topic in allTopics"
              :key="topic"
              size="sm"
              :variant="workspace.subscribedTopics.includes(topic) ? 'default' : 'outline'"
              class="capitalize"
              @click="workspace.toggleTopicSubscription(topic)"
            >
              {{ topic.replace('-', ' ') }}
            </UIButton>
          </UICardContent>
        </UICard>

        <UICard class="border-border/60 bg-card/75">
          <UICardHeader>
            <UICardTitle class="flex items-center gap-2 text-lg"><StickyNote class="h-5 w-5" /> Annotations</UICardTitle>
            <UICardDescription>Private by default, or share with a cohort.</UICardDescription>
          </UICardHeader>
          <UICardContent class="space-y-3">
            <div class="grid gap-2 sm:grid-cols-2">
              <select v-model="workspace.selectedVisibility" class="h-10 rounded-md border border-input bg-background px-3 text-sm">
                <option value="private">Private</option>
                <option value="cohort">Cohort</option>
              </select>
              <select
                v-model="workspace.selectedCohortId"
                :disabled="workspace.selectedVisibility !== 'cohort'"
                class="h-10 rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
              >
                <option value="">Select Cohort</option>
                <option v-for="cohort in workspace.cohorts" :key="cohort.id" :value="cohort.id">{{ cohort.name }}</option>
              </select>
            </div>

            <UITextarea v-model="annotationDraft" placeholder="Write your reflection, follow-up question, or action item..." :rows="3" />
            <div class="space-y-2 rounded-lg border border-border/60 bg-background/50 p-3">
              <p class="text-xs uppercase tracking-[0.12em] text-muted-foreground">Step 1: Select text from content</p>
              <p class="text-xs text-muted-foreground">Highlight transcript/excerpt text below, then add your note.</p>
              <div
                ref="transcriptSelectionHost"
                class="max-h-28 overflow-auto rounded-md border border-input bg-background px-3 py-2 text-sm leading-6"
                @mouseup="captureSelectionFromTranscript"
                @keyup="captureSelectionFromTranscript"
              >
                {{ workspace.currentVideo?.summary || 'No transcript/excerpt available for selection.' }}
              </div>
              <p v-if="selectedHighlightedText" class="text-xs text-muted-foreground">
                Selected ({{ selectedStartOffset }}-{{ selectedEndOffset }}): "{{ selectedHighlightedText }}"
              </p>
            </div>
            <p v-if="annotationError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {{ annotationError }}
            </p>
            <UIButton class="w-full" :disabled="annotationSaving || !selectedHighlightedText || (workspace.selectedVisibility === 'cohort' && !workspace.selectedCohortId)" @click="saveAnnotation">
              {{ annotationSaving ? 'Saving...' : 'Save Annotation' }}
            </UIButton>

            <div class="space-y-2">
              <div
                v-for="annotation in currentAnnotations"
                :key="annotation.id"
                class="rounded-lg border border-border/60 bg-background/50 p-3"
              >
                <div class="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                  <span class="capitalize">{{ annotation.visibility }}</span>
                  <span>{{ new Date(annotation.updated_at).toLocaleString() }}</span>
                </div>
                <p class="text-sm">{{ annotation.annotation_text }}</p>
              </div>
              <p v-if="!currentAnnotations.length" class="text-xs text-muted-foreground">No annotations yet for this video.</p>
            </div>
          </UICardContent>
        </UICard>
      </div>
    </div>

    <div v-else-if="activeTab === 'bookshelf'" class="space-y-4">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><BookHeart class="h-5 w-5" /> Private Bookshelf</UICardTitle>
          <UICardDescription>Saved content for focused revisit, notes, and continuous learning.</UICardDescription>
        </UICardHeader>
        <UICardContent>
          <div v-if="workspace.privateBookshelf.length" class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <UICard
              v-for="video in workspace.privateBookshelf"
              :key="video.id"
              class="border-border/60 bg-background/70 transition hover:-translate-y-0.5"
            >
              <UICardHeader>
                <UICardTitle class="text-base leading-5">{{ video.title }}</UICardTitle>
                <UICardDescription>{{ video.summary }}</UICardDescription>
              </UICardHeader>
              <UICardContent class="flex items-center justify-between">
                <UIBadge variant="outline" class="capitalize">{{ video.topic }}</UIBadge>
                <UIButton variant="ghost" size="sm" @click="workspace.selectVideo(video.id); activeTab = 'videos'">Open</UIButton>
              </UICardContent>
            </UICard>
          </div>
          <div v-else class="rounded-xl border border-dashed border-border/70 p-8 text-center text-sm text-muted-foreground">
             No saved content yet. Bookmark items from the catalog to build your bookshelf.
           </div>
        </UICardContent>
      </UICard>
    </div>

    <div v-else class="space-y-4">
      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="text-lg">Report Application Milestone</UICardTitle>
          <UICardDescription>Log progress updates for one of your applications.</UICardDescription>
        </UICardHeader>
        <UICardContent class="grid gap-3 md:grid-cols-2">
          <select v-model="milestoneForm.applicationId" class="h-10 rounded-md border border-input bg-background px-3 text-sm">
            <option value="">Select application</option>
            <option v-for="application in workspace.applications" :key="application.id" :value="application.id">
              {{ application.id.slice(0, 8) }}... • {{ application.status.replace('_', ' ') }}
            </option>
          </select>
          <UIInput v-model="milestoneForm.milestoneTemplateId" placeholder="Milestone template ID" />
          <UIInput v-model="milestoneForm.milestoneName" placeholder="Milestone name" class="md:col-span-2" />
          <UIInput v-model="milestoneForm.progressValue" type="number" placeholder="Progress value" />
          <UIInput v-model="milestoneForm.targetValue" type="number" placeholder="Target value" />
          <UITextarea v-model="milestoneForm.description" class="md:col-span-2" :rows="2" placeholder="Optional note" />
          <UIButton class="md:col-span-2" :disabled="!milestoneForm.applicationId || !milestoneForm.milestoneTemplateId || !milestoneForm.milestoneName" @click="submitMilestoneUpdate">
            Submit milestone update
          </UIButton>
        </UICardContent>
      </UICard>

      <UICard class="border-border/60 bg-card/75">
        <UICardHeader>
          <UICardTitle class="flex items-center gap-2 text-lg"><CheckCircle2 class="h-5 w-5" /> Employment Milestones</UICardTitle>
          <UICardDescription>Track your journey from learning interactions to verified career outcomes.</UICardDescription>
        </UICardHeader>
        <UICardContent class="space-y-3">
          <div
            v-for="milestone in workspace.milestones"
            :key="milestone.id"
            class="rounded-lg border border-border/60 bg-background/60 p-4"
          >
            <div class="mb-2 flex items-center justify-between gap-2">
              <p class="font-medium">{{ milestone.milestone_name }}</p>
              <UIBadge :variant="milestone.progress_value >= milestone.target_value ? 'success' : 'secondary'">
                {{ milestone.progress_value }}/{{ milestone.target_value }}
              </UIBadge>
            </div>
            <div class="h-2 rounded-full bg-muted">
              <div
                class="h-2 rounded-full bg-primary transition-all"
                :style="{ width: `${completionPercentage(milestone.progress_value, milestone.target_value)}%` }"
              />
            </div>
            <div class="mt-2 flex items-center justify-between text-xs text-muted-foreground">
              <span class="capitalize">{{ milestone.source }} update</span>
              <span>{{ new Date(milestone.updated_at).toLocaleString() }}</span>
            </div>
          </div>
          <div v-if="!workspace.milestones.length" class="rounded-xl border border-dashed border-border/70 p-8 text-center text-sm text-muted-foreground">
            Milestones will appear here as your activity and job progress updates are recorded.
          </div>
        </UICardContent>
      </UICard>
    </div>
  </section>
</template>
