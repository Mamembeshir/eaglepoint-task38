<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { UIButton } from '@/components/ui/button'
import { UIInput } from '@/components/ui/input'

const props = withDefaults(defineProps<{
  open: boolean
  title?: string
  description?: string
  confirmLabel?: string
  loading?: boolean
  errorMessage?: string
}>(), {
  title: 'Confirm Sensitive Action',
  description: 'For security, re-enter your password to continue.',
  confirmLabel: 'Confirm',
  loading: false,
  errorMessage: ''
})

const emit = defineEmits<{
  (e: 'confirm', password: string): void
  (e: 'cancel'): void
}>()

const password = ref('')

const canSubmit = computed(() => password.value.trim().length >= 8 && !props.loading)

function clearLocalState() {
  password.value = ''
}

function onCancel() {
  clearLocalState()
  emit('cancel')
}

function onConfirm() {
  const raw = password.value
  emit('confirm', raw)
  clearLocalState()
}

watch(
  () => props.open,
  (isOpen) => {
    if (!isOpen) {
      clearLocalState()
    }
  }
)
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 px-4">
    <div class="w-full max-w-md rounded-xl border border-border/70 bg-card p-5 shadow-2xl">
      <h3 class="text-lg font-semibold">{{ title }}</h3>
      <p class="mt-1 text-sm text-muted-foreground">{{ description }}</p>

      <div class="mt-4 space-y-2">
        <label class="text-sm font-medium">Password</label>
        <UIInput v-model="password" type="password" autocomplete="current-password" placeholder="Re-enter password" @keyup.enter="canSubmit && onConfirm()" />
      </div>

      <p v-if="errorMessage" class="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
        {{ errorMessage }}
      </p>

      <div class="mt-4 flex justify-end gap-2">
        <UIButton variant="outline" :disabled="loading" @click="onCancel">Cancel</UIButton>
        <UIButton :disabled="!canSubmit" @click="onConfirm">{{ loading ? 'Confirming...' : confirmLabel }}</UIButton>
      </div>
    </div>
  </div>
</template>
