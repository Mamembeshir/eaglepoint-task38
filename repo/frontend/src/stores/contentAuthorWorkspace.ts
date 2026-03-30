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

interface SubmissionStage {
  stage_name: string
  stage_order: number
  is_required: boolean
  is_parallel: boolean
  is_completed: boolean
}

interface Submission {
  content_id: string
  title: string
  content_type: ContentType
  status: string
  risk_score: number | null
  risk_grade: string | null
  workflow_stage_count: number
  stages: SubmissionStage[]
  review_comments: ReviewComment[]
  created_at: string
}

interface SubmissionCreateResponse {
  content_id: string
}

interface SubmitResult {
  ok: boolean
  contentId?: string
}

export const useContentAuthorWorkspaceStore = defineStore('content-author-workspace', () => {
  const loading = ref(false)
  const submissions = ref<Submission[]>([])
  const submitError = ref('')

  function isValidHttpUrl(value: string): boolean {
    try {
      const parsed = new URL(value)
      return parsed.protocol === 'http:' || parsed.protocol === 'https:'
    } catch {
      return false
    }
  }

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
    if (payload.content_type === 'video' && payload.media_url && !isValidHttpUrl(payload.media_url.trim())) {
      return 'Media URL must start with http:// or https:// and point to a direct media file.'
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
  }): Promise<SubmitResult> {
    submitError.value = ''
    const validationError = validateSubmission(payload)
    if (validationError) {
      submitError.value = validationError
      return { ok: false }
    }

    loading.value = true
    try {
      const { data } = await api.post<SubmissionCreateResponse>('/api/v1/content/submissions', {
        ...payload,
        title: payload.title.trim(),
        body: payload.body?.trim() || undefined,
        media_url: payload.media_url?.trim() || undefined
      })
      await loadSubmissions()
      return { ok: true, contentId: data?.content_id }
    } catch (error) {
      submitError.value = getApiErrorMessage(error)
      logDevError(error)
      return { ok: false }
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
