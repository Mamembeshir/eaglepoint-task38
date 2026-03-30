import { beforeEach, describe, expect, it, vi } from 'vitest'

type Role = 'student' | 'employer_manager' | 'content_author' | 'reviewer' | 'system_administrator' | null

const authState = vi.hoisted(() => ({
  initialized: true,
  isAuthenticated: false,
  role: null as Role,
  refreshSession: vi.fn(async () => undefined)
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authState
}))

import router from '@/router'

describe('router guards', () => {
  beforeEach(async () => {
    authState.initialized = true
    authState.isAuthenticated = false
    authState.role = null
    authState.refreshSession.mockClear()
    await router.replace('/')
  })

  it('redirects unauthenticated users from /app to /login', async () => {
    await router.push('/app')
    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/app')
  })

  it('redirects authenticated guestOnly routes away from /login and /register', async () => {
    authState.isAuthenticated = true
    authState.role = 'student'

    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/app')

    await router.push('/register')
    expect(router.currentRoute.value.path).toBe('/app')
  })

  it('blocks student role from hiring/control/operations spaces', async () => {
    authState.isAuthenticated = true
    authState.role = 'student'

    await router.push('/app/hiring-space')
    expect(router.currentRoute.value.path).toBe('/app')

    await router.push('/app/control-space')
    expect(router.currentRoute.value.path).toBe('/app')

    await router.push('/app/operations')
    expect(router.currentRoute.value.path).toBe('/app')
  })

  it('allows proper role access to protected pages', async () => {
    authState.isAuthenticated = true
    authState.role = 'employer_manager'

    await router.push('/app/hiring-space')
    expect(router.currentRoute.value.path).toBe('/app/hiring-space')

    authState.role = 'system_administrator'
    await router.push('/app/operations')
    expect(router.currentRoute.value.path).toBe('/app/operations')
  })
})
