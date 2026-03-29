import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'

import { api } from '@/lib/api'
import { getProfileBackupKey } from '@/lib/profileBackup'
import { useAuthStore } from '@/stores/auth'

interface UserProfile {
  id: string
  email: string | null
  first_name: string | null
  last_name: string | null
  display_name: string | null
  bio: string | null
  avatar_url: string | null
  phone_number: string | null
  consent_contact_info_visible: boolean
  consent_photo_visible: boolean
  consent_analytics: boolean
  consent_data_portability: boolean
  created_at: string
  updated_at: string
}

interface ExportPayload {
  exported_at: string
  user: Record<string, unknown>
  cohorts: Array<Record<string, unknown>>
}

interface DeletionStatus {
  user_id: string
  is_marked_for_deletion: boolean
  deletion_requested_at: string
  scheduled_deletion_at: string
  reason: string
}

export const useProfileWorkspaceStore = defineStore('profile-workspace', () => {
  const auth = useAuthStore()
  const loading = ref(false)
  const profile = ref<UserProfile | null>(null)
  const consentForm = reactive({
    consent_contact_info_visible: false,
    consent_photo_visible: false,
    consent_analytics: false,
    consent_data_portability: false
  })

  function getActiveBackupKey() {
    const userId = profile.value?.id || auth.user?.id
    if (!userId) return null
    return getProfileBackupKey(userId)
  }

  function syncConsentForm() {
    if (!profile.value) return
    consentForm.consent_contact_info_visible = profile.value.consent_contact_info_visible
    consentForm.consent_photo_visible = profile.value.consent_photo_visible
    consentForm.consent_analytics = profile.value.consent_analytics
    consentForm.consent_data_portability = profile.value.consent_data_portability
  }

  async function loadProfile() {
    loading.value = true
    try {
      const { data } = await api.get<UserProfile>('/api/v1/users/me')
      profile.value = data
      syncConsentForm()
    } finally {
      loading.value = false
    }
  }

  async function saveConsentSettings() {
    const { data } = await api.patch<UserProfile>('/api/v1/users/me', {
      consent_contact_info_visible: consentForm.consent_contact_info_visible,
      consent_photo_visible: consentForm.consent_photo_visible,
      consent_analytics: consentForm.consent_analytics,
      consent_data_portability: consentForm.consent_data_portability
    })
    profile.value = data
    syncConsentForm()
  }

  async function exportFromServer() {
    const { data } = await api.get<ExportPayload>('/api/v1/users/me/export')
    return data
  }

  async function importToServer(payload: ExportPayload, source = 'local_fallback') {
    const user = payload.user || {}
    const { data } = await api.post<UserProfile>('/api/v1/users/me/import', {
      source,
      user: {
        first_name: user.first_name ?? null,
        last_name: user.last_name ?? null,
        display_name: user.display_name ?? null,
        bio: user.bio ?? null,
        avatar_url: user.avatar_url ?? null,
        phone_number: user.phone_number ?? null,
        consent_contact_info_visible: user.consent_contact_info_visible ?? null,
        consent_photo_visible: user.consent_photo_visible ?? null,
        consent_analytics: user.consent_analytics ?? null,
        consent_data_portability: user.consent_data_portability ?? null
      }
    })
    profile.value = data
    syncConsentForm()
  }

  async function markAccountForDeletion(reason: string) {
    const { data } = await api.post<DeletionStatus>('/api/v1/users/me/deletion/mark', { reason })
    return data
  }

  function saveLocalBackup(payload: ExportPayload) {
    const key = getActiveBackupKey()
    if (!key) return
    localStorage.setItem(key, JSON.stringify(payload))
  }

  function loadLocalBackup(): ExportPayload | null {
    const key = getActiveBackupKey()
    if (!key) return null
    const raw = localStorage.getItem(key)
    if (!raw) return null
    return JSON.parse(raw) as ExportPayload
  }

  function clearLocalBackup(userId: string | null | undefined) {
    if (!userId) return
    localStorage.removeItem(getProfileBackupKey(userId))
  }

  return {
    loading,
    profile,
    consentForm,
    loadProfile,
    saveConsentSettings,
    exportFromServer,
    importToServer,
    markAccountForDeletion,
    saveLocalBackup,
    loadLocalBackup,
    clearLocalBackup
  }
})
