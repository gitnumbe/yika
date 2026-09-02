import axios from 'axios'

// 后端 API：开发走 vite 代理（相对路径 /auth、/platform、/api 等，零 CORS）；
// 生产经 Nginx 同域反向代理到后端。无需绝对地址。
const baseURL = import.meta.env.VITE_API_BASE || ''

export const api = axios.create({
  baseURL,
  withCredentials: true, // 共享 Cookie（iframe 子系统共享登录态）
})

// 请求拦截：优先 header token（若 store 有），否则靠 Cookie
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('yika_access')
  if (token && !config.headers['token']) {
    config.headers['token'] = token
  }
  return config
})

// 响应拦截：401 → 清 token 跳登录；统一错误提示
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('yika_access')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

export default api
