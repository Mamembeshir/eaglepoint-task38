import { describe, expect, it } from 'vitest'

import { api } from '@/lib/api'

describe('api client', () => {
  it('is configured for cookie-based auth and response interceptors', () => {
    expect(api.defaults.withCredentials).toBe(true)
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
    expect(api.interceptors.response.handlers.length).toBeGreaterThan(0)
    expect(api.interceptors.request.handlers.length).toBeGreaterThan(0)
  })

  it('adds Idempotency-Key for POST/PUT/PATCH requests', async () => {
    const requestHandler = api.interceptors.request.handlers[0]?.fulfilled
    expect(requestHandler).toBeTypeOf('function')

    const postConfig = await requestHandler?.({ method: 'post', headers: {} })
    const putConfig = await requestHandler?.({ method: 'put', headers: {} })
    const patchConfig = await requestHandler?.({ method: 'patch', headers: {} })

    expect(postConfig?.headers?.['Idempotency-Key']).toBeTruthy()
    expect(putConfig?.headers?.['Idempotency-Key']).toBeTruthy()
    expect(patchConfig?.headers?.['Idempotency-Key']).toBeTruthy()
  })

  it('reuses existing Idempotency-Key when already provided', async () => {
    const requestHandler = api.interceptors.request.handlers[0]?.fulfilled
    const config = await requestHandler?.({ method: 'patch', headers: { 'Idempotency-Key': 'existing-key' } })
    expect(config?.headers?.['Idempotency-Key']).toBe('existing-key')
  })
})
