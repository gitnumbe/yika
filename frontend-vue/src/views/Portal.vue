<!-- P2.3 门户工作台：子系统图标墙(按角色过滤) + 运营位 -->
<template>
  <div class="portal">
    <header class="portal-header">
      <div class="brand">
        <span class="brand-logo">yika</span>
        <span class="brand-ai">AI</span>
      </div>
      <el-dropdown @command="onUserCmd">
        <span class="user-chip">
          <el-avatar :size="28" class="avatar">{{ initial }}</el-avatar>
          <span class="user-name">{{ user?.display_name || user?.username || '用户' }}</span>
          <el-tag size="small" class="role-tag" effect="plain">{{ roleLabel }}</el-tag>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <main class="portal-main">
      <section class="subsys-grid">
        <!-- 子系统图标墙：按当前角色过滤（由 /subsystems/mine 提供） -->
        <el-card
          v-for="s in subsystems"
          :key="s.key"
          class="subsys-card"
          shadow="hover"
          @click="openSubsys(s)"
        >
          <div class="subsys-icon" :style="{ background: s.icon_bg || 'var(--primary-soft)' }">
            <el-icon :size="26" :color="s.icon_color || 'var(--primary)'"><Grid /></el-icon>
          </div>
          <div class="subsys-name">{{ s.name }}</div>
          <div class="subsys-desc">{{ s.description || '—' }}</div>
        </el-card>
        <el-empty v-if="!subsystems.length" description="当前角色暂无可访问的子系统" />
      </section>

      <!-- 运营三卡：待办 / 最近访问 / 公告 -->
      <section class="op-cards">
        <el-card class="op-card" shadow="never">
          <template #header><span class="op-title">待办</span></template>
          <div class="op-empty">暂无待办事项</div>
        </el-card>
        <el-card class="op-card" shadow="never">
          <template #header><span class="op-title">最近访问</span></template>
          <div class="op-empty">暂无最近访问</div>
        </el-card>
        <el-card class="op-card" shadow="never">
          <template #header><span class="op-title">系统公告</span></template>
          <div class="op-empty">暂无公告</div>
        </el-card>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api/client'

const router = useRouter()
const auth = useAuthStore()
const subsystems = ref<any[]>([])

const user = computed(() => auth.user)
const initial = computed(() => (auth.user?.display_name || auth.user?.username || 'U').slice(0, 1).toUpperCase())
const roleLabel = computed(() => {
  const m: any = { admin: '管理员', leader: '组长', instructor: '讲师', developer: '开发' }
  return user.value ? m[user.value.role] || user.value.role : ''
})

async function loadSubsystems() {
  const r = await api.get('/subsystems/mine')
  subsystems.value = r.data
}

function openSubsys(s: any) {
  router.push(`/subsys/${s.key}`)
}

function onUserCmd(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}

onMounted(async () => {
  await auth.fetchMe()
  await loadSubsystems()
})
</script>

<style scoped>
.portal { min-height: 100vh; background: var(--bg); }
.portal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.brand { display: flex; align-items: center; font-weight: 800; font-size: 20px; }
.brand-logo { color: var(--primary); }
.brand-ai { color: var(--primary); }
.user-chip { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.avatar { background: var(--primary-soft); color: var(--primary); }
.user-name { color: var(--text); font-size: 14px; }
.role-tag { color: var(--text2); }
.portal-main { max-width: 1080px; margin: 0 auto; padding: 24px; }
.subsys-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}
.subsys-card { cursor: pointer; transition: transform .2s, box-shadow .2s; }
.subsys-card:hover { transform: translateY(-3px); border-color: var(--primary); }
.subsys-icon {
  width: 52px; height: 52px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
}
.subsys-name { margin-top: 12px; font-weight: 600; color: var(--text); }
.subsys-desc { color: var(--text3); font-size: 13px; margin-top: 4px; }
.op-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 24px; }
.op-title { font-weight: 600; color: var(--text); }
.op-empty { color: var(--text3); font-size: 13px; padding: 12px 0; }
@media (max-width: 700px) { .op-cards { grid-template-columns: 1fr; } }
</style>
