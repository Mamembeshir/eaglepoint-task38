import { api } from '@/lib/api'

export async function confirmStepUp(password: string) {
  await api.post('/api/v1/auth/step-up', { password: password.trim() })
}
