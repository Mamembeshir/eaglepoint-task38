import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/lib/api'
import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'

type ContentType = 'article' | 'video' | 'job_announcement'

interface ReviewComment {
  stage_name: string
  decision: string
  reviewer_id: string | null
  comments: string | null
  created_at: string
}

interface Submission {
  content_id: string
  title: string
  content_type: ContentType
  status: string
  risk_score: number | null
  risk_grade: string | null
  review_comments: ReviewComment[]
  created_at: string
}

export const useContentAuthorWorkspaceStore = defineStore('content-author-workspace', () => {
  const loading = ref(false)
  const submissions = ref<Submission[]>([])
  const submitError = ref('')

  function validateSubmission(payload: {
    content_type: ContentType
    title: string
    body?: string
    media_url?: string
  }): string | null {
    if (!payload.title.trim()) {
      return 'Title is required.'
    }
    if ((payload.content_type === 'article' || payload.content_type === 'job_announcement') && !(payload.body ?? '').trim()) {
      return 'Body is required for article and job announcement submissions.'
    }
    if (payload.content_type === 'video' && !(payload.media_url ?? '').trim()) {
      return 'Media URL is required for video submissions.'
    }
    return null
  }

  async function loadSubmissions() {
    loading.value = true
    try {
      const { data } = await api.get<Submission[]>('/api/v1/content/submissions/mine')
      submissions.value = data
    } finally {
      loading.value = false
    }
  }

  async function submitContent(payload: {
    content_type: ContentType
    title: string
    body?: string
    media_url?: string
    metadata?: Record<string, unknown>
  }) {
    submitError.value = ''
    const validationError = validateSubmission(payload)
    if (validationError) {
      submitError.value = validationError
      return false
    }

    loading.value = true
    try {
      await api.post('/api/v1/content/submissions', {
        ...payload,
        title: payload.title.trim(),
        body: payload.body?.trim() || undefined,
        media_url: payload.media_url?.trim() || undefined
      })
      await loadSubmissions()
      return true
    } catch (error) {
      submitError.value = getApiErrorMessage(error)
      logDevError(error)
      return false
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    submissions,
    submitError,
    loadSubmissions,
    submitContent,
    validateSubmission
  }
})
