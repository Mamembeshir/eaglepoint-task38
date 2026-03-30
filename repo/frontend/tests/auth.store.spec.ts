import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn()
  }
}))

import { api } from '@/lib/api'
import { getProfileBackupKey } from '@/lib/profileBackup'
import { useAuthStore } from '@/stores/auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api.post).mockReset()
    vi.mocked(api.get).mockReset()
  })

  it('populates auth state after login and clears it on logout', async () => {
    const store = useAuthStore()
    const user = {
      id: 'f1f9a99a-8068-4f0f-a85d-e3ee1f154a8d',
      email: 'student@example.com',
      first_name: null,
      last_name: null,
      display_name: null,
      role: 'student' as const,
      created_at: new Date().toISOString()
    }

    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        user,
        access_token_expires_at: new Date().toISOString(),
        refresh_token_expires_at: new Date().toISOString(),
        token_type: 'bearer'
      }
    } as never)

    await store.login({ email: 'student@example.com', password: 'Password123' })
    expect(store.isAuthenticated).toBe(true)
    expect(store.user?.email).toBe('student@example.com')

    localStorage.setItem(getProfileBackupKey(user.id), '{"backup":true}')

    vi.mocked(api.post).mockResolvedValueOnce({ data: {} } as never)
    await store.logout()

    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
    expect(vi.mocked(api.post)).toHaveBeenLastCalledWith('/api/v1/auth/logout')
    expect(localStorage.getItem(getProfileBackupKey(user.id))).toBeNull()
  })
})
