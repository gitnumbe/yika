<!-- P7a.1 客户管理页：组内客户列表 + 新建/编辑 + 详情（版式A企业浅色） -->
<template>
  <div class="business">
    <header class="biz-header">
      <el-button link @click="$router.push('/portal')"><el-icon><Back /></el-icon> 工作台</el-button>
      <div class="biz-title">客户管理</div>
      <el-button type="primary" size="small" @click="openCreate">新建客户</el-button>
    </header>

    <main class="biz-main">
      <el-card shadow="never" class="panel">
        <el-table :data="customers" border v-loading="loading">
          <el-table-column prop="name" label="客户名称" min-width="160" />
          <el-table-column prop="industry" label="行业" width="120" />
          <el-table-column prop="scale" label="规模" width="90" />
          <el-table-column prop="main_business" label="主营" min-width="180" show-overflow-tooltip />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="primary" plain @click="openDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && customers.length === 0" description="暂无客户，点击右上角新建" />
      </el-card>
    </main>

    <!-- 新建 / 编辑弹窗 -->
    <el-dialog v-model="dlg" :title="editing ? '编辑客户' : '新建客户'" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="客户名称" required>
          <el-input v-model="form.name" placeholder="公司名" />
        </el-form-item>
        <el-form-item label="行业">
          <el-input v-model="form.industry" placeholder="如 工业软件 / 制造" />
        </el-form-item>
        <el-form-item label="规模">
          <el-select v-model="form.scale" placeholder="选规模" clearable>
            <el-option label="小型" value="小型" />
            <el-option label="中型" value="中型" />
            <el-option label="中大型" value="中大型" />
            <el-option label="大型" value="大型" />
          </el-select>
        </el-form-item>
        <el-form-item label="主营">
          <el-input v-model="form.main_business" placeholder="主要业务" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情弹窗（含触发 A1 建档） -->
    <el-dialog v-model="detailDlg" title="客户详情" width="520px">
      <el-descriptions :column="1" border v-if="detail">
        <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
        <el-descriptions-item label="行业">{{ detail.industry || '-' }}</el-descriptions-item>
        <el-descriptions-item label="规模">{{ detail.scale || '-' }}</el-descriptions-item>
        <el-descriptions-item label="主营">{{ detail.main_business || '-' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" plain :loading="aiLoading" @click="triggerA1">AI 建档（A1）</el-button>
        <el-button @click="detailDlg = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'

const customers = ref<any[]>([])
const loading = ref(false)
const dlg = ref(false)
const editing = ref(false)
const form = ref<any>({ name: '', industry: '', scale: '', main_business: '' })
const detailDlg = ref(false)
const detail = ref<any>(null)
const aiLoading = ref(false)

async function load() {
  loading.value = true
  try {
    const r = await api.get('/customers/')
    customers.value = r.data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = false
  form.value = { name: '', industry: '', scale: '', main_business: '' }
  dlg.value = true
}

function openEdit(row: any) {
  editing.value = true
  form.value = { ...row }
  dlg.value = true
}

async function save() {
  if (!form.value.name) { ElMessage.warning('请填客户名称'); return }
  if (editing.value) {
    await api.put(`/customers/${form.value.id}`, form.value)
    ElMessage.success('已更新')
  } else {
    await api.post('/customers/', form.value)
    ElMessage.success('已创建')
  }
  dlg.value = false
  load()
}

async function openDetail(row: any) {
  const r = await api.get(`/customers/${row.id}`)
  detail.value = r.data
  detailDlg.value = true
}

async function triggerA1() {
  // A1 客户画像建档：后端起异步任务，前端提示（真实结果由后端流水线/任务返回，详见 P5/P6）
  aiLoading.value = true
  try {
    const r = await api.post(`/customers/${detail.value.id}/analyze`)
    ElMessage.success(r.data?.message || '已触发 A1 建档')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error?.message || 'A1 触发失败')
  } finally {
    aiLoading.value = false
  }
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
