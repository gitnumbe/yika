<!-- P7b.1/P7b.2 录音笔记页 + A3 候选箱：录音上传→A6笔记展示→提炼→候选确认 -->
<template>
  <div class="business">
    <header class="biz-header">
      <el-button link @click="$router.push('/portal')"><el-icon><Back /></el-icon> 工作台</el-button>
      <div class="biz-title">录音与笔记</div>
      <el-button type="primary" size="small" @click="dlgUpload = true"><el-icon><Microphone /></el-icon> 上传录音</el-button>
    </header>
    <main class="biz-main">
      <el-card shadow="never" class="panel">
        <template #header><span class="op-title">笔记列表</span></template>
        <el-table :data="notes" border v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column label="场景" width="110">
            <template #default="{ row }">{{ sceneLabel(row.scenario) }}</template>
          </el-table-column>
          <el-table-column label="摘要" min-width="200">
            <template #default="{ row }">{{ (row.ai_structured||{}).summary || '（无摘要）' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <el-button size="small" @click="openDetail(row)">详情</el-button>
              <el-button size="small" type="warning" plain @click="extract(row)">提炼需求</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && notes.length===0" description="暂无笔记，先上传一段录音" />
      </el-card>
    </main>

    <!-- 录音上传弹窗 -->
    <el-dialog v-model="dlgUpload" title="上传录音" width="520px">
      <el-form label-width="90px">
        <el-form-item label="所属客户"><el-select v-model="upForm.customer_id" clearable filterable placeholder="选客户"><el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" /></el-select></el-form-item>
        <el-form-item label="录音文件" required>
          <input type="file" accept="audio/*" @change="onFile" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgUpload=false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="doUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 笔记详情 + A3 候选箱 -->
    <el-dialog v-model="dlgDetail" :title="'笔记 #' + (cur?.id||'')" width="720px">
      <div v-if="cur">
        <div class="note-block"><div class="note-block-title">转写文本</div>{{ cur.transcript || '（无转写）' }}</div>
        <el-divider />
        <template v-if="cur.ai_structured && (cur.ai_structured.summary || (cur.ai_structured.points||[]).length)">
          <div class="note-block"><div class="note-block-title">摘要</div>{{ cur.ai_structured.summary || '—' }}</div>
          <div class="note-block"><div class="note-block-title">要点</div><div v-for="(p,i) in (cur.ai_structured.points||[])" :key="i">· {{ p.topic }}：{{ p.detail }}</div></div>
          <div class="note-block"><div class="note-block-title">决策</div><div v-for="(d,i) in (cur.ai_structured.decisions||[])" :key="i">· {{ d.content }}</div></div>
          <div class="note-block"><div class="note-block-title">待办</div><div v-for="(t,i) in (cur.ai_structured.todos||[])" :key="i">· {{ t.item }}{{ t.owner ? '（'+t.owner+'）' : '' }}</div></div>
        </template>
        <el-empty v-else description="尚无结构化笔记（转写任务进行中或未成功）" />
        <el-divider v-if="candidates.length" />
        <!-- A3 候选箱 -->
        <template v-if="candidates.length">
          <div class="note-block"><div class="note-block-title">候选需求（待确认，人工拍板后才入需求库）</div>
            <div v-for="(c,i) in candidates" :key="i" class="cand-row">
              <el-checkbox v-model="c.keep" />
              <el-input v-model="c.title" size="small" style="flex:1" />
              <el-tag size="small" :type="(c.confidence||0)>0.7?'success':'info'">{{ Math.round((c.confidence||0)*100) }}%</el-tag>
            </div>
          </div>
          <div style="margin-top:10px">
            <el-button type="primary" size="small" @click="confirmCandidates">确认选中</el-button>
            <el-button size="small" @click="candidates=[]">清除</el-button>
          </div>
        </template>
        <el-empty v-else description="点击「提炼需求」从转写中提取候选需求" :image-size="60" />
      </div>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Microphone } from '@element-plus/icons-vue'
import api from '../../api/client'
const notes = ref<any[]>([])
const customers = ref<any[]>([])
const loading = ref(false)
const dlgUpload = ref(false)
const uploading = ref(false)
const upForm = ref<any>({ customer_id: null })
let file: File | null = null
const dlgDetail = ref(false)
const cur = ref<any>(null)
const candidates = ref<any[]>([])
const sceneLabel = (s: string) => ({ req_discussion:'需求沟通', internal:'内部', solution:'方案讨论' } as any)[s] || s
function onFile(e: any) { file = e.target.files?.[0] || null }
async function load() {
  loading.value = true
  try {
    const [n, c] = await Promise.all([api.get('/notes/'), api.get('/customers/')])
    notes.value = n.data
    customers.value = c.data
  } finally { loading.value = false }
}
async function doUpload() {
  if (!file) { ElMessage.warning('请选录音文件'); return }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('audio', file)
    if (upForm.value.customer_id) fd.append('customer_id', String(upForm.value.customer_id))
    await api.post('/recordings/upload', fd)
    ElMessage.success('已上传，转写任务后台处理中')
    dlgUpload.value = false; file = null
    setTimeout(load, 2500)  // 稍等后台流水线
  } finally { uploading.value = false }
}
function openDetail(row: any) {
  cur.value = row
  candidates.value = []
  dlgDetail.value = true
}
async function extract(row: any) {
  const r = await api.post(`/notes/${row.id}/extract`)
  candidates.value = (r.data.candidates || []).map((c:any) => ({ ...c, keep: true }))
  if (!candidates.value.length) { ElMessage.info('未提炼到候选需求'); return }
  cur.value = row
  dlgDetail.value = true
}
async function confirmCandidates() {
  const keep = candidates.value.filter((c:any) => c.keep)
  if (!keep.length) { ElMessage.warning('请勾选至少一项'); return }
  const body = { project_id: null, customer_id: (cur.value as any)?.customer_id, candidates: keep.map((c:any)=>({ title:c.title, description:c.description||'', source_ref:c.source_ref||'' })) }
  await api.post(`/notes/${cur.value.id}/confirm-requirements`, body)
  ElMessage.success('候选已确认入需求库')
  candidates.value = [] ; dlgDetail.value = false ; load()
}
onMounted(load)
</script>

<style scoped>
.business { min-height: 100vh; background: #f5f7fa; }
.biz-header { display: flex; align-items: center; gap: 16px; padding: 16px 24px; background: #fff; border-bottom: 1px solid #e6e8eb; }
.biz-title { font-size: 18px; font-weight: 600; color: #1f2329; flex: 1; }
.biz-main { max-width: 1080px; margin: 0 auto; padding: 24px; }
.panel { border-radius: 10px; }
.note-card { margin-bottom: 14px; }
.note-block { margin-bottom: 10px; }
.note-block-title { font-weight: 600; color: #1f2329; margin-bottom: 4px; }
.cand-row { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px dashed #eee; }
</style>
