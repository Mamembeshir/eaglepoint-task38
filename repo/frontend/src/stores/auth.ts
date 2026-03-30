import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/lib/api'
import { getProfileBackupKey } from '@/lib/profileBackup'
import type { AppRole, AuthResponse, AuthUser, LoginPayload, RegisterPayload } from '@/types/auth'

const AUTH_USER_STORAGE_KEY = 'meritforge.auth.user'

function readStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(AUTH_USER_STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

function writeStoredUser(user: AuthUser | null) {
  if (!user) {
    localStorage.removeItem(AUTH_USER_STORAGE_KEY)
    return
  }
  localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user))
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(readStoredUser())
  const loading = ref(false)
  const initialized = ref(Boolean(user.value))

  const isAuthenticated = computed(() => Boolean(user.value))
  const role = computed<AppRole | null>(() => user.value?.role ?? null)

  async function login(payload: LoginPayload) {
    loading.value = true
    try {
      const { data } = await api.post<AuthResponse>('/api/v1/auth/login', payload)
      user.value = data.user
      writeStoredUser(data.user)
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
      writeStoredUser(data.user)
      return data
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    const currentUserId = user.value?.id ?? null
    loading.value = true
    try {
      await api.post('/api/v1/auth/logout')
    } finally {
      if (currentUserId) {
        localStorage.removeItem(getProfileBackupKey(currentUserId))
      }
      user.value = null
      writeStoredUser(null)
      loading.value = false
    }
  }

  async function refreshSession() {
    if (initialized.value) return
    try {
      const { data } = await api.get<AuthUser>('/api/v1/users/me')
      user.value = data
      writeStoredUser(data)
    } catch {
      user.value = null
      writeStoredUser(null)
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
