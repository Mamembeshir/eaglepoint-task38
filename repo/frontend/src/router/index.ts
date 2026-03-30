import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import type { AppRole } from '@/types/auth'

const roleAll: AppRole[] = ['student', 'employer_manager', 'content_author', 'reviewer', 'system_administrator']

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/app'
    },
    {
      path: '/login',
      name: 'login',
      meta: { guestOnly: true },
      component: () => import('@/views/auth/LoginView.vue')
    },
    {
      path: '/register',
      name: 'register',
      meta: { guestOnly: true },
      component: () => import('@/views/auth/RegisterView.vue')
    },
    {
      path: '/app',
      component: () => import('@/layouts/AppShellLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'workspace-overview',
          component: () => import('@/views/workspace/WorkspaceOverviewView.vue'),
          meta: { roles: roleAll, title: 'Overview' }
        },
        {
          path: 'career-space',
          name: 'career-space',
          component: () => import('@/views/workspace/StudentWorkspaceView.vue'),
          meta: { roles: ['student'], title: 'Career Space' }
        },
        {
          path: 'hiring-space',
          name: 'hiring-space',
          component: () => import('@/views/workspace/EmployerWorkspaceView.vue'),
          meta: { roles: ['employer_manager'], title: 'Hiring Space' }
        },
        {
          path: 'editorial-space',
          name: 'editorial-space',
          component: () => import('@/views/workspace/EditorialWorkspaceView.vue'),
          meta: { roles: ['content_author', 'reviewer'], title: 'Editorial Space' }
        },
        {
          path: 'control-space',
          name: 'control-space',
          component: () => import('@/views/workspace/AdminWorkspaceView.vue'),
          meta: { roles: ['system_administrator'], title: 'Control Space' }
        },
        {
          path: 'operations',
          name: 'operations-dashboard',
          component: () => import('@/views/workspace/OperationsDashboardView.vue'),
          meta: { roles: ['system_administrator'], title: 'Operations' }
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/workspace/ProfileWorkspaceView.vue'),
          meta: { roles: roleAll, title: 'Profile' }
        }
      ]
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) {
    await auth.refreshSession()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { path: '/app' }
  }

  const roles = to.meta.roles as AppRole[] | undefined
  if (roles && auth.role && !roles.includes(auth.role)) {
    return { path: '/app' }
  }

  return true
})

export default router
