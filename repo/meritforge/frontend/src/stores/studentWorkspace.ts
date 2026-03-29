import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/lib/api'
import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'
import { useAuthStore } from '@/stores/auth'

type AnnotationVisibility = 'private' | 'cohort' | 'public'
type AnnotationVisibilitySelection = 'private' | 'cohort'

interface CareerVideo {
  id: string
  title: string
  topic: string
  durationSeconds: number
  summary: string
  streamUrl: string
  poster: string
  contentType: 'video' | 'article' | 'job_announcement'
}

interface ContentItem {
  id: string
  title: string
  content_type: 'video' | 'article' | 'job_announcement'
  media_url?: string | null
  metadata?: Record<string, unknown> | null
  summary?: string | null
}

interface CohortOption {
  id: string
  name: string
  slug: string
}

interface Milestone {
  id: string
  milestone_name: string
  source: string
  progress_value: number
  target_value: number
  achievement_date: string | null
  updated_at: string
}

interface AnnotationItem {
  id: string
  annotation_text: string | null
  visibility: AnnotationVisibility
  cohort_id: string | null
  updated_at: string
}

interface BookmarkItem {
  id: string
  content_id: string
  is_favorite: boolean
}

interface TopicSubscriptionItem {
  id: string
  topic: string
  created_at: string
}

interface AnnotationSelectionPayload {
  startOffset: number
  endOffset: number
  highlightedText: string
}

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
  const selectedVisibility = ref<AnnotationVisibilitySelection>('private')
  const selectedCohortId = ref<string>('')
  const hydrateError = ref('')
  const searchError = ref('')
  const actionError = ref('')
  const annotationsError = ref('')

  const currentVideo = computed(() => videos.value.find((v) => v.id === currentVideoId.value) ?? videos.value[0])
  const privateBookshelf = computed(() => videos.value.filter((v) => bookmarkedVideoIds.value.includes(v.id)))

  function mapContentToVideo(item: ContentItem): CareerVideo {
    const metadata = (item.metadata ?? {}) as Record<string, unknown>
    const topic = typeof metadata.topic === 'string' ? metadata.topic : item.content_type.replace('_', '-')
    const durationSeconds = typeof metadata.duration_seconds === 'number'
      ? metadata.duration_seconds
      : Number(metadata.duration_seconds) || 0
    const streamUrl = item.media_url || (typeof metadata.stream_url === 'string' ? metadata.stream_url : '')
    const poster = typeof metadata.poster_url === 'string' ? metadata.poster_url : ''
    const summary = item.summary || (typeof metadata.summary === 'string' ? metadata.summary : '')

    return {
      id: item.id,
      title: item.title,
      topic,
      durationSeconds,
      summary,
      streamUrl,
      poster,
      contentType: item.content_type
    }
  }

  function isUuid(value: string | null | undefined) {
    if (!value) return false
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
  }

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
      const [progressRes, exportRes, milestoneRes, contentRes, bookmarksRes, subscriptionsRes] = await Promise.all([
        api.get<Array<{ content_id: string; progress_seconds: number }>>('/api/v1/telemetry/progress'),
        api.get<{ cohorts: CohortOption[] }>('/api/v1/users/me/export'),
        api.get<Milestone[]>(`/api/v1/students/${auth.user.id}/milestones`),
        api.get<ContentItem[]>('/api/v1/content', { params: { type: 'video' } }),
        api.get<BookmarkItem[]>('/api/v1/bookmarks').catch(() => ({ data: [] })),
        api.get<TopicSubscriptionItem[]>('/api/v1/users/me/topic-subscriptions').catch(() => ({ data: [] }))
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

      if (!videos.value.find((video) => video.id === currentVideoId.value)) {
        currentVideoId.value = videos.value[0]?.id ?? ''
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
    if (!currentVideo.value) return
    progressByVideo.value[currentVideo.value.id] = positionSeconds
    await sendTelemetry('play', currentVideo.value.id, {
      position_seconds: positionSeconds,
      duration_seconds: currentVideo.value.durationSeconds,
      topic: currentVideo.value.topic
    })
  }

  async function skipCurrentVideo() {
    if (!currentVideo.value) return
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

  return {
    loading,
    contents,
    videos,
    currentVideo,
    currentVideoId,
    favoriteVideoIds,
    bookmarkedVideoIds,
    subscribedTopics,
    progressByVideo,
    cohorts,
    milestones,
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
    addAnnotation
  }
})
