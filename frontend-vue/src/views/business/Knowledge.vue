<!-- P7a.3 知识库页：全平台查询 + 写入按角色（开发/组长直接发，讲师 draft 待审） -->
<template>
  <div class="business">
    <header class="biz-header">
      <el-button link @click="$router.push('/portal')"><el-icon><Back /></el-icon> 工作台</el-button>
      <div class="biz-title">知识库</div>
      <el-button v-if="canWrite" type="primary" size="small" @click="openCreate">新建知识</el-button>
    </header>
    <main class="biz-main">
      <el-input v-model="kw" placeholder="搜索标题/内容/标签" clearable style="margin-bottom:12px" @input="load" />
      <el-card shadow="never" class="panel">
        <el-table :data="filtered" border v-loading="loading">
          <el-table-column prop="title" label="标题" min-width="180" />
          <el-table-column prop="body" label="内容" min-width="220" show-overflow-tooltip />
          <el-table-column label="标签" min-width="120">
            <template #default="{ row }">
              <el-tag v-for="t in row.tags" :key="t" size="small" style="margin-right:4px">{{ t }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'published' ? 'success' : 'warning'">{{ row.status === 'published' ? '已发布' : '待审' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="canReview" label="操作" width="110">
            <template #default="{ row }">
              <el-button v-if="row.status === 'draft'" size="small" type="success" @click="review(row)">审核</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && filtered.length === 0" description="暂无知识" />
      </el-card>
    </main>
    <el-dialog v-model="dlg" title="新建知识" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标题" required><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="form.body" type="textarea" :rows="5" /></el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create default-first-option placeholder="输入标签回车" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-alert v-if="willBeDraft" title="讲师提交将进入待审核，由组长/开发审核后发布" type="info" :closable="false" style="margin-bottom:8px" />
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api/client'
import { useAuthStore } from '../../stores/auth'
const auth = useAuthStore()
const items = ref<any[]>([])
const loading = ref(false)
const kw = ref('')
const dlg = ref(false)
const form = ref<any>({ title: '', body: '', tags: [] })
const canWrite = computed(() => ['developer','leader'].includes(auth.user?.role))
const canReview = computed(() => ['developer','leader'].includes(auth.user?.role))
const willBeDraft = computed(() => auth.user?.role === 'instructor')
const filtered = computed(() => {
  if (!kw.value) return items.value
  const k = kw.value.toLowerCase()
  return items.value.filter((i) => (i.title||'').toLowerCase().includes(k) || (i.body||'').toLowerCase().includes(k) || (i.tags||[]).some((t:string)=>t.toLowerCase().includes(k)))
})
async function load() {
  loading.value = true
  try { const r = await api.get('/knowledge/'); items.value = r.data }
  finally { loading.value = false }
}
if (!auth.user) { await auth.fetchMe() }
function openCreate() { form.value = { title:'', body:'', tags:[] }; dlg.value = true }
async function save() {
  if (!form.value.title) { ElMessage.warning('请填标题'); return }
  await api.post('/knowledge/', form.value)
  ElMessage.success(willBeDraft.value ? '已提交待审' : '已发布'); dlg.value = false; load()
}
async function review(row: any) {
  await api.post(`/knowledge/${row.id}/review`)
  ElMessage.success('已审核发布'); load()
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
