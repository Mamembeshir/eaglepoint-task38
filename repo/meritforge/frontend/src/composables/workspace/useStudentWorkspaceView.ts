import { computed, onMounted, reactive, ref, watch } from 'vue'

import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'
import { useStudentWorkspaceStore } from '@/stores/studentWorkspace'

export function useStudentWorkspaceView() {
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
  const catalogPage = ref(1)
  const annotationsPage = ref(1)
  const bookshelfPage = ref(1)
  const milestonesPage = ref(1)
  const CATALOG_PAGE_SIZE = 8
  const ANNOTATIONS_PAGE_SIZE = 5
  const BOOKSHELF_PAGE_SIZE = 6
  const MILESTONES_PAGE_SIZE = 6
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
  const catalogPageCount = computed(() => Math.max(1, Math.ceil(filteredContent.value.length / CATALOG_PAGE_SIZE)))
  const pagedFilteredContent = computed(() => {
    const start = (catalogPage.value - 1) * CATALOG_PAGE_SIZE
    return filteredContent.value.slice(start, start + CATALOG_PAGE_SIZE)
  })
  const annotationsPageCount = computed(() => Math.max(1, Math.ceil(currentAnnotations.value.length / ANNOTATIONS_PAGE_SIZE)))
  const pagedAnnotations = computed(() => {
    const start = (annotationsPage.value - 1) * ANNOTATIONS_PAGE_SIZE
    return currentAnnotations.value.slice(start, start + ANNOTATIONS_PAGE_SIZE)
  })
  const bookshelfPageCount = computed(() => Math.max(1, Math.ceil(workspace.privateBookshelf.length / BOOKSHELF_PAGE_SIZE)))
  const pagedBookshelf = computed(() => {
    const start = (bookshelfPage.value - 1) * BOOKSHELF_PAGE_SIZE
    return workspace.privateBookshelf.slice(start, start + BOOKSHELF_PAGE_SIZE)
  })
  const milestonesPageCount = computed(() => Math.max(1, Math.ceil(workspace.milestones.length / MILESTONES_PAGE_SIZE)))
  const pagedMilestones = computed(() => {
    const start = (milestonesPage.value - 1) * MILESTONES_PAGE_SIZE
    return workspace.milestones.slice(start, start + MILESTONES_PAGE_SIZE)
  })

  const completionPercentage = (progressValue: number, targetValue: number) => {
    if (targetValue <= 0) return 0
    return Math.min(100, Math.round((progressValue / targetValue) * 100))
  }

  function isUuid(value: string) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
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
    const templateId = milestoneForm.milestoneTemplateId.trim()
    if (!templateId) {
      pageError.value = 'Please provide a milestone template ID before submitting progress.'
      return
    }
    if (!isUuid(templateId)) {
      pageError.value = 'Milestone template ID must be a valid UUID (for example: 123e4567-e89b-12d3-a456-426614174000).'
      return
    }
    try {
      await workspace.reportApplicationMilestone({
        applicationId: milestoneForm.applicationId,
        milestoneTemplateId: templateId,
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
      applyMessage.value = 'This job post is not ready for applications right now. Please try another listing.'
      return
    }

    if (!applyForm.coverLetter.trim()) {
      applyMessage.value = 'Please add a short cover letter so employers can understand your interest.'
      return
    }

    applyLoading.value = true
    applyMessage.value = ''
    try {
      const application = await workspace.applyToJobPost(currentContent.value.jobPostId, {
        coverLetter: applyForm.coverLetter || undefined
      })
      applyMessage.value = `Application sent successfully. Reference: ${application.id.slice(0, 8)}...`
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

  watch(filteredContent, () => {
    if (catalogPage.value > catalogPageCount.value) {
      catalogPage.value = catalogPageCount.value
    }
  })

  watch(currentAnnotations, () => {
    if (annotationsPage.value > annotationsPageCount.value) {
      annotationsPage.value = annotationsPageCount.value
    }
  })

  watch(
    () => workspace.privateBookshelf.length,
    () => {
      if (bookshelfPage.value > bookshelfPageCount.value) {
        bookshelfPage.value = bookshelfPageCount.value
      }
    }
  )

  watch(
    () => workspace.milestones.length,
    () => {
      if (milestonesPage.value > milestonesPageCount.value) {
        milestonesPage.value = milestonesPageCount.value
      }
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
      annotationsPage.value = 1
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

  return {
    workspace,
    playerEl,
    activeTab,
    contentFilter,
    annotationDraft,
    annotationSaving,
    annotationError,
    transcriptSelectionHost,
    selectedStartOffset,
    selectedEndOffset,
    selectedHighlightedText,
    searchQuery,
    searchResults,
    searching,
    pageError,
    videoLoadError,
    videoLoading,
    catalogPage,
    catalogPageCount,
    pagedFilteredContent,
    annotationsPage,
    annotationsPageCount,
    pagedAnnotations,
    bookshelfPage,
    bookshelfPageCount,
    pagedBookshelf,
    milestonesPage,
    milestonesPageCount,
    pagedMilestones,
    milestoneForm,
    applyForm,
    applyLoading,
    applyMessage,
    allTopics,
    filteredContent,
    currentContent,
    currentProgress,
    currentAnnotations,
    completionPercentage,
    onVideoPlay,
    onVideoTimeUpdate,
    skipVideo,
    onVideoLoaded,
    onVideoError,
    retryVideoLoad,
    submitMilestoneUpdate,
    applyToSelectedJob,
    saveAnnotation,
    captureSelectionFromTranscript
  }
}
