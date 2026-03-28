import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn()
  }
}))

import { api } from '@/lib/api'
import { useEmployerWorkspaceStore } from '@/stores/employerWorkspace'

describe('employer workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.patch).mockReset()
  })

  it('loads posts and sets selected post id', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: [
        {
          id: 'post-1',
          content_id: '11111111-1111-4111-8111-111111111111',
          title: 'Backend Engineer',
          employer_name: 'MeritForge',
          location: 'Remote',
          employment_type: 'full_time',
          application_deadline: null,
          is_active: true,
          created_at: new Date().toISOString()
        }
      ]
    } as never)

    const store = useEmployerWorkspaceStore()
    await store.loadPosts()

    expect(vi.mocked(api.get)).toHaveBeenCalledWith('/api/v1/employer/job-posts')
    expect(store.posts).toHaveLength(1)
    expect(store.selectedPostId).toBe('post-1')
  })
})
