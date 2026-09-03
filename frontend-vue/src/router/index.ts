import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/', redirect: '/portal' },
  { path: '/portal', component: () => import('../views/Portal.vue') },
  { path: '/subsys/:key', component: () => import('../views/SubsystemShell.vue') },
  { path: '/admin', component: () => import('../views/Admin.vue') },
  // P7a 业务页（手动流）
  { path: '/customers', component: () => import('../views/business/Customers.vue') },
  { path: '/projects', component: () => import('../views/business/Projects.vue') },
  { path: '/requirements', component: () => import('../views/business/Requirements.vue') },
  { path: '/knowledge', component: () => import('../views/business/Knowledge.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 未登录跳登录（非公开路由）
router.beforeEach((to) => {
  const token = localStorage.getItem('yika_access')
  if (!to.meta.public && !token) {
    return { path: '/login' }
  }
})

export default router
