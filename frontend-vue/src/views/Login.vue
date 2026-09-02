<!--
  P2.2 登录页 · 版A 企业浅色
  布局按旧版（左视频 50% + 右表单 50% 圆角卡片），配色全部用新版版A浅色 token。
  Element Plus 组件优先（el-input / el-button / el-message）。
-->
<template>
  <div class="login-page">
    <div class="login-card">
      <!-- 左侧：视频媒体区（布局沿用旧版） -->
      <div class="login-media">
        <video class="login-video" src="/login-video.mp4" autoPlay muted loop playsInline />
        <div class="login-media-overlay" />
        <div class="login-brand">
          <span class="brand-logo">yika</span>
          <span class="brand-ai">AI</span>
        </div>
        <div class="login-media-caption">AI 驱动的企业业务集成平台</div>
      </div>

      <!-- 右侧：登录表单（新版浅色） -->
      <div class="login-form-side">
        <div class="login-form-inner">
          <p class="login-eyebrow">内部协作平台</p>
          <h2 class="login-title">欢迎回来</h2>
          <p class="login-subtitle">登录以继续协作</p>

          <el-form @submit.prevent="onLogin">
            <el-form-item>
              <el-input v-model="form.username" size="large" placeholder="请输入用户名" autocomplete="username" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="form.password" size="large" type="password" placeholder="请输入密码" show-password autocomplete="current-password" />
            </el-form-item>
            <el-alert v-if="err" :title="err" type="error" :closable="false" class="login-error" />
            <el-button type="primary" size="large" class="login-submit" :loading="loading" @click="onLogin">
              登 录
            </el-button>
          </el-form>

          <p class="login-footer">账号由管理员开通 · 纯内部使用</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const err = ref('')

async function onLogin() {
  if (!form.value.username.trim() || !form.value.password) {
    err.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  err.value = ''
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/portal')
  } catch (e: any) {
    err.value = e.response?.data?.error?.message || '登录失败，请检查用户名密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 布局沿旧版：全屏浅色底 + 居中大圆角卡片 + 左视频右表单 50:50 */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  padding: 24px;
}
.login-card {
  display: flex;
  width: min(1000px, 100%);
  min-height: min(620px, calc(100vh - 48px));
  border-radius: 20px;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
/* 左：视频 */
.login-media {
  position: relative;
  flex: 1 1 50%;
  overflow: hidden;
}
.login-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.login-media-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(51, 112, 255, 0.25) 0%, transparent 40%, rgba(0, 0, 0, 0.4) 100%);
}
.login-brand {
  position: absolute;
  top: 28px;
  left: 30px;
  display: flex;
  align-items: center;
  gap: 2px;
  font-weight: 800;
  font-size: 22px;
  color: #fff;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.3);
}
.brand-ai { color: #ffd76a; }
.login-media-caption {
  position: absolute;
  left: 30px;
  bottom: 28px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  letter-spacing: 0.08em;
}
/* 右：表单（新版浅色） */
.login-form-side {
  flex: 1 1 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 56px;
  background: var(--surface);
}
.login-form-inner { width: 100%; max-width: 340px; }
.login-eyebrow {
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--text3);
  margin-bottom: 12px;
}
.login-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}
.login-subtitle {
  font-size: 14px;
  color: var(--text2);
  margin-bottom: 28px;
}
.login-error { margin-bottom: 14px; }
.login-submit { width: 100%; margin-top: 4px; }
.login-footer {
  margin-top: 28px;
  text-align: center;
  font-size: 12px;
  color: var(--text3);
}
@media (max-width: 860px) {
  .login-media { display: none; }
  .login-card { min-height: auto; }
  .login-form-side { padding: 40px 32px; }
}
</style>
