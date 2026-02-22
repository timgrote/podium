import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { layout: 'dashboard' },
    },
  ],
})

router.beforeEach(async (to) => {
  const { isAuthenticated, checkSession } = useAuth()

  await checkSession()

  if (to.meta.public) {
    if (isAuthenticated.value && to.path === '/login') {
      return '/dashboard'
    }
    return true
  }

  if (!isAuthenticated.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
