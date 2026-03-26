import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/projects',
    },
    {
      path: '/login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/dashboard',
      redirect: '/projects',
    },
    {
      path: '/projects',
      component: () => import('../views/DashboardView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/projects/:projectId',
      component: () => import('../views/ProjectPageView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/projects/:projectId/tasks/:entityId',
      component: () => import('../views/ProjectPageView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/projects/:projectId/contracts/:entityId',
      component: () => import('../views/ProjectPageView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/projects/:projectId/invoices/:entityId',
      component: () => import('../views/ProjectPageView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/projects/:projectId/proposals/:entityId',
      component: () => import('../views/ProjectPageView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/my-tasks',
      component: () => import('../views/MyTasksView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/my-tasks/:taskId',
      component: () => import('../views/MyTasksView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/timesheet',
      component: () => import('../views/TimesheetView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/clients',
      component: () => import('../views/ClientsView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/financial',
      component: () => import('../views/FinancialView.vue'),
      meta: { layout: 'dashboard' },
    },
    {
      path: '/profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { layout: 'dashboard' },
    },
  ],
})

router.beforeEach(async (to) => {
  const { isAuthenticated, checkSession } = useAuth()

  await checkSession()

  if (to.meta.public) {
    if (isAuthenticated.value && to.path === '/login') {
      return '/projects'
    }
    return true
  }

  if (!isAuthenticated.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

export default router
