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

  it('loads applicant profiles and keeps consent-masked fields', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: [{ id: 'post-1' }] } as never)
      .mockResolvedValueOnce({
        data: [
          {
            id: 'app-1',
            job_post_id: 'post-1',
            applicant_id: '11111111-1111-4111-8111-111111111111',
            status: 'submitted',
            submitted_at: null,
            reviewed_at: null,
            created_at: new Date().toISOString()
          }
        ]
      } as never)
      .mockResolvedValueOnce({ data: [] } as never)
      .mockResolvedValueOnce({
        data: {
          id: '11111111-1111-4111-8111-111111111111',
          display_name: 'Student A',
          first_name: 'Student',
          last_name: 'A',
          email: null,
          phone_number: null,
          avatar_url: null
        }
      } as never)

    const store = useEmployerWorkspaceStore()
    await store.loadPosts()
    await store.loadSelectedPostDetails()

    expect(store.profileDisplayName('11111111-1111-4111-8111-111111111111')).toBe('Student A')
    expect(store.applicantProfiles['11111111-1111-4111-8111-111111111111']?.email).toBeNull()
    expect(store.profileErrors['11111111-1111-4111-8111-111111111111']).toBeUndefined()
  })

  it('handles denied profile fetch gracefully', async () => {
    vi.mocked(api.get)
      .mockResolvedValueOnce({ data: [{ id: 'post-1' }] } as never)
      .mockResolvedValueOnce({
        data: [
          {
            id: 'app-1',
            job_post_id: 'post-1',
            applicant_id: '11111111-1111-4111-8111-111111111111',
            status: 'submitted',
            submitted_at: null,
            reviewed_at: null,
            created_at: new Date().toISOString()
          }
        ]
      } as never)
      .mockResolvedValueOnce({ data: [] } as never)
      .mockRejectedValueOnce({
        isAxiosError: true,
        response: { data: { detail: 'User not found' } }
      } as never)

    const store = useEmployerWorkspaceStore()
    await store.loadPosts()
    await store.loadSelectedPostDetails()

    expect(store.applicantProfiles['11111111-1111-4111-8111-111111111111']).toBeNull()
    expect(store.profileErrors['11111111-1111-4111-8111-111111111111']).toBe('User not found')
    expect(store.profileDisplayName('11111111-1111-4111-8111-111111111111')).toBe('11111111...')
  })
})
