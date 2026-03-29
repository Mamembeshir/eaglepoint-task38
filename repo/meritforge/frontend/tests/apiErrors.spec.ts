import { describe, expect, it } from 'vitest'

import { GENERIC_ERROR_MESSAGE, getApiErrorMessage } from '@/lib/apiErrors'

describe('getApiErrorMessage', () => {
  it('returns detail when API provides a string message', () => {
    const message = getApiErrorMessage({
      isAxiosError: true,
      response: {
        data: {
          detail: 'Invalid credentials'
        }
      }
    })

    expect(message).toBe('Invalid credentials')
  })

  it('returns first validation detail line for pydantic-style array', () => {
    const message = getApiErrorMessage({
      isAxiosError: true,
      response: {
        data: {
          detail: [
            {
              loc: ['body', 'email'],
              msg: 'value is not a valid email address'
            }
          ]
        }
      }
    })

    expect(message).toBe('body.email: value is not a valid email address')
  })

  it('returns generic fallback when response detail is missing', () => {
    const message = getApiErrorMessage({
      isAxiosError: true,
      response: {
        data: {}
      }
    })

    expect(message).toBe(GENERIC_ERROR_MESSAGE)
  })

  it('returns generic fallback for non-axios errors', () => {
    const message = getApiErrorMessage(new Error('boom'))
    expect(message).toBe(GENERIC_ERROR_MESSAGE)
  })
})
