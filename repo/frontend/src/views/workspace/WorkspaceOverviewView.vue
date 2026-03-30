<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { UIButton } from '@/components/ui/button'
import { UICard, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import type { AppRole } from '@/types/auth'

const auth = useAuthStore()

const greeting = computed(() => {
  if (auth.user?.display_name) return auth.user.display_name
  if (auth.user?.first_name) return auth.user.first_name
  return 'there'
})

interface RoleDestination {
  title: string
  description: string
  to: string
  actionLabel: string
}

const roleDestinations: Record<AppRole, RoleDestination[]> = {
  student: [
    {
      title: 'Career Space',
      description: 'Watch learning videos, track progress, and save bookmarks.',
      to: '/app/career-space',
      actionLabel: 'Open Career Space'
    },
    {
      title: 'Profile',
      description: 'Manage privacy, export/import data, and account controls.',
      to: '/app/profile',
      actionLabel: 'Open Profile'
    }
  ],
  employer_manager: [
    {
      title: 'Hiring Space',
      description: 'Manage job posts, applications, and milestone verification.',
      to: '/app/hiring-space',
      actionLabel: 'Open Hiring Space'
    },
    {
      title: 'Profile',
      description: 'Update your account settings and data preferences.',
      to: '/app/profile',
      actionLabel: 'Open Profile'
    }
  ],
  content_author: [
    {
      title: 'Editorial Space',
      description: 'Submit new content and track review outcomes.',
      to: '/app/editorial-space',
      actionLabel: 'Open Editorial Space'
    },
    {
      title: 'Profile',
      description: 'Manage account settings and consent preferences.',
      to: '/app/profile',
      actionLabel: 'Open Profile'
    }
  ],
  reviewer: [
    {
      title: 'Editorial Space',
      description: 'Process review queue decisions and revision feedback.',
      to: '/app/editorial-space',
      actionLabel: 'Open Review Queue'
    },
    {
      title: 'Profile',
      description: 'Manage account settings and consent preferences.',
      to: '/app/profile',
      actionLabel: 'Open Profile'
    }
  ],
  system_administrator: [
    {
      title: 'Control Space',
      description: 'Administer publishing, review workflow setup, and governance controls.',
      to: '/app/control-space',
      actionLabel: 'Open Control Space'
    },
    {
      title: 'Operations Dashboard',
      description: 'Monitor platform activity, trends, and exports.',
      to: '/app/operations',
      actionLabel: 'Open Operations'
    },
    {
      title: 'Profile',
      description: 'Manage account settings and consent preferences.',
      to: '/app/profile',
      actionLabel: 'Open Profile'
    }
  ]
}

const destinations = computed(() => {
  const role = auth.role
  if (!role) return []
  return roleDestinations[role]
})
</script>

<template>
  <section class="space-y-6">
    <header>
      <p class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Workspace</p>
      <h2 class="mt-2 text-3xl font-semibold tracking-tight">Welcome, {{ greeting }}</h2>
      <p class="mt-1 text-muted-foreground">Start from the key tools for your role and jump directly into active workflows.</p>
    </header>

    <UICard class="border-border/60 bg-card/75">
      <UICardHeader>
        <UICardTitle>Your role shortcuts</UICardTitle>
        <UICardDescription>Use these quick links to open the pages you use most.</UICardDescription>
      </UICardHeader>
      <div class="grid gap-4 px-6 pb-6 md:grid-cols-2 xl:grid-cols-3">
        <div v-for="item in destinations" :key="item.to" class="rounded-lg border border-border/60 bg-background/60 p-4">
          <p class="font-medium">{{ item.title }}</p>
          <p class="mt-1 text-sm text-muted-foreground">{{ item.description }}</p>
          <RouterLink :to="item.to" class="mt-3 inline-block">
            <UIButton size="sm" class="w-full">{{ item.actionLabel }}</UIButton>
          </RouterLink>
        </div>
      </div>
    </UICard>

    <p v-if="!destinations.length" class="rounded-md border border-border/60 bg-card/60 px-3 py-2 text-sm text-muted-foreground">
      Your role is still loading. Try refreshing this page.
    </p>
  </section>
</template>
