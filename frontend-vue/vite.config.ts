import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      // 平台后端（P0-P1，端口 8010）
      '/auth': 'http://127.0.0.1:8010',
      '/api': 'http://127.0.0.1:8010',
      '/org': 'http://127.0.0.1:8010',
      '/subsystems': 'http://127.0.0.1:8010',
      '/permissions': 'http://127.0.0.1:8010',
      '/customers': 'http://127.0.0.1:8010',
      '/knowledge': 'http://127.0.0.1:8010',
      '/projects': 'http://127.0.0.1:8010',
      '/requirements': 'http://127.0.0.1:8010',
      '/notes': 'http://127.0.0.1:8010',
    },
  },
})
