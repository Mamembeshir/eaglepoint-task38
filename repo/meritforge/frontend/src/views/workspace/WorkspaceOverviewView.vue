<script setup lang="ts">
import { computed } from 'vue'

import { UICard, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const greeting = computed(() => {
  if (auth.user?.display_name) return auth.user.display_name
  if (auth.user?.first_name) return auth.user.first_name
  return 'there'
})
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Workspace</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Welcome, {{ greeting }}</h2>
      <p class="mt-1 text-muted-foreground">Your role-tailored navigation is ready. Workspace pages can now be implemented incrementally.</p>
    </header>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <UICard class="border-border/60 bg-card/70">
        <UICardHeader>
          <UICardTitle>Role Workspace</UICardTitle>
          <UICardDescription>Navigation adapts automatically from authenticated role.</UICardDescription>
        </UICardHeader>
      </UICard>
      <UICard class="border-border/60 bg-card/70">
        <UICardHeader>
          <UICardTitle>Protected Routes</UICardTitle>
          <UICardDescription>Unauthenticated users are redirected to the login flow.</UICardDescription>
        </UICardHeader>
      </UICard>
      <UICard class="border-border/60 bg-card/70">
        <UICardHeader>
          <UICardTitle>Theme System</UICardTitle>
          <UICardDescription>Dark, light, and system modes are fully configured.</UICardDescription>
        </UICardHeader>
      </UICard>
    </div>
  </section>
</template>
