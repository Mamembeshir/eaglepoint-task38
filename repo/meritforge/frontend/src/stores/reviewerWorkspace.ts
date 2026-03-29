import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/lib/api'
import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'

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
  const actionError = ref('')

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
    actionError.value = ''
    try {
      await api.post(`/api/v1/review-workflow/stages/${stageId}/decisions`, {
        decision: 'approve',
        comments: comments || null
      })
      await loadQueue()
      return true
    } catch (error) {
      actionError.value = getApiErrorMessage(error)
      logDevError(error)
      return false
    }
  }

  async function returnForRevision(stageId: string, comments: string) {
    const comment = comments.trim()
    actionError.value = ''
    if (comment.length < 20) {
      actionError.value = 'Provide at least 20 characters explaining why it must be revised.'
      return false
    }
    try {
      await api.post(`/api/v1/review-workflow/stages/${stageId}/decisions`, {
        decision: 'return_for_revision',
        comments: comment
      })
      await loadQueue()
      return true
    } catch (error) {
      actionError.value = getApiErrorMessage(error)
      logDevError(error)
      return false
    }
  }

  return {
    loading,
    queue,
    actionError,
    loadQueue,
    approve,
    returnForRevision
  }
})
