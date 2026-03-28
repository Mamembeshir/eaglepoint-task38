<script setup lang="ts">
import { computed } from 'vue'

import { cn } from '@/lib/utils'

interface Props {
  modelValue?: string
  placeholder?: string
  rows?: number
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  rows: 3
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const classes = computed(() =>
  cn(
    'flex min-h-[90px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
    props.class
  )
)
</script>

<template>
  <textarea
    :rows="rows"
    :placeholder="placeholder"
    :class="classes"
    :value="modelValue"
    @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
  />
</template>
