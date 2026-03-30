import axios from 'axios'

const configuredBaseURL = import.meta.env.VITE_API_URL
const baseURL = configuredBaseURL === undefined ? '' : configuredBaseURL

export const api = axios.create({
  baseURL,
  withCredentials: true,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

api.interceptors.request.use((config) => {
  const method = String(config.method || 'get').toLowerCase()
  if (!['post', 'put', 'patch'].includes(method)) {
    return config
  }

  const headers = (config.headers || {}) as Record<string, unknown>
  if (!headers['Idempotency-Key']) {
    headers['Idempotency-Key'] = generateIdempotencyKey()
  }
  config.headers = headers

  return config
})

let refreshPromise: Promise<void> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status
    const originalRequest = error.config as (typeof error.config & { _retry?: boolean }) | undefined

    if (!originalRequest || status !== 401 || originalRequest._retry) {
      throw error
    }

    const requestUrl = String(originalRequest.url || '')
    const isAuthEndpoint =
      requestUrl.includes('/api/v1/auth/login') ||
      requestUrl.includes('/api/v1/auth/register') ||
      requestUrl.includes('/api/v1/auth/logout') ||
      requestUrl.includes('/api/v1/auth/refresh')

    if (isAuthEndpoint) {
      throw error
    }

    originalRequest._retry = true

    try {
      if (!refreshPromise) {
        refreshPromise = api.post('/api/v1/auth/refresh').then(() => undefined).finally(() => {
          refreshPromise = null
        })
      }

      await refreshPromise
      return api.request(originalRequest)
    } catch {
      throw error
    }
  }
)
