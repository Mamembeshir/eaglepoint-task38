<script setup lang="ts">
import { Download, HardDriveDownload, Upload } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UITextarea } from '@/components/ui/textarea'
import { getApiErrorMessage, logDevError } from '@/lib/apiErrors'
import { confirmStepUp } from '@/lib/stepUp'
import { useProfileWorkspaceStore } from '@/stores/profileWorkspace'
import StepUpConfirmationModal from '@/components/app/StepUpConfirmationModal.vue'

const store = useProfileWorkspaceStore()
const importJsonText = ref('')
const message = ref('')
const deletionReason = ref('')
const stepUpOpen = ref(false)
const stepUpLoading = ref(false)
const stepUpError = ref('')

function downloadJson(payload: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

async function exportData() {
  const data = await store.exportFromServer()
  importJsonText.value = JSON.stringify(data, null, 2)
  store.saveLocalBackup(data)
  downloadJson(data, `meritforge-profile-export-${new Date().toISOString().slice(0, 10)}.json`)
  message.value = 'Export completed. JSON downloaded and local fallback backup updated.'
}

async function saveConsents() {
  await store.saveConsentSettings()
  message.value = 'Consent preferences saved.'
}

async function importData() {
  try {
    const parsed = JSON.parse(importJsonText.value)
    await store.importToServer(parsed, 'local_fallback')
    message.value = 'Import completed and profile updated.'
  } catch (error) {
    message.value = getApiErrorMessage(error)
    logDevError(error)
  }
}

function requestDeletion() {
  if (!deletionReason.value.trim()) {
    message.value = 'Provide a deletion reason before confirming.'
    return
  }
  stepUpError.value = ''
  stepUpOpen.value = true
}

function cancelStepUp() {
  stepUpOpen.value = false
  stepUpError.value = ''
}

async function confirmDeletion(password: string) {
  stepUpLoading.value = true
  stepUpError.value = ''
  try {
    await confirmStepUp(password)
    await store.markAccountForDeletion(deletionReason.value.trim())
    message.value = 'Your account has been marked for deletion.'
    deletionReason.value = ''
    cancelStepUp()
  } catch (error) {
    stepUpError.value = getApiErrorMessage(error)
    logDevError(error)
  } finally {
    stepUpLoading.value = false
  }
}

function onImportFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    importJsonText.value = String(reader.result || '')
  }
  reader.readAsText(file)
}

function loadLocalBackup() {
  const backup = store.loadLocalBackup()
  if (!backup) {
    message.value = 'No local fallback backup found on this device.'
    return
  }
  importJsonText.value = JSON.stringify(backup, null, 2)
  message.value = 'Loaded local fallback backup from browser storage.'
}

onMounted(async () => {
  await store.loadProfile()
})
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Privacy & Portability</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Profile Consent & Local Transfer</h2>
      <p class="mt-1 text-sm text-muted-foreground">Privacy controls and offline-friendly export/import to move data across devices without internet dependencies.</p>
    </header>

    <UICard class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle>Consent Controls</UICardTitle>
        <UICardDescription>Choose what personal data is visible and what processing is allowed.</UICardDescription>
      </UICardHeader>
      <UICardContent class="space-y-3">
        <label class="flex items-center gap-2 text-sm">
          <input v-model="store.consentForm.consent_contact_info_visible" type="checkbox" />
          Share contact info (email and phone) with other users
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="store.consentForm.consent_photo_visible" type="checkbox" />
          Share profile photo publicly
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="store.consentForm.consent_analytics" type="checkbox" />
          Allow analytics processing for product improvements
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="store.consentForm.consent_data_portability" type="checkbox" />
          Allow local export/import portability workflows
        </label>
        <UIButton class="w-full sm:w-auto" @click="saveConsents">Save Consent Settings</UIButton>
      </UICardContent>
    </UICard>

    <UICard class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle>Local Export / Import</UICardTitle>
        <UICardDescription>Use JSON files as a fallback multi-device transfer path inside offline or intranet environments.</UICardDescription>
      </UICardHeader>
      <UICardContent class="space-y-3">
        <div class="flex flex-wrap gap-2">
          <UIButton class="gap-2" @click="exportData">
            <Download class="h-4 w-4" />
            Export JSON
          </UIButton>
          <UIButton variant="outline" class="gap-2" @click="loadLocalBackup">
            <HardDriveDownload class="h-4 w-4" />
            Load Local Backup
          </UIButton>
          <label class="inline-flex cursor-pointer items-center gap-2 rounded-md border border-input px-3 py-2 text-sm">
            <Upload class="h-4 w-4" />
            Import File
            <input type="file" accept="application/json" class="hidden" @change="onImportFileChange" />
          </label>
        </div>
        <UITextarea v-model="importJsonText" :rows="12" placeholder="Paste exported JSON here or import a file..." />
        <UIButton class="w-full sm:w-auto" :disabled="!importJsonText" @click="importData">Apply Import to This Account</UIButton>
      </UICardContent>
    </UICard>

    <UICard class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle>Sensitive Actions</UICardTitle>
        <UICardDescription>Account deletion requires step-up confirmation.</UICardDescription>
      </UICardHeader>
      <UICardContent class="space-y-3">
        <UITextarea v-model="deletionReason" :rows="3" placeholder="Reason for deleting your account" />
        <UIButton variant="outline" class="w-full sm:w-auto" @click="requestDeletion">Mark Account for Deletion</UIButton>
      </UICardContent>
    </UICard>

    <p v-if="message" class="text-sm text-muted-foreground">{{ message }}</p>

    <StepUpConfirmationModal
      :open="stepUpOpen"
      title="Confirm Account Deletion"
      description="Re-enter your password to mark this account for deletion."
      confirm-label="Confirm deletion"
      :loading="stepUpLoading"
      :error-message="stepUpError"
      @cancel="cancelStepUp"
      @confirm="confirmDeletion"
    />
  </section>
</template>
