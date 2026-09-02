import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/', redirect: '/portal' },
  { path: '/portal', component: () => import('../views/Portal.vue') },
  { path: '/subsys/:key', component: () => import('../views/SubsystemShell.vue') },
  { path: '/admin', component: () => import('../views/Admin.vue') },
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
