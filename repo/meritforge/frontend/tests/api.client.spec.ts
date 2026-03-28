import { describe, expect, it } from 'vitest'

import { api } from '@/lib/api'

describe('api client', () => {
  it('is configured for cookie-based auth and response interceptors', () => {
    expect(api.defaults.withCredentials).toBe(true)
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
    expect(api.interceptors.response.handlers.length).toBeGreaterThan(0)
  })
})
