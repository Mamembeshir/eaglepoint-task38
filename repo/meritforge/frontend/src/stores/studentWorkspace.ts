import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/lib/api'
import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'
import { useAuthStore } from '@/stores/auth'
import { isUuid, mapContentToVideo } from '@/stores/workspace/studentWorkspace.helpers'
import type {
  AnnotationItem,
  AnnotationSelectionPayload,
  AnnotationVisibilitySelection,
  BookmarkItem,
  CareerVideo,
  CohortOption,
  ContentItem,
  Milestone,
  StudentApplication,
  TopicSubscriptionItem
} from '@/stores/workspace/studentWorkspace.types'

export const useStudentWorkspaceStore = defineStore('student-workspace', () => {
  const auth = useAuthStore()
  const loading = ref(false)
  const contents = ref<ContentItem[]>([])
  const videos = ref<CareerVideo[]>([])
  const currentVideoId = ref('')
  const favoriteVideoIds = ref<string[]>([])
  const bookmarkedVideoIds = ref<string[]>([])
  const subscribedTopics = ref<string[]>([])
  const progressByVideo = ref<Record<string, number>>({})
  const cohorts = ref<CohortOption[]>([])
  const milestones = ref<Milestone[]>([])
  const annotationsByVideo = ref<Record<string, AnnotationItem[]>>({})
  const applications = ref<StudentApplication[]>([])
  const selectedVisibility = ref<AnnotationVisibilitySelection>('private')
  const selectedCohortId = ref<string>('')
  const hydrateError = ref('')
  const searchError = ref('')
  const actionError = ref('')
  const annotationsError = ref('')

  const currentVideo = computed(() => videos.value.find((v) => v.id === currentVideoId.value) ?? videos.value[0])
  const privateBookshelf = computed(() => videos.value.filter((v) => bookmarkedVideoIds.value.includes(v.id)))
  const videoItems = computed(() => videos.value.filter((item) => item.contentType === 'video'))

  async function sendTelemetry(
    eventType: 'play' | 'skip' | 'favorite' | 'search' | 'job_application',
    contentId: string | null | undefined,
    eventData: Record<string, unknown>
  ) {
    if (!auth.isAuthenticated) return
    if (!isUuid(contentId)) {
      console.warn(`[telemetry] skipped ${eventType}: missing/invalid content_id`, contentId)
      return
    }
    try {
      await api.post('/api/v1/telemetry/events', {
        event_type: eventType,
        content_id: contentId,
        resource_type: 'student_video',
        resource_id: currentVideo.value?.id,
        event_data: eventData
      })
    } catch (error) {
      logDevError(error)
    }
  }

  async function hydrateServerState() {
    if (!auth.user) return
    hydrateError.value = ''
    loading.value = true
    try {
      const [progressRes, exportRes, milestoneRes, contentRes, bookmarksRes, subscriptionsRes, applicationsRes] = await Promise.all([
        api.get<Array<{ content_id: string; progress_seconds: number }>>('/api/v1/telemetry/progress'),
        api.get<{ cohorts: CohortOption[] }>('/api/v1/users/me/export'),
        api.get<Milestone[]>(`/api/v1/students/${auth.user.id}/milestones`),
        api.get<ContentItem[]>('/api/v1/content'),
        api.get<BookmarkItem[]>('/api/v1/bookmarks').catch(() => ({ data: [] })),
        api.get<TopicSubscriptionItem[]>('/api/v1/users/me/topic-subscriptions').catch(() => ({ data: [] })),
        api.get<StudentApplication[]>('/api/v1/student/applications').catch(() => ({ data: [] }))
      ])

      const progressMap: Record<string, number> = {}
      for (const item of progressRes.data) {
        progressMap[item.content_id] = item.progress_seconds
      }
      progressByVideo.value = progressMap
      cohorts.value = exportRes.data.cohorts ?? []
      milestones.value = milestoneRes.data ?? []

      const backendItems = (contentRes.data ?? []).filter((item) => isUuid(item.id))
      contents.value = backendItems
      videos.value = backendItems.map((item) => mapContentToVideo(item))

      const bookmarkItems = bookmarksRes.data ?? []
      bookmarkedVideoIds.value = bookmarkItems.map((item) => item.content_id)
      favoriteVideoIds.value = bookmarkItems.filter((item) => item.is_favorite).map((item) => item.content_id)
      subscribedTopics.value = (subscriptionsRes.data ?? []).map((item) => item.topic)
      applications.value = applicationsRes.data ?? []

      if (!videos.value.find((video) => video.id === currentVideoId.value)) {
        currentVideoId.value = videoItems.value[0]?.id ?? videos.value[0]?.id ?? ''
      }
    } catch (error) {
      hydrateError.value = getApiErrorMessage(error)
      logDevError(error)
    } finally {
      loading.value = false
    }
  }

  async function loadAnnotations(contentId: string) {
    if (!isUuid(contentId)) return
    annotationsError.value = ''
    try {
      const { data } = await api.get<AnnotationItem[]>(`/api/v1/contents/${contentId}/annotations`)
      annotationsByVideo.value[contentId] = data
    } catch (error) {
      annotationsError.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  function selectVideo(videoId: string) {
    currentVideoId.value = videoId
  }

  async function trackPlay(positionSeconds: number) {
    if (!currentVideo.value || currentVideo.value.contentType !== 'video') return
    progressByVideo.value[currentVideo.value.id] = positionSeconds
    await sendTelemetry('play', currentVideo.value.id, {
      position_seconds: positionSeconds,
      duration_seconds: currentVideo.value.durationSeconds,
      topic: currentVideo.value.topic
    })
  }

  async function skipCurrentVideo() {
    if (!currentVideo.value || currentVideo.value.contentType !== 'video') return
    await sendTelemetry('skip', currentVideo.value.id, {
      skipped_video_id: currentVideo.value.id,
      topic: currentVideo.value.topic,
      resume_seconds: progressByVideo.value[currentVideo.value.id] ?? 0
    })
  }

  async function toggleFavorite(videoId: string) {
    actionError.value = ''
    const exists = favoriteVideoIds.value.includes(videoId)
    const previous = [...favoriteVideoIds.value]
    favoriteVideoIds.value = exists
      ? favoriteVideoIds.value.filter((id) => id !== videoId)
      : [...favoriteVideoIds.value, videoId]

    try {
      await api.post('/api/v1/bookmarks', {
        content_id: videoId,
        is_favorite: !exists
      })

      await sendTelemetry('favorite', videoId, {
        video_id: videoId,
        is_favorite: !exists
      })
    } catch (error) {
      favoriteVideoIds.value = previous
      actionError.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function toggleBookmark(videoId: string) {
    actionError.value = ''
    const previousBookmarked = [...bookmarkedVideoIds.value]
    const previousFavorite = [...favoriteVideoIds.value]
    const exists = bookmarkedVideoIds.value.includes(videoId)
    try {
      if (exists) {
        try {
          await api.delete(`/api/v1/bookmarks/${videoId}`)
        } catch {
          await api.post('/api/v1/bookmarks', {
            content_id: videoId,
            is_favorite: false,
            archived: true
          })
        }
        bookmarkedVideoIds.value = bookmarkedVideoIds.value.filter((id) => id !== videoId)
        favoriteVideoIds.value = favoriteVideoIds.value.filter((id) => id !== videoId)
        return
      }

      await api.post('/api/v1/bookmarks', {
        content_id: videoId,
        is_favorite: false
      })
      bookmarkedVideoIds.value = [...bookmarkedVideoIds.value, videoId]
    } catch (error) {
      bookmarkedVideoIds.value = previousBookmarked
      favoriteVideoIds.value = previousFavorite
      actionError.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function toggleTopicSubscription(topic: string) {
    actionError.value = ''
    const normalizedTopic = topic.trim().toLowerCase()
    if (!normalizedTopic) return
    const exists = subscribedTopics.value.includes(normalizedTopic)
    const previous = [...subscribedTopics.value]
    try {
      if (exists) {
        await api.delete('/api/v1/users/me/topic-subscriptions', { params: { topic: normalizedTopic } })
        subscribedTopics.value = subscribedTopics.value.filter((entry) => entry !== normalizedTopic)
      } else {
        await api.post('/api/v1/users/me/topic-subscriptions', { topic: normalizedTopic })
        subscribedTopics.value = [...subscribedTopics.value, normalizedTopic]
      }
      await sendTelemetry('search', currentVideo.value?.id, {
        action: 'topic_subscription',
        topic: normalizedTopic,
        subscribed: !exists
      })
    } catch (error) {
      subscribedTopics.value = previous
      actionError.value = getApiErrorMessage(error)
      logDevError(error)
    }
  }

  async function searchContent(query: string, contentType: 'video' | 'article' | 'job_announcement' = 'video', limit = 20) {
    return searchCatalog(query, contentType, limit)
  }

  async function searchCatalog(query: string, contentType?: 'video' | 'article' | 'job_announcement', limit = 20) {
    searchError.value = ''
    const normalizedQuery = query.trim()
    if (!normalizedQuery) return [] as CareerVideo[]
    try {
      const { data } = await api.get<ContentItem[]>('/api/v1/content', {
        params: {
          type: contentType,
          q: normalizedQuery,
          limit,
          offset: 0
        }
      })
      const results = (data ?? []).filter((item) => isUuid(item.id)).map((item) => mapContentToVideo(item))
      await sendTelemetry('search', results[0]?.id ?? currentVideo.value?.id, {
        query: normalizedQuery,
        result_count: results.length
      })
      return results
    } catch (error) {
      searchError.value = getApiErrorMessage(error)
      logDevError(error)
      return [] as CareerVideo[]
    }
  }

  async function addAnnotation(contentId: string, text: string, selection: AnnotationSelectionPayload) {
    if (!text.trim()) return
    if (selectedVisibility.value === 'cohort' && !selectedCohortId.value) {
      throw new Error('Please select a cohort for cohort visibility.')
    }
    if (selection.endOffset <= selection.startOffset || !selection.highlightedText.trim()) {
      throw new Error('Select text from transcript/content before adding a note.')
    }
    await api.post('/api/v1/annotations', {
      content_id: contentId,
      visibility: selectedVisibility.value,
      cohort_id: selectedVisibility.value === 'cohort' ? selectedCohortId.value || null : null,
      start_offset: selection.startOffset,
      end_offset: selection.endOffset,
      annotation_text: text.trim(),
      highlighted_text: selection.highlightedText,
      tags: []
    })
    await loadAnnotations(contentId)
  }

  async function reportApplicationMilestone(payload: {
    applicationId: string
    milestoneTemplateId: string
    milestoneName: string
    progressValue: number
    targetValue: number
    description?: string
  }) {
    actionError.value = ''
    try {
      await api.post(`/api/v1/student/applications/${payload.applicationId}/milestones`, {
        milestone_template_id: payload.milestoneTemplateId,
        milestone_name: payload.milestoneName,
        description: payload.description,
        progress_value: payload.progressValue,
        target_value: payload.targetValue
      })
      if (auth.user) {
        const { data } = await api.get<Milestone[]>(`/api/v1/students/${auth.user.id}/milestones`)
        milestones.value = data ?? []
      }
    } catch (error) {
      actionError.value = getApiErrorMessage(error)
      logDevError(error)
      throw error
    }
  }

  async function applyToJobPost(jobPostId: string, payload?: {
    coverLetter?: string
    resumeUrl?: string
    portfolioUrl?: string
  }) {
    actionError.value = ''
    try {
      const { data } = await api.post<StudentApplication>(`/api/v1/student/job-posts/${jobPostId}/applications`, {
        cover_letter: payload?.coverLetter,
        resume_url: payload?.resumeUrl,
        portfolio_url: payload?.portfolioUrl
      })

      const existing = applications.value.find((item) => item.id === data.id)
      if (!existing) {
        applications.value = [data, ...applications.value]
      }

      await sendTelemetry('job_application', currentVideo.value?.id, {
        job_post_id: jobPostId,
        application_id: data.id,
        status: data.status
      })
      return data
    } catch (error) {
      actionError.value = getApiErrorMessage(error)
      logDevError(error)
      throw error
    }
  }

  return {
    loading,
    contents,
    videos,
    currentVideo,
    currentVideoId,
    videoItems,
    favoriteVideoIds,
    bookmarkedVideoIds,
    subscribedTopics,
    progressByVideo,
    cohorts,
    milestones,
    applications,
    annotationsByVideo,
    selectedVisibility,
    selectedCohortId,
    privateBookshelf,
    hydrateError,
    searchError,
    actionError,
    annotationsError,
    hydrateServerState,
    loadAnnotations,
    selectVideo,
    trackPlay,
    skipCurrentVideo,
    toggleFavorite,
    toggleBookmark,
    toggleTopicSubscription,
    searchContent,
    searchCatalog,
    addAnnotation,
    reportApplicationMilestone,
    applyToJobPost
  }
})
