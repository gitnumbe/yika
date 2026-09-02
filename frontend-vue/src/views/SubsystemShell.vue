<!-- P2.4 子系统外壳：统一导航栏 + iframe 接入点 + 共享登录态(Cookie) -->
<template>
  <div class="shell">
    <header class="shell-header">
      <el-button link class="back-btn" @click="$router.push('/portal')">
        <el-icon><Back /></el-icon> 工作台
      </el-button>
      <div class="shell-title">{{ subsys?.name || '子系统' }}</div>
      <div class="shell-right">
        <el-tag v-if="subsys" size="small" effect="plain">{{ subsys.key }}</el-tag>
      </div>
    </header>
    <iframe
      v-if="subsys?.url"
      class="shell-iframe"
      :src="subsys.url"
      :key="subsys.url"
    />
    <el-empty v-else description="该子系统未配置接入地址" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const subsys = ref<any>(null)

async function load() {
  const key = route.params.key as string
  try {
    const r = await api.get('/subsystems/mine')
    subsys.value = (r.data as any[]).find((s) => s.key === key) || null
  } catch {
    subsys.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.shell { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg); }
.shell-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  height: 52px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.back-btn { color: var(--text2); }
.shell-title { font-weight: 600; color: var(--text); font-size: 15px; }
.shell-right { margin-left: auto; }
.shell-iframe {
  flex: 1;
  width: 100%;
  border: none;
  background: var(--surface);
}
</style>
