import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

type ThemeMode = 'light' | 'dark' | 'system'

const storageKey = 'meritforge-theme-mode'

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>((localStorage.getItem(storageKey) as ThemeMode) || 'system')

  const resolvedTheme = computed<'light' | 'dark'>(() => {
    if (mode.value === 'system') return getSystemTheme()
    return mode.value
  })

  function applyTheme() {
    const dark = resolvedTheme.value === 'dark'
    document.documentElement.classList.toggle('dark', dark)
  }

  function setMode(value: ThemeMode) {
    mode.value = value
    localStorage.setItem(storageKey, value)
    applyTheme()
  }

  function init() {
    applyTheme()
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (mode.value === 'system') applyTheme()
    })
  }

  return { mode, resolvedTheme, setMode, init }
})
