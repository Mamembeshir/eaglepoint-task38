import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useStudentWorkspaceStore } from '@/stores/studentWorkspace'

const videoId = '11111111-1111-4111-8111-111111111111'
const otherVideoId = '22222222-2222-4222-8222-222222222222'

describe('student workspace store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.get).mockReset()
    vi.mocked(api.post).mockReset()
    vi.mocked(api.delete).mockReset()

    const auth = useAuthStore()
    auth.user = {
      id: '33333333-3333-4333-8333-333333333333',
      email: 'student@example.com',
      first_name: null,
      last_name: null,
      display_name: null,
      role: 'student',
      created_at: new Date().toISOString()
    }
  })

  it('hydrates server state from backend APIs', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/api/v1/telemetry/progress') {
        return { data: [{ content_id: videoId, progress_seconds: 48 }] } as never
      }
      if (url === '/api/v1/users/me/export') {
        return { data: { cohorts: [{ id: 'c1', name: 'Alpha', slug: 'alpha' }] } } as never
      }
      if (url.includes('/api/v1/students/')) {
        return { data: [{ id: 'm1', milestone_name: 'Watch', source: 'automated', progress_value: 1, target_value: 2, achievement_date: null, updated_at: new Date().toISOString() }] } as never
      }
      if (url === '/api/v1/content') {
        return {
          data: [
            { id: videoId, title: 'Video A', content_type: 'video', media_url: '/a.mp4', metadata: { topic: 'career', duration_seconds: 120 }, summary: 'A' },
            { id: otherVideoId, title: 'Video B', content_type: 'video', media_url: '/b.mp4', metadata: { topic: 'portfolio', duration_seconds: 90 }, summary: 'B' }
          ]
        } as never
      }
      if (url === '/api/v1/bookmarks') {
        return { data: [{ id: 'b1', content_id: videoId, is_favorite: true }] } as never
      }
      return { data: [] } as never
    })

    const store = useStudentWorkspaceStore()
    await store.hydrateServerState()

    expect(store.videos).toHaveLength(2)
    expect(store.currentVideoId).toBe(videoId)
    expect(store.progressByVideo[videoId]).toBe(48)
    expect(store.bookmarkedVideoIds).toEqual([videoId])
    expect(store.favoriteVideoIds).toEqual([videoId])
  })

  it('sends telemetry and bookmark/favorite API calls', async () => {
    const getSpy = vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/api/v1/telemetry/progress') return { data: [{ content_id: videoId, progress_seconds: 0 }] } as never
      if (url === '/api/v1/users/me/export') return { data: { cohorts: [] } } as never
      if (url.includes('/api/v1/students/')) return { data: [] } as never
      if (url === '/api/v1/content') {
        return { data: [{ id: videoId, title: 'Video A', content_type: 'video', media_url: '/a.mp4', metadata: { topic: 'career', duration_seconds: 120 }, summary: 'A' }] } as never
      }
      if (url === '/api/v1/bookmarks') return { data: [] } as never
      return { data: [] } as never
    })

    const postSpy = vi.mocked(api.post).mockResolvedValue({ data: {} } as never)
    const deleteSpy = vi.mocked(api.delete).mockResolvedValue({ data: {} } as never)
    const localSetSpy = vi.spyOn(Storage.prototype, 'setItem')

    const store = useStudentWorkspaceStore()
    await store.hydrateServerState()
    await store.trackPlay(30)
    await store.toggleFavorite(videoId)
    await store.toggleBookmark(videoId)
    await store.toggleBookmark(videoId)

    expect(getSpy).toHaveBeenCalled()
    expect(postSpy).toHaveBeenCalledWith('/api/v1/telemetry/events', expect.objectContaining({ event_type: 'play', content_id: videoId }))
    expect(postSpy).toHaveBeenCalledWith('/api/v1/bookmarks', expect.objectContaining({ content_id: videoId, is_favorite: true }))
    expect(deleteSpy).toHaveBeenCalledWith(`/api/v1/bookmarks/${videoId}`)
    expect(localSetSpy).not.toHaveBeenCalled()
  })

  it('posts annotation with selected cohort and expected payload', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} } as never)
    vi.mocked(api.get).mockResolvedValue({ data: [] } as never)

    const store = useStudentWorkspaceStore()
    store.selectedVisibility = 'cohort'
    store.selectedCohortId = 'cohort-9'

    await store.addAnnotation(videoId, 'Need follow-up', {
      startOffset: 0,
      endOffset: 14,
      highlightedText: 'Need follow-up'
    })

    expect(vi.mocked(api.post)).toHaveBeenCalledWith('/api/v1/annotations', {
      content_id: videoId,
      visibility: 'cohort',
      cohort_id: 'cohort-9',
      start_offset: 0,
      end_offset: 14,
      annotation_text: 'Need follow-up',
      highlighted_text: 'Need follow-up',
      tags: []
    })
  })
})
