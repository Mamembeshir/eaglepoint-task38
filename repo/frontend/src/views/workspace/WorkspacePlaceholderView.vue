<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'

const route = useRoute()

const title = computed(() => String(route.meta.title || 'Workspace Section'))
</script>

<template>
  <div class="max-w-3xl">
    <UICard class="border-border/60 bg-card/70">
      <UICardHeader>
        <UICardTitle>{{ title }}</UICardTitle>
        <UICardDescription>
          This workspace area is intentionally left as a premium-ready placeholder with route protection and role access in place.
        </UICardDescription>
      </UICardHeader>
      <UICardContent>
        <p class="text-sm text-muted-foreground">
          No specific workspace implementation has been added yet, per requirement.
        </p>
      </UICardContent>
    </UICard>
  </div>
</template>
