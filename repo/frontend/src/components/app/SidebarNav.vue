<script setup lang="ts">
import { Briefcase, Compass, FileCheck2, LineChart, ShieldCheck, Sparkles, UserRound } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { cn } from '@/lib/utils'
import type { AppRole } from '@/types/auth'

interface NavItem {
  label: string
  to: string
  icon: unknown
  roles: AppRole[]
}

const props = defineProps<{ role: AppRole | null }>()
const route = useRoute()

const navItems: NavItem[] = [
  { label: 'Overview', to: '/app', icon: Compass, roles: ['student', 'employer_manager', 'content_author', 'reviewer', 'system_administrator'] },
  { label: 'Career Space', to: '/app/career-space', icon: Sparkles, roles: ['student'] },
  { label: 'Hiring Space', to: '/app/hiring-space', icon: Briefcase, roles: ['employer_manager'] },
  { label: 'Editorial Space', to: '/app/editorial-space', icon: FileCheck2, roles: ['content_author', 'reviewer'] },
  { label: 'Control Space', to: '/app/control-space', icon: ShieldCheck, roles: ['system_administrator'] },
  { label: 'Operations', to: '/app/operations', icon: LineChart, roles: ['system_administrator'] },
  { label: 'Profile', to: '/app/profile', icon: UserRound, roles: ['student', 'employer_manager', 'content_author', 'reviewer', 'system_administrator'] }
]

const filteredItems = computed(() => {
  if (!props.role) return []
  const role = props.role
  return navItems.filter((item) => item.roles.includes(role))
})
</script>

<template>
  <nav class="space-y-1.5">
    <RouterLink
      v-for="item in filteredItems"
      :key="item.to"
      :to="item.to"
      :class="cn(
        'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
        route.path === item.to
          ? 'bg-primary text-primary-foreground shadow-sm'
          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
      )"
    >
      <component :is="item.icon" class="h-4 w-4" />
      <span>{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>
