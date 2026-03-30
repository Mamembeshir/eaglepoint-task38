import axios from 'axios'

const GENERIC_ERROR_MESSAGE = 'Something went wrong. Please try again.'

function getDetailFromArray(detail: unknown[]): string | null {
  const first = detail[0]
  if (!first || typeof first !== 'object') return null

  const record = first as { msg?: unknown; loc?: unknown }
  const msg = typeof record.msg === 'string' ? record.msg.trim() : ''
  const loc = Array.isArray(record.loc)
    ? record.loc.map((value) => String(value)).join('.')
    : ''

  if (loc && msg) return `${loc}: ${msg}`
  if (msg) return msg
  if (loc) return loc
  return null
}

export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      const trimmed = detail.trim()
      if (trimmed) return trimmed
    }

    if (Array.isArray(detail)) {
      const fromArray = getDetailFromArray(detail)
      if (fromArray) return fromArray
    }
  }

  return GENERIC_ERROR_MESSAGE
}

export function logDevError(error: unknown) {
  if (import.meta.env.DEV) {
    console.error(error)
  }
}

export { GENERIC_ERROR_MESSAGE }
