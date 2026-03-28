import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/lib/api'

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
    await api.post('/api/v1/content/submissions', payload)
    await loadSubmissions()
  }

  return {
    loading,
    submissions,
    loadSubmissions,
    submitContent
  }
})
