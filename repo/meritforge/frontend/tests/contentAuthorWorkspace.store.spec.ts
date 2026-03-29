import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn()
  }
}))

import { api } from '@/lib/api'
import { useContentAuthorWorkspaceStore } from '@/stores/contentAuthorWorkspace'

describe('content author workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
  })

  it('validates payload and does not call API when invalid', async () => {
    const store = useContentAuthorWorkspaceStore()

    const missingTitle = await store.submitContent({
      content_type: 'article',
      title: '   ',
      body: 'Body'
    })

    const missingBody = await store.submitContent({
      content_type: 'article',
      title: 'Valid title',
      body: '   '
    })

    const missingMedia = await store.submitContent({
      content_type: 'video',
      title: 'Video title',
      media_url: '   '
    })

    expect(missingTitle).toBe(false)
    expect(missingBody).toBe(false)
    expect(missingMedia).toBe(false)
    expect(vi.mocked(api.post)).not.toHaveBeenCalled()
    expect(store.submitError).toBe('Media URL is required for video submissions.')
  })

  it('sets submitError when submission API call fails', async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      isAxiosError: true,
      response: {
        data: {
          detail: 'Submission failed due to policy.'
        }
      }
    })

    const store = useContentAuthorWorkspaceStore()
    const ok = await store.submitContent({
      content_type: 'article',
      title: 'Policy-sensitive item',
      body: 'Some body'
    })

    expect(ok).toBe(false)
    expect(store.submitError).toBe('Submission failed due to policy.')
    expect(store.loading).toBe(false)
  })
})
