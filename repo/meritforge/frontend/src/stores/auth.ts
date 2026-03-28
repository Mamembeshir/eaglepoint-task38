import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/lib/api'
import type { AppRole, AuthResponse, AuthUser, LoginPayload, RegisterPayload } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const loading = ref(false)
  const initialized = ref(false)

  const isAuthenticated = computed(() => Boolean(user.value))
  const role = computed<AppRole | null>(() => user.value?.role ?? null)

  async function login(payload: LoginPayload) {
    loading.value = true
    try {
      const { data } = await api.post<AuthResponse>('/api/v1/auth/login', payload)
      user.value = data.user
      return data
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload) {
    loading.value = true
    try {
      const { data } = await api.post<AuthResponse>('/api/v1/auth/register', {
        email: payload.username.trim(),
        password: payload.password
      })
      user.value = data.user
      return data
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      await api.post('/api/v1/auth/logout')
    } finally {
      user.value = null
      loading.value = false
    }
  }

  async function refreshSession() {
    if (initialized.value) return
    try {
      const { data } = await api.get<AuthUser>('/api/v1/users/me')
      user.value = data
    } catch {
      user.value = null
    } finally {
      initialized.value = true
    }
  }

  return {
    user,
    loading,
    initialized,
    isAuthenticated,
    role,
    login,
    register,
    logout,
    refreshSession
  }
})
