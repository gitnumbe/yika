<!-- P7a.2 需求页：状态机流转 + 组长评审按钮按权限显示 -->
<template>
  <div class="business">
    <header class="biz-header">
      <el-button link @click="$router.push('/portal')"><el-icon><Back /></el-icon> 工作台</el-button>
      <div class="biz-title">需求管理</div>
      <el-button type="primary" size="small" @click="openCreate">新建需求</el-button>
    </header>
    <main class="biz-main">
      <el-alert v-if="isInstructor" title="讲师可提交需求供评审，但评审由组长拍板" type="info" :closable="false" style="margin-bottom:12px" />
      <el-card shadow="never" class="panel">
        <el-table :data="reqs" border v-loading="loading">
          <el-table-column prop="title" label="需求" min-width="180" />
          <el-table-column label="状态" width="130">
            <template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ label(row.status) }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="90" />
          <el-table-column label="操作" width="300">
            <template #default="{ row }">
              <el-button v-if="row.status === 'draft'" size="small" type="primary" plain @click="transition(row,'pending_review')">提交评审</el-button>
              <!-- 评审操作：仅组长 -->
              <template v-if="isLeader && row.status === 'pending_review'">
                <el-button size="small" type="success" @click="transition(row,'feasible')">可行</el-button>
                <el-button size="small" type="warning" @click="transition(row,'info_needed')">需调整</el-button>
                <el-button size="small" type="danger" @click="transition(row,'infeasible')">不可行</el-button>
              </template>
              <!-- 开发/交付：非讲师 -->
              <template v-if="!isInstructor && (row.status === 'feasible')">
                <el-button size="small" type="primary" @click="transition(row,'in_dev')">进入开发</el-button>
              </template>
              <template v-if="!isInstructor && row.status === 'in_dev'">
                <el-button size="small" type="success" @click="transition(row,'delivered')">标记交付</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && reqs.length === 0" description="暂无需求" />
      </el-card>
    </main>
    <el-dialog v-model="dlg" title="新建需求" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="标题" required><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
        <el-form-item label="所属项目">
          <el-select v-model="form.project_id" clearable filterable placeholder="选项目">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority">
            <el-option label="高" value="high" /><el-option label="中" value="med" /><el-option label="低" value="low" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
import { useAuthStore } from '../../stores/auth'
const route = useRoute()
const auth = useAuthStore()
const reqs = ref<any[]>([])
const projects = ref<any[]>([])
const loading = ref(false)
const dlg = ref(false)
const form = ref<any>({ title: '', description: '', project_id: null, priority: 'med' })
const isLeader = computed(() => auth.user?.role === 'leader')
const isInstructor = computed(() => auth.user?.role === 'instructor')
const LABELS: any = { draft:'草稿', pending_review:'待评审', feasible:'可行', plan_needed:'需调整·方案待调', info_needed:'需调整·信息待补', infeasible:'不可行', in_dev:'开发中', delivered:'已交付' }
const label = (s: string) => LABELS[s] || s
const statusTag = (s: string): any => ({ draft:'info', pending_review:'warning', feasible:'success', infeasible:'danger', in_dev:'primary', delivered:'success' } as any)[s] || 'info'
async function load() {
  loading.value = true
  try {
    const [r, p] = await Promise.all([api.get('/requirements/'), api.get('/projects/')])
    reqs.value = r.data
    projects.value = p.data
  } finally { loading.value = false }
}
if (!auth.user) { await auth.fetchMe() }
function openCreate() { form.value = { title:'', description:'', project_id: route.query.project_id || null, priority:'med' }; dlg.value = true }
async function save() {
  if (!form.value.title) { ElMessage.warning('请填标题'); return }
  await api.post('/requirements/', form.value)
  ElMessage.success('已创建'); dlg.value = false; load()
}
async function transition(row: any, to: string) {
  const reason = to === 'infeasible' ? '判定不可行' : ''
  await api.post(`/requirements/${row.id}/transition`, { to, reason })
  ElMessage.success('状态已更新'); load()
}
onMounted(load)
</script>

<style scoped>
.business { min-height: 100vh; background: #f5f7fa; }
.biz-header { display: flex; align-items: center; gap: 16px; padding: 16px 24px; background: #fff; border-bottom: 1px solid #e6e8eb; }
.biz-title { font-size: 18px; font-weight: 600; color: #1f2329; flex: 1; }
.biz-main { max-width: 1080px; margin: 0 auto; padding: 24px; }
.panel { border-radius: 10px; }
</style>
