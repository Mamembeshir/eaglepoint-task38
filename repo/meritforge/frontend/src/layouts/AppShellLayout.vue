<script setup lang="ts">
import { LogOut, Menu } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import SidebarNav from '@/components/app/SidebarNav.vue'
import ThemeToggle from '@/components/app/ThemeToggle.vue'
import { UIButton } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const mobileMenu = ref(false)

const displayName = computed(() => auth.user?.display_name || auth.user?.first_name || 'Workspace User')
const roleLabel = computed(() => (auth.role ?? 'user').replace(/_/g, ' '))

async function onLogout() {
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <div class="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_0%,hsl(var(--primary)/0.14),transparent_45%),radial-gradient(circle_at_80%_100%,hsl(var(--accent)/0.18),transparent_35%)]" />
    <div class="relative mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 lg:grid-cols-[280px,1fr]">
      <aside class="hidden border-r border-border/60 bg-card/70 backdrop-blur lg:block">
        <div class="flex h-full flex-col p-6">
          <div class="mb-8 flex items-center justify-between">
            <div>
              <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">MeritForge</p>
              <h1 class="mt-1 text-2xl font-semibold tracking-tight">Workspace</h1>
            </div>
            <ThemeToggle />
          </div>
          <SidebarNav :role="auth.role" />
          <div class="mt-auto rounded-lg border border-border/60 bg-background/60 p-4">
            <p class="text-sm font-medium capitalize">{{ roleLabel }}</p>
            <p class="text-xs text-muted-foreground">Role-adaptive navigation enabled</p>
          </div>
        </div>
      </aside>

      <div class="relative flex min-h-screen flex-col">
        <header class="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur">
          <div class="mx-auto flex h-16 w-full items-center justify-between px-4 sm:px-6 lg:px-8">
            <div class="flex items-center gap-3">
              <UIButton variant="outline" size="icon" class="lg:hidden" @click="mobileMenu = !mobileMenu">
                <Menu class="h-4 w-4" />
              </UIButton>
              <div>
                <p class="text-sm font-medium">{{ displayName }}</p>
                <p class="text-xs capitalize text-muted-foreground">{{ roleLabel }}</p>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <ThemeToggle class="lg:hidden" />
              <UIButton variant="ghost" size="sm" class="gap-2" @click="onLogout">
                <LogOut class="h-4 w-4" />
                Sign out
              </UIButton>
            </div>
          </div>
          <div v-if="mobileMenu" class="border-t border-border/60 p-4 lg:hidden">
            <SidebarNav :role="auth.role" />
          </div>
        </header>

        <main class="flex-1 p-4 sm:p-6 lg:p-8">
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>
