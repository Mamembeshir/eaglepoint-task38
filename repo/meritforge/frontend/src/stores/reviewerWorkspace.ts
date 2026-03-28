import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/lib/api'

interface ReviewQueueItem {
  stage_id: string
  content_id: string
  title: string
  content_type: string
  status: string
  stage_name: string
  stage_order: number
  is_parallel: boolean
  required_distinct_reviewers: number
  current_distinct_approvers: number
  latest_comment: string | null
  updated_at: string
}

export const useReviewerWorkspaceStore = defineStore('reviewer-workspace', () => {
  const loading = ref(false)
  const queue = ref<ReviewQueueItem[]>([])

  async function loadQueue() {
    loading.value = true
    try {
      const { data } = await api.get<ReviewQueueItem[]>('/api/v1/review-workflow/queue')
      queue.value = data
    } finally {
      loading.value = false
    }
  }

  async function approve(stageId: string, comments?: string) {
    await api.post(`/api/v1/review-workflow/stages/${stageId}/decisions`, {
      decision: 'approve',
      comments: comments || null
    })
    await loadQueue()
  }

  async function returnForRevision(stageId: string, comments: string) {
    const comment = comments.trim()
    const ensured = comment.length >= 20 ? comment : `${comment} ${'Please revise and resubmit with required corrections.'}`
    await api.post(`/api/v1/review-workflow/stages/${stageId}/decisions`, {
      decision: 'return_for_revision',
      comments: ensured
    })
    await loadQueue()
  }

  return {
    loading,
    queue,
    loadQueue,
    approve,
    returnForRevision
  }
})
