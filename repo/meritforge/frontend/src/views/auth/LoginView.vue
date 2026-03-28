<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next'
import { reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import ThemeToggle from '@/components/app/ThemeToggle.vue'
import { UIButton } from '@/components/ui/button'
import { UICard, UICardContent, UICardDescription, UICardHeader, UICardTitle } from '@/components/ui/card'
import { UIInput } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const form = reactive({
  email: '',
  password: ''
})

const errorMessage = ref('')

async function onSubmit() {
  errorMessage.value = ''
  try {
    await auth.login(form)
    await router.push('/app')
  } catch (error) {
    errorMessage.value = 'Unable to sign in. Check your credentials and try again.'
  }
}
</script>

<template>
  <div class="relative min-h-screen overflow-hidden bg-background text-foreground">
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,hsl(var(--primary)/0.2),transparent_40%),radial-gradient(circle_at_80%_80%,hsl(var(--accent)/0.3),transparent_45%)]" />
    <div class="relative mx-auto flex min-h-screen w-full max-w-6xl items-center justify-center px-4 py-16 sm:px-8">
      <div class="grid w-full items-center gap-8 lg:grid-cols-2">
        <section class="animate-fade-in-up space-y-6 text-center lg:text-left">
          <p class="text-xs uppercase tracking-[0.18em] text-muted-foreground">MeritForge Platform</p>
          <h1 class="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Premium Career Media and Hiring Workspace
          </h1>
          <p class="max-w-xl text-base text-muted-foreground sm:text-lg">
            Secure, role-aware intranet experience for students, employers, reviewers, and platform administrators.
          </p>
        </section>

        <UICard class="animate-fade-in-up border-border/60 bg-card/80 backdrop-blur-sm">
          <UICardHeader class="space-y-1">
            <div class="flex items-center justify-between">
              <UICardTitle>Sign in</UICardTitle>
              <ThemeToggle />
            </div>
            <UICardDescription>Use your MeritForge account to access your workspace.</UICardDescription>
          </UICardHeader>
          <UICardContent>
            <form class="space-y-4" @submit.prevent="onSubmit">
              <div class="space-y-2">
                <label class="text-sm font-medium">Email</label>
                <UIInput v-model="form.email" type="email" autocomplete="email" placeholder="name@company.local" />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium">Password</label>
                <UIInput v-model="form.password" type="password" autocomplete="current-password" placeholder="Enter password" />
              </div>
              <p v-if="errorMessage" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {{ errorMessage }}
              </p>
              <UIButton type="submit" class="w-full gap-2" :disabled="auth.loading">
                <span>{{ auth.loading ? 'Signing in...' : 'Continue to workspace' }}</span>
                <ArrowRight class="h-4 w-4" />
              </UIButton>
              <p class="text-center text-sm text-muted-foreground">
                New here?
                <RouterLink to="/register" class="font-medium text-primary hover:underline">Create account</RouterLink>
              </p>
            </form>
          </UICardContent>
        </UICard>
      </div>
    </div>
  </div>
</template>
