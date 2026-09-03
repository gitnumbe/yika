<!-- P7a.2 项目页：组内项目列表 + 新建 -->
<template>
  <div class="business">
    <header class="biz-header">
      <el-button link @click="$router.push('/portal')"><el-icon><Back /></el-icon> 工作台</el-button>
      <div class="biz-title">项目管理</div>
      <el-button type="primary" size="small" @click="openCreate">新建项目</el-button>
    </header>
    <main class="biz-main">
      <el-card shadow="never" class="panel">
        <el-table :data="projects" border v-loading="loading">
          <el-table-column prop="name" label="项目名称" min-width="160" />
          <el-table-column prop="customer_name" label="所属客户" min-width="140" />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="$router.push({ path: '/requirements', query: { project_id: row.id } })">需求</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && projects.length === 0" description="暂无项目" />
      </el-card>
    </main>
    <el-dialog v-model="dlg" title="新建项目" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="项目名" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="所属客户" required>
          <el-select v-model="form.customer_id" filterable placeholder="选客户">
            <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
const projects = ref<any[]>([])
const customers = ref<any[]>([])
const loading = ref(false)
const dlg = ref(false)
const form = ref<any>({ name: '', customer_id: null, description: '' })
async function load() {
  loading.value = true
  try {
    const [p, c] = await Promise.all([api.get('/projects/'), api.get('/customers/')])
    projects.value = p.data
    customers.value = c.data
  } finally { loading.value = false }
}
function openCreate() { form.value = { name: '', customer_id: null, description: '' }; dlg.value = true }
async function save() {
  if (!form.value.name || !form.value.customer_id) { ElMessage.warning('请填项目名和客户'); return }
  await api.post('/projects/', form.value)
  ElMessage.success('已创建'); dlg.value = false; load()
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
