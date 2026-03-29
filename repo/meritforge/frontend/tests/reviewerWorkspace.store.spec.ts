import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

import { api } from '@/lib/api'
import { useReviewerWorkspaceStore } from '@/stores/reviewerWorkspace'

describe('reviewer workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
  })

  it('does not pad return-for-revision comments and rejects short comments', async () => {
    const store = useReviewerWorkspaceStore()

    const shortResult = await store.returnForRevision('stage-1', 'too short')
    expect(shortResult).toBe(false)
    expect(store.actionError).toContain('at least 20 characters')
    expect(vi.mocked(api.post)).not.toHaveBeenCalled()

    vi.mocked(api.post).mockResolvedValueOnce({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValue({ data: [] } as never)

    const comment = 'Please revise tone and add source citations.'
    const okResult = await store.returnForRevision('stage-1', `  ${comment}  `)

    expect(okResult).toBe(true)
    expect(vi.mocked(api.post)).toHaveBeenCalledWith('/api/v1/review-workflow/stages/stage-1/decisions', {
      decision: 'return_for_revision',
      comments: comment
    })
    expect(comment).not.toContain('Please revise and resubmit with required corrections.')
  })
})
