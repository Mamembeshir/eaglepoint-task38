<script setup lang="ts">
import { Moon, Sun, Monitor } from 'lucide-vue-next'

import { UIButton } from '@/components/ui/button'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()

function cycleTheme() {
  if (theme.mode === 'light') theme.setMode('dark')
  else if (theme.mode === 'dark') theme.setMode('system')
  else theme.setMode('light')
}
</script>

<template>
  <UIButton variant="outline" size="icon" class="rounded-full" @click="cycleTheme">
    <Sun v-if="theme.mode === 'light'" class="h-4 w-4" />
    <Moon v-else-if="theme.mode === 'dark'" class="h-4 w-4" />
    <Monitor v-else class="h-4 w-4" />
    <span class="sr-only">Toggle theme</span>
  </UIButton>
</template>
