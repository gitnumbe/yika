import { defineStore } from 'pinia'
import api from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as any,
    token: localStorage.getItem('yika_access') || '',
    permissions: null as any,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    async login(username: string, password: string) {
      // 后端登录：返回双令牌 + 写共享域 Cookie；同时存 access 供 header
      const r = await api.post('/auth/login', { username, password })
      this.token = r.data.token
      localStorage.setItem('yika_access', r.data.token)
      return r.data
    },
    async fetchMe() {
      const r = await api.get('/api/shared/me')
      this.user = r.data
      return r.data
    },
    async fetchPermissions() {
      const r = await api.get('/permissions/mine')
      this.permissions = r.data
      return r.data
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('yika_access')
    },
  },
})
