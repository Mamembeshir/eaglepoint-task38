<script setup lang="ts">
import { computed } from 'vue'

import ContentAuthorWorkspaceView from '@/views/workspace/ContentAuthorWorkspaceView.vue'
import ReviewerWorkspaceView from '@/views/workspace/ReviewerWorkspaceView.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const isReviewerOnly = computed(() => auth.role === 'reviewer')
</script>

<template>
  <ReviewerWorkspaceView v-if="isReviewerOnly" />
  <ContentAuthorWorkspaceView v-else />
</template>
