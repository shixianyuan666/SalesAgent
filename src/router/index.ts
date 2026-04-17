import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import LoginPage from '@/pages/LoginPage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'
import ProductsPage from '@/pages/ProductsPage.vue'
import InboxPage from '@/pages/InboxPage.vue'
import SettingsPage from '@/pages/SettingsPage.vue'
import MemoryPage from '@/pages/MemoryPage.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
  },
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardPage,
    meta: { requiresAuth: true },
  },
  {
    path: '/products',
    name: 'products',
    component: ProductsPage,
    meta: { requiresAuth: true },
  },
  {
    path: '/inbox',
    name: 'inbox',
    component: InboxPage,
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsPage,
    meta: { requiresAuth: true },
  },
  {
    path: '/memory',
    name: 'memory',
    component: MemoryPage,
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const { isAuthed } = useAuth()
  const requiresAuth = Boolean(to.meta?.requiresAuth)
  if (requiresAuth && !isAuthed.value) return { name: 'login' }
  if (to.name === 'login' && isAuthed.value) return { name: 'dashboard' }
  return true
})

export default router
